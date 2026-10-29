"""Ledger limitado de lotes; todas as escritas usam a UoW do chamador."""
from dataclasses import asdict
from uuid import uuid4
from psycopg.types.json import Jsonb

from app.application.activate_mega_sena_baseline import STREAM_KEY
from app.application.historical_content import digest
from app.application.persistence import PersistenceError
from app.application.sync_postgres import CODE_VERSION, review_targets
from app.infrastructure.postgres.catalog import PgCatalogRepository
from app.infrastructure.postgres.common import advisory_command, insert
from app.infrastructure.postgres.sync import PgSyncRepository


class PgSyncBatchRepository:
    def __init__(self,db,observe):
        self.db,self.observe=db,observe
        self.sync=PgSyncRepository(db,observe)

    def _header(self,checkpoint,binding):
        cp=self.sync._checkpoint(checkpoint,binding)
        row=self.db.execute("""SELECT b.last_sequence,a.coverage_hash,a.coverage_report FROM lb.baseline_activation a
            JOIN lb.ingestion_baseline b ON b.id=a.baseline_id JOIN lb.raw_artifact r ON r.id=b.artifact_id
            WHERE a.checkpoint_id=%s AND a.baseline_id=%s AND a.target_source_id=%s AND b.materialization_status='loaded'
            AND r.storage_state='available'""",(checkpoint,cp["baseline_id"],binding.source_id)).fetchone()
        if not row or cp["stream_key"]!=STREAM_KEY or digest(row["coverage_report"])!=row["coverage_hash"]:
            raise PersistenceError("sync_not_initialized")
        return {**cp,"anchor":row["last_sequence"]}

    def open(self,request):
        policy=asdict(request.policy); policy["interval_seconds"]=float(policy["interval_seconds"])
        fingerprint=digest({"version":CODE_VERSION,"checkpoint":str(request.checkpoint_id),"policy":policy})
        advisory_command(self.db,"sync-batch",request.command)
        prior=self.db.execute("SELECT * FROM lb.sync_batch WHERE command_key=%s",(request.command,)).fetchone()
        if prior and prior["request_hash"]!=fingerprint: raise PersistenceError("idempotency_conflict")
        if prior and prior["report"] is not None: return prior
        binding=PgCatalogRepository(self.db).qualify()
        cp=self._header(request.checkpoint_id,binding)
        if prior and prior["catalog_fingerprint"]!=binding.fingerprint: raise PersistenceError("catalog_changed")
        other=self.db.execute("SELECT id FROM lb.sync_batch WHERE checkpoint_id=%s AND status='running'",
                              (request.checkpoint_id,)).fetchone()
        if other and (not prior or prior["id"]!=other["id"]): raise PersistenceError("sync_batch_in_progress")
        lease=self.sync.claim_lease(request.checkpoint_id,binding,300)
        if prior:
            self.db.execute("UPDATE lb.sync_batch SET lease_token=%s WHERE id=%s",(lease.token,prior["id"]))
            return {**prior,"lease_token":lease.token}
        identifier=uuid4()
        insert(self.db,"sync_batch",id=identifier,checkpoint_id=request.checkpoint_id,command_key=request.command,
               request_hash=fingerprint,catalog_fingerprint=binding.fingerprint,policy=Jsonb(policy),
               cursor_start=cp["cursor_sequence"],review_start=cp["review_next"],
               review_targets=Jsonb(review_targets(cp["anchor"],cp["cursor_sequence"],cp["review_next"],policy["review_window"])),
               lease_token=lease.token,status="running",started_at=cp["now"])
        self.observe("after_batch_open")
        return self.db.execute("SELECT * FROM lb.sync_batch WHERE id=%s",(identifier,)).fetchone()

    def _lock(self,batch_id,token,expected=None):
        binding=PgCatalogRepository(self.db).qualify()
        info=self.db.execute("SELECT checkpoint_id FROM lb.sync_batch WHERE id=%s",(batch_id,)).fetchone()
        if not info: raise PersistenceError("sync_batch_not_found")
        cp=self.sync._checkpoint(info["checkpoint_id"],binding)
        batch=self.db.execute("SELECT * FROM lb.sync_batch WHERE id=%s FOR UPDATE",(batch_id,)).fetchone()
        if batch["status"]!="running": raise PersistenceError("sync_batch_not_running")
        if binding.fingerprint!=batch["catalog_fingerprint"]: raise PersistenceError("catalog_changed")
        if token!=batch["lease_token"] or token!=cp["lease_token"] or cp["lease_until"]<=cp["now"]:
            raise PersistenceError("lease_lost")
        if expected is not None and cp["cursor_sequence"]!=expected: raise PersistenceError("checkpoint_conflict")
        return batch,cp

    def heartbeat(self,batch_id,token):
        batch,cp=self._lock(batch_id,token)
        if cp["cooldown_until"] is not None and cp["cooldown_until"]>cp["now"]: raise PersistenceError("source_cooldown")
        changed=self.db.execute("""UPDATE lb.sync_checkpoint SET lease_until=clock_timestamp()+interval '300 seconds',row_version=row_version+1
            WHERE id=%s AND lease_token=%s AND lease_until>clock_timestamp()""",(cp["id"],token))
        if changed.rowcount!=1: raise PersistenceError("lease_lost")

    def snapshot(self,batch_id,token):
        batch,cp=self._lock(batch_id,token)
        operations=self.db.execute("SELECT * FROM lb.sync_batch_operation WHERE batch_id=%s ORDER BY ordinal",(batch_id,)).fetchall()
        return {"batch":batch,"operations":operations,"cursor":cp["cursor_sequence"]}

    def reserve(self,batch_id,token,planned):
        batch,cp=self._lock(batch_id,token)
        if self.db.execute("SELECT 1 FROM lb.sync_batch_operation WHERE batch_id=%s AND state='pending'",(batch_id,)).fetchone():
            raise PersistenceError("operation_in_progress")
        ordinal=self.db.execute("SELECT count(*)+1 AS n FROM lb.sync_batch_operation WHERE batch_id=%s",(batch_id,)).fetchone()["n"]
        identifier=uuid4()
        insert(self.db,"sync_batch_operation",id=identifier,batch_id=batch_id,ordinal=ordinal,phase=planned["phase"],
               contest=planned["contest"],expected_cursor=cp["cursor_sequence"],review_after=planned["review_after"],
               reuse_id=planned["reuse_id"],capture_key="sync-capture:"+digest(str(identifier)) if planned["reuse_id"] is None else None,
               state="pending",created_at=cp["now"])
        self.observe("after_operation_reserved")
        return self.db.execute("SELECT * FROM lb.sync_batch_operation WHERE id=%s",(identifier,)).fetchone()

    def attach(self,batch_id,token,operation,receipt):
        self._lock(batch_id,token)
        row=self.db.execute("SELECT receipt_id FROM lb.sync_batch_operation WHERE id=%s AND batch_id=%s",(operation,batch_id)).fetchone()
        if not row or row["receipt_id"] not in (None,receipt): raise PersistenceError("idempotency_conflict")
        if row["receipt_id"] is None:
            self.db.execute("UPDATE lb.sync_batch_operation SET receipt_id=%s WHERE id=%s",(receipt,operation))

    def prepare_operation(self,batch_id,token,operation):
        self._lock(batch_id,token)
        row=self.db.execute("SELECT * FROM lb.sync_batch_operation WHERE id=%s AND batch_id=%s FOR UPDATE",(operation,batch_id)).fetchone()
        if not row or row["state"]!="pending" or not row["receipt_id"]: raise PersistenceError("invalid_batch_operation")
        key="sync-process:"+digest({"operation":str(operation),"token":token})
        self.db.execute("UPDATE lb.sync_batch_operation SET processing_key=%s,lease_token=%s WHERE id=%s",(key,token,operation))
        return {**row,"processing_key":key,"lease_token":token}

    def phase(self,intent,receipt):
        row=self.db.execute("""SELECT o.* FROM lb.sync_batch_operation o JOIN lb.sync_batch b ON b.id=o.batch_id
            WHERE o.id=%s AND b.checkpoint_id=%s AND o.receipt_id=%s AND o.expected_cursor=%s""",
            (intent.operation_id,intent.checkpoint_id,receipt,intent.expected_cursor)).fetchone()
        if not row: raise PersistenceError("invalid_batch_operation")
        return row["phase"]

    def lock_operation(self,intent,binding,key):
        info=self.db.execute("SELECT batch_id FROM lb.sync_batch_operation WHERE id=%s",(intent.operation_id,)).fetchone()
        if not info: raise PersistenceError("invalid_batch_operation")
        batch,cp=self._lock(info["batch_id"],intent.lease_token,intent.expected_cursor)
        op=self.db.execute("SELECT * FROM lb.sync_batch_operation WHERE id=%s FOR UPDATE",(intent.operation_id,)).fetchone()
        if (op["state"]!="pending" or op["processing_key"]!=key or op["lease_token"]!=intent.lease_token
                or batch["checkpoint_id"]!=intent.checkpoint_id): raise PersistenceError("invalid_batch_operation")
        return cp,op

    def complete_operation(self,intent,op,observation,outcome):
        accepted=observation["revision_id"] is not None
        sequence=None
        if accepted:
            row=self.db.execute("""SELECT value FROM lb.draw_identity WHERE draw_id=%s AND namespace='official_draw_number'
                AND assurance='official' AND active""",(observation["draw_id"],)).fetchone()
            if not row: raise PersistenceError("identity_conflict")
            sequence=int(row["value"])
        self.db.execute("""UPDATE lb.sync_batch_operation SET state='done',observation_id=%s,outcome=%s,
            observed_sequence=%s,completed_at=clock_timestamp() WHERE id=%s""",
            (observation["observation_id"],outcome,sequence,op["id"]))
        if accepted and op["phase"]=="discovery":
            self.db.execute("UPDATE lb.sync_batch SET latest_sequence=%s WHERE id=%s",(sequence,op["batch_id"]))
        self.observe("after_batch_operation")

    def release(self,batch_id,token):
        row=self.db.execute("SELECT checkpoint_id FROM lb.sync_batch WHERE id=%s",(batch_id,)).fetchone()
        if not row: return
        cp=self.db.execute("SELECT *,clock_timestamp() AS now FROM lb.sync_checkpoint WHERE id=%s FOR UPDATE",(row["checkpoint_id"],)).fetchone()
        if cp["lease_token"]==token and cp["lease_until"] is not None and cp["lease_until"]>cp["now"]:
            self.db.execute("UPDATE lb.sync_checkpoint SET lease_until=clock_timestamp(),row_version=row_version+1 WHERE id=%s",(cp["id"],))

    def finish(self,batch_id,token,reason):
        batch,cp=self._lock(batch_id,token)
        operations=self.db.execute("""SELECT o.*,c.http_status FROM lb.sync_batch_operation o
            LEFT JOIN lb.capture_receipt c ON c.id=o.receipt_id WHERE o.batch_id=%s ORDER BY o.ordinal""",(batch_id,)).fetchall()
        if reason=="quarantined" and operations[-1]["http_status"]==429: reason="source_cooldown"
        status="completed" if reason in ("caught_up","budget_exhausted") else "stopped"
        report={"report_version":"mega-sena-sql-sync-v1","batch_id":str(batch_id),"status":status,"stop_reason":reason,
            "cursor_before":batch["cursor_start"],"cursor_after":cp["cursor_sequence"],"review_next":cp["review_next"],
            "latest_observed":batch["latest_sequence"],"request_slots_used":sum(o["reuse_id"] is None for o in operations),
            "cooldown_until":cp["cooldown_until"].isoformat() if cp["cooldown_until"] else None,
            "policy":batch["policy"],"remaining":max(0,batch["latest_sequence"]-cp["cursor_sequence"]) if batch["latest_sequence"] is not None else None,
            "operations":[{"ordinal":o["ordinal"],"phase":o["phase"],"contest":o["contest"],"observed":o["observed_sequence"],
                "outcome":o["outcome"],"reused_discovery":o["reuse_id"] is not None,
                "http_status":o["http_status"],
                "receipt_id":str(o["receipt_id"]) if o["receipt_id"] else None,
                "observation_id":str(o["observation_id"]) if o["observation_id"] else None} for o in operations]}
        self.db.execute("""UPDATE lb.sync_batch SET status=%s,stop_reason=%s,report=%s,finished_at=clock_timestamp() WHERE id=%s""",
                        (status,reason,Jsonb(report),batch_id))
        self.release(batch_id,token)
        self.observe("after_batch_finished")
        return report
