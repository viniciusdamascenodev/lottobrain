"""Aprovação atômica e append-only de baseline histórica para o fluxo JSON."""
from uuid import uuid4

from psycopg.types.json import Jsonb

from app.application.activate_mega_sena_baseline import POLICY_VERSION, STREAM_KEY, require_eligible_coverage
from app.application.historical_content import digest
from app.application.historical_import import XLSX_SOURCE
from app.application.persistence import PersistenceError
from app.ingestion.mega_sena_api import SOURCE_KEY
from app.infrastructure.postgres.catalog import PgCatalogRepository
from app.infrastructure.postgres.common import advisory_command, insert
from app.infrastructure.postgres.historical_import import PgHistoricalImportRepository


def _result(row):
    return {"activation_id":str(row["id"]),"baseline_id":str(row["baseline_id"]),
            "checkpoint_id":str(row["checkpoint_id"]),"initial_cursor":2954,"next_contest":2955,
            "coverage_hash":row["coverage_hash"],"plan_hash":row["historical_plan_hash"]}


class PgBaselineRepository:
    def __init__(self, db, observe):
        self.db, self.observe = db, observe

    def activate(self, request, plan):
        self.db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        self.observe("before_baseline_command_lock")
        advisory_command(self.db,"baseline-command",request.command)
        history = PgHistoricalImportRepository(self.db,self.observe)
        saved = history.describe(XLSX_SOURCE,request.history_key)
        if saved["manifest"] != plan.manifest or plan.fingerprint != request.expected_plan_hash:
            raise PersistenceError("historical_manifest_mismatch")
        request_hash = digest({"schema":"baseline-command-v1","historical_run":str(saved["run_id"]),
            "history_key":request.history_key,"plan_hash":plan.fingerprint,"approval_reference":request.approval_reference,
            "target_source":SOURCE_KEY,"stream":STREAM_KEY,"policy":POLICY_VERSION})
        previous = self.db.execute("SELECT * FROM lb.baseline_activation WHERE command_key=%s",(request.command,)).fetchone()
        if previous:
            if previous["request_hash"] != request_hash:
                raise PersistenceError("idempotency_conflict")
            if digest(previous["coverage_report"]) != previous["coverage_hash"]:
                raise PersistenceError("artifact_hash_mismatch")
            # Recuperar a decisão passada não renova catálogo, lease ou cursor.
            return _result(previous)

        binding = PgCatalogRepository(self.db).qualify(SOURCE_KEY)
        advisory_command(self.db,"baseline-source",str(binding.source_id))
        if self.db.execute("SELECT 1 FROM lb.sync_checkpoint WHERE lottery_id=%s AND source_id=%s",
                           (binding.lottery_id,binding.source_id)).fetchone():
            raise PersistenceError("checkpoint_already_initialized")
        registration,report = history.coverage_snapshot(request.history_key,plan)
        require_eligible_coverage(report)
        artifact = self.db.execute("SELECT artifact_id FROM lb.capture_receipt WHERE id=%s",
                                   (registration["receipt_id"],)).fetchone()
        historical_source = self.db.execute("SELECT source_id FROM lb.ingestion_run WHERE id=%s",
                                           (registration["run_id"],)).fetchone()["source_id"]
        clock = self.db.execute("SELECT clock_timestamp() AS now,current_user AS approver").fetchone()
        activation_id,baseline_id,checkpoint_id = uuid4(),uuid4(),uuid4()
        coverage_hash = digest(report)
        insert(self.db,"ingestion_baseline",id=baseline_id,lottery_id=binding.lottery_id,source_id=historical_source,
               artifact_id=artifact["artifact_id"],first_sequence=1,last_sequence=2954,
               manifest_hash=report["expected_records_manifest_sha256"],
               audit_reference=f"urn:lottobrain:baseline-activation:{activation_id}",
               audited_at=clock["now"],materialization_status="loaded")
        self.observe("after_baseline_insert")
        # ON CONFLICT também faz a concorrência sob snapshot antigo falhar com
        # 40001, permitindo o retry transacional limitado já existente na UoW.
        activation = self.db.execute("""INSERT INTO lb.baseline_activation
            (id,baseline_id,lottery_id,historical_source_id,historical_run_id,historical_receipt_id,
             target_source_id,checkpoint_id,stream_key,command_key,request_hash,historical_plan_hash,
             policy_version,target_catalog_fingerprint,target_config_snapshot,coverage_hash,coverage_report,
             approval_reference,approved_by,approved_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT DO NOTHING RETURNING *""",
            (activation_id,baseline_id,binding.lottery_id,historical_source,registration["run_id"],registration["receipt_id"],
             binding.source_id,checkpoint_id,STREAM_KEY,request.command,request_hash,plan.fingerprint,
             POLICY_VERSION,binding.fingerprint,Jsonb(binding.source_snapshot),coverage_hash,Jsonb(report),
             request.approval_reference,clock["approver"],clock["now"])).fetchone()
        if not activation:
            raise PersistenceError("checkpoint_already_initialized")
        self.observe("after_activation_insert")
        insert(self.db,"sync_checkpoint",id=checkpoint_id,lottery_id=binding.lottery_id,source_id=binding.source_id,
               stream_key=STREAM_KEY,strategy="official_numeric_sequence",baseline_id=baseline_id,
               cursor_sequence=2954,review_next=2955)
        self.observe("after_checkpoint_insert")
        return _result(activation)
