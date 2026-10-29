"""Snapshot de auditoria independente da UoW de escrita; nunca adquire lease."""
import psycopg
from psycopg.rows import dict_row

from app.application.persistence import PersistenceError
from app.infrastructure.postgres.catalog import PgCatalogRepository
from app.infrastructure.postgres.content_reader import read_contents


class PgSyncAuditReader:
    def __init__(self, *, connect=None, dsn=None):
        if connect is None and not dsn:
            raise ValueError("Conexão explícita necessária")
        self.connect = connect or (lambda: psycopg.connect(
            dsn, row_factory=dict_row, connect_timeout=10,
            application_name="lottobrain-sync-audit"))

    def read(self, request):
        try:
            return self._read(request)
        except (psycopg.Error, OSError):
            raise PersistenceError("audit_database_unavailable") from None

    def _read(self, request):
        db = None
        try:
            db = self.connect()
            if db.autocommit:
                raise PersistenceError("audit_requires_transactional_connection")
            db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            db.execute("SET LOCAL statement_timeout='20s'")
            db.execute("SET LOCAL lock_timeout='3s'")
            return self._snapshot(db, request)
        finally:
            if db is not None:
                try:
                    db.rollback()
                except Exception:
                    pass  # Fechar encerra a transação; não esconder a falha original.
                finally:
                    db.close()

    def _snapshot(self, db, request):
        snapshot = {"at": db.execute("SELECT transaction_timestamp() AS at").fetchone()["at"],
                    "checkpoint": None, "truncated": [], "contents": {}, "content_errors": {}}
        cp = db.execute("SELECT * FROM lb.sync_checkpoint WHERE id=%s",
                        (request.checkpoint_id,)).fetchone()
        snapshot["checkpoint"] = cp
        if cp is None:
            return snapshot
        snapshot["source"] = db.execute("""SELECT s.*,l.slug FROM lb.data_source s
            JOIN lb.lottery l ON l.id=s.lottery_id WHERE s.id=%s""", (cp["source_id"],)).fetchone()
        try:
            binding = PgCatalogRepository(db).qualify()
            snapshot["current_catalog"] = binding.fingerprint
        except PersistenceError:
            snapshot["current_catalog"] = None
        snapshot["baseline"] = db.execute("SELECT * FROM lb.ingestion_baseline WHERE id=%s",
                                          (cp["baseline_id"],)).fetchone()
        activation = db.execute("SELECT * FROM lb.baseline_activation WHERE checkpoint_id=%s",
                                (cp["id"],)).fetchone()
        snapshot["activation"] = activation
        snapshot["historical_run"] = db.execute("SELECT * FROM lb.ingestion_run WHERE id=%s",
            (activation["historical_run_id"],)).fetchone() if activation else None
        batches = db.execute("""SELECT * FROM lb.sync_batch WHERE checkpoint_id=%s
            ORDER BY started_at,id LIMIT %s""", (cp["id"], request.max_batches + 1)).fetchall()
        steps = db.execute("""SELECT * FROM lb.sync_step WHERE checkpoint_id=%s
            ORDER BY sequence_no LIMIT %s""", (cp["id"], request.max_steps + 1)).fetchall()
        for name, rows, limit in (("batches", batches, request.max_batches),
                                   ("steps", steps, request.max_steps)):
            if len(rows) > limit:
                snapshot["truncated"].append(name)
            snapshot[name] = rows[:limit]
        batch_ids = [b["id"] for b in snapshot["batches"]]
        operations = db.execute("""SELECT * FROM lb.sync_batch_operation WHERE batch_id=ANY(%s)
            ORDER BY batch_id,ordinal""", (batch_ids,)).fetchall() if batch_ids else []
        snapshot["operations"] = operations
        keys = [op["capture_key"] for op in operations if op["capture_key"]]
        captures = db.execute("""SELECT r.id AS run_id,r.idempotency_key AS capture_key,
            r.request_hash,r.source_id,r.lottery_id,r.status AS run_status,
            f.id AS attempt_id,f.ordinal,f.requested_identity,f.outcome,f.error_code,
            f.http_status,c.id AS receipt_id FROM lb.ingestion_run r
            LEFT JOIN lb.fetch_attempt f ON f.run_id=r.id
            LEFT JOIN lb.capture_receipt c ON c.fetch_attempt_id=f.id
            WHERE r.idempotency_key=ANY(%s) AND r.source_id=%s ORDER BY r.id,f.ordinal
            LIMIT 20001""", (keys, cp["source_id"])).fetchall() if keys else []
        if len(captures) > 20000:
            snapshot["truncated"].append("captures")
        snapshot["captures"] = captures[:20000]
        observation_ids = list({row["observation_id"] for row in snapshot["steps"] + operations
                                if row["observation_id"]})
        observations = db.execute("SELECT * FROM lb.candidate_observation WHERE id=ANY(%s)",
                                  (observation_ids,)).fetchall() if observation_ids else []
        snapshot["observations"] = observations
        process_ids = list({o["processing_run_id"] for o in observations})
        snapshot["processing"] = db.execute("SELECT * FROM lb.processing_run WHERE id=ANY(%s)",
                                            (process_ids,)).fetchall() if process_ids else []
        process_keys = [op["processing_key"] for op in operations if op["processing_key"]]
        attempts = db.execute("""SELECT * FROM lb.processing_attempt
            WHERE command_key=ANY(%s) OR processing_run_id=ANY(%s)
            ORDER BY command_key LIMIT 20001""", (process_keys, process_ids)).fetchall() if process_keys or process_ids else []
        if len(attempts) > 20000:
            snapshot["truncated"].append("processing_attempts")
        snapshot["attempts"] = attempts[:20000]
        receipt_ids = {op["receipt_id"] for op in operations if op["receipt_id"]}
        receipt_ids.update(c["receipt_id"] for c in captures if c["receipt_id"])
        receipt_ids.update(p["receipt_id"] for p in snapshot["processing"])
        if activation:
            receipt_ids.add(activation["historical_receipt_id"])
        snapshot["receipts"] = db.execute("SELECT * FROM lb.capture_receipt WHERE id=ANY(%s)",
                                          (list(receipt_ids),)).fetchall() if receipt_ids else []
        artifact_ids = {c["artifact_id"] for c in snapshot["receipts"]}
        if snapshot["baseline"]:
            artifact_ids.add(snapshot["baseline"]["artifact_id"])
        snapshot["artifacts"] = db.execute("SELECT * FROM lb.raw_artifact WHERE id=ANY(%s)",
                                            (list(artifact_ids),)).fetchall() if artifact_ids else []
        revision_ids = list({o["revision_id"] for o in observations if o["revision_id"]})
        snapshot["revisions"] = db.execute("SELECT * FROM lb.draw_revision WHERE id=ANY(%s)",
                                            (revision_ids,)).fetchall() if revision_ids else []
        draw_ids = list({o["draw_id"] for o in observations if o["draw_id"]})
        snapshot["identities"] = db.execute("""SELECT * FROM lb.draw_identity
            WHERE draw_id=ANY(%s) AND namespace='official_draw_number'""",
                                            (draw_ids,)).fetchall() if draw_ids else []
        # Um agregado inválido não esconde a evidência dos demais.
        for offset in range(0, len(revision_ids), 500):
            chunk = revision_ids[offset:offset + 500]
            try:
                snapshot["contents"].update(read_contents(db, chunk))
            except PersistenceError:
                for identifier in chunk:
                    try:
                        snapshot["contents"].update(read_contents(db, [identifier]))
                    except PersistenceError:
                        snapshot["content_errors"][identifier] = "relational_content_invalid"
        return snapshot
