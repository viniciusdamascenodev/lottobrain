"""Metadados T1/T2; HTTP e escrita de bytes ficam fora destes métodos."""
from uuid import uuid4

from psycopg.types.json import Jsonb

from app.application.persistence import CaptureTicket, PersistenceError, Receipt
from app.infrastructure.postgres.catalog import ENDPOINT
from app.infrastructure.postgres.common import advisory_command, insert


class PgCaptureRepository:
    def __init__(self, db):
        self.db = db

    def start(self, binding, key, request_hash, contest):
        advisory_command(self.db, "acquire", key)
        run = self.db.execute("SELECT id,request_hash FROM lb.ingestion_run WHERE source_id=%s AND idempotency_key=%s FOR UPDATE",
                              (binding.source_id,key)).fetchone()
        if run:
            if run["request_hash"] != request_hash:
                raise PersistenceError("idempotency_conflict")
            row = self.db.execute("""SELECT f.id,c.id AS receipt_id,f.error_code FROM lb.fetch_attempt f
                LEFT JOIN lb.capture_receipt c ON c.fetch_attempt_id=f.id WHERE f.run_id=%s AND f.ordinal=1""",(run["id"],)).fetchone()
            if not row:
                raise PersistenceError("capture_in_progress")
            return CaptureTicket(run["id"],row["id"],row["receipt_id"],row["error_code"] or ("capture_in_progress" if not row["receipt_id"] else None))
        if self.db.execute("""SELECT 1 FROM lb.capture_receipt c JOIN lb.fetch_attempt f ON f.id=c.fetch_attempt_id
            WHERE c.source_id=%s AND c.http_status=429 AND f.finished_at > clock_timestamp()-interval '15 minutes' LIMIT 1""",
            (binding.source_id,)).fetchone() or self.db.execute("SELECT 1 FROM lb.sync_checkpoint WHERE source_id=%s AND cooldown_until > clock_timestamp() LIMIT 1",(binding.source_id,)).fetchone():
            raise PersistenceError("source_cooldown")
        now = self.db.execute("SELECT clock_timestamp() AS now").fetchone()["now"]
        run_id = insert(self.db,"ingestion_run",id=uuid4(),lottery_id=binding.lottery_id,source_id=binding.source_id,
            idempotency_key=key,request_hash=request_hash,source_config_snapshot=Jsonb(binding.source_snapshot),
            mode="manual_sql",status="running",started_at=now,correlation_id=uuid4())
        attempt = insert(self.db,"fetch_attempt",id=uuid4(),run_id=run_id,source_id=binding.source_id,lottery_id=binding.lottery_id,
            ordinal=1,requested_identity=str(contest) if contest is not None else None,
            url=ENDPOINT if contest is None else f"{ENDPOINT}/{contest}",started_at=now,outcome="running")
        return CaptureTicket(run_id,attempt,fresh=True)

    def complete(self, binding, ticket, response, sha256, object_key):
        attempt = self.db.execute("SELECT * FROM lb.fetch_attempt WHERE id=%s FOR UPDATE",(ticket.attempt_id,)).fetchone()
        if not attempt or attempt["run_id"] != ticket.run_id or attempt["source_id"] != binding.source_id:
            raise PersistenceError("evidence_missing")
        existing = self.db.execute("""SELECT c.id,a.sha256 FROM lb.capture_receipt c JOIN lb.raw_artifact a ON a.id=c.artifact_id
            WHERE c.fetch_attempt_id=%s""",(ticket.attempt_id,)).fetchone()
        if existing:
            if existing["sha256"] != sha256 or attempt["http_status"] != response.status:
                raise PersistenceError("idempotency_conflict")
            return existing["id"]
        if attempt["outcome"] != "running" or attempt["url"] != response.url:
            raise PersistenceError("capture_conflict")
        self.db.execute("""INSERT INTO lb.raw_artifact(id,sha256,byte_count,object_key,storage_state,registered_at)
            VALUES (%s,%s,%s,%s,'available',clock_timestamp()) ON CONFLICT(sha256) DO NOTHING""",
            (uuid4(),sha256,len(response.body),object_key))
        artifact = self.db.execute("SELECT id,byte_count,object_key,storage_state FROM lb.raw_artifact WHERE sha256=%s",(sha256,)).fetchone()
        if not artifact or (artifact["byte_count"],artifact["object_key"],artifact["storage_state"]) != (len(response.body),object_key,"available"):
            raise PersistenceError("artifact_metadata_conflict")
        self.db.execute("UPDATE lb.fetch_attempt SET outcome='response',http_status=%s,finished_at=clock_timestamp() WHERE id=%s",
                        (response.status,ticket.attempt_id))
        return insert(self.db,"capture_receipt",id=uuid4(),lottery_id=binding.lottery_id,source_id=binding.source_id,
            fetch_attempt_id=ticket.attempt_id,artifact_id=artifact["id"],capture_kind="http",captured_at=response.captured_at,
            effective_url=response.url,http_status=response.status,content_type=response.content_type,byte_count=len(response.body))

    def receipt(self, receipt_id):
        row = self.db.execute("""SELECT c.id,f.run_id,a.sha256,a.object_key,c.byte_count,c.http_status,c.content_type,
            c.captured_at,c.effective_url,f.requested_identity,c.source_id FROM lb.capture_receipt c
            JOIN lb.raw_artifact a ON a.id=c.artifact_id JOIN lb.fetch_attempt f ON f.id=c.fetch_attempt_id
            WHERE c.id=%s AND c.capture_kind='http' AND a.storage_state='available'""",(receipt_id,)).fetchone()
        if not row:
            raise PersistenceError("evidence_missing")
        return Receipt(row["id"],row["run_id"],row["sha256"],row["object_key"],row["byte_count"],row["http_status"],
                       row["content_type"],row["captured_at"],row["effective_url"],
                       int(row["requested_identity"]) if row["requested_identity"] is not None else None,row["source_id"])

    def fail(self, ticket, code):
        # Códigos fechados: não persistir exceção de rede/URL/credencial arbitrária.
        if code not in ("http.transport_failure","unexpected_response_url","response_too_large","invalid_content_length","truncated_response"):
            code = "http.transport_failure"
        self.db.execute("""UPDATE lb.fetch_attempt SET outcome='transport_error',error_code=%s,finished_at=clock_timestamp()
            WHERE id=%s AND outcome='running'""",(code,ticket.attempt_id))
        self.db.execute("UPDATE lb.ingestion_run SET status='failed',finished_at=clock_timestamp() WHERE id=%s AND status='running'",(ticket.run_id,))

    def finish(self, receipt_id, outcome):
        self.db.execute("""UPDATE lb.ingestion_run SET status=%s,finished_at=clock_timestamp() WHERE status='running' AND id=(
            SELECT f.run_id FROM lb.fetch_attempt f JOIN lb.capture_receipt c ON c.fetch_attempt_id=f.id WHERE c.id=%s)""",
            ("stopped" if outcome == "quarantined" else "completed",receipt_id))
