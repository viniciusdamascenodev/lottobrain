"""Receita, tentativas e observações: idempotência não é unicidade de conteúdo."""
from uuid import uuid4

from psycopg.types.json import Jsonb

from app.application.mega_sena_content import CODE_VERSION as LEGACY_CODE, POLICY_VERSION as LEGACY_POLICY, VERSION
from app.application.mega_sena_incremental import CODE_VERSION, POLICY_VERSION
from app.application.persistence import PersistenceError
from app.ingestion.mega_sena_api import ADAPTER_VERSION
from app.infrastructure.postgres.common import advisory_command, insert


class PgProcessingRepository:
    def __init__(self, db):
        self.db = db

    def lock_command(self, key, request_hash, *, compatible_hashes=()):
        advisory_command(self.db,"process",key)
        row = self.db.execute("""SELECT a.outcome,a.request_hash,a.processing_run_id FROM lb.processing_attempt a
            WHERE command_key=%s""",(key,)).fetchone()
        if row and row["request_hash"] not in (request_hash,*compatible_hashes):
            raise PersistenceError("idempotency_conflict")
        return row

    def claim(self, binding, receipt):
        # Uma interpretação antiga concluída permanece replay, inclusive sob outra
        # chave. Não reprocessar um raw antigo como se fosse uma captura posterior.
        legacy = self.db.execute("""SELECT p.id FROM lb.processing_run p WHERE p.receipt_id=%s AND p.lottery_id=%s
            AND p.adapter_version=%s AND p.code_version=%s AND p.canonicalization_version=%s
            AND p.validation_policy_version=%s AND p.catalog_fingerprint=%s AND p.status='completed'
            AND EXISTS (SELECT 1 FROM lb.candidate_observation o WHERE o.processing_run_id=p.id AND o.row_locator='/')
            FOR UPDATE""",(receipt.id,binding.lottery_id,ADAPTER_VERSION,LEGACY_CODE,VERSION,LEGACY_POLICY,binding.fingerprint)).fetchone()
        if legacy:
            return legacy["id"]
        recipe = (receipt.id,binding.lottery_id,ADAPTER_VERSION,CODE_VERSION,VERSION,POLICY_VERSION,binding.fingerprint)
        self.db.execute("""INSERT INTO lb.processing_run(id,receipt_id,lottery_id,adapter_version,code_version,
            canonicalization_version,validation_policy_version,catalog_fingerprint,status,started_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'running',clock_timestamp())
            ON CONFLICT(receipt_id,adapter_version,code_version,canonicalization_version,validation_policy_version,catalog_fingerprint) DO NOTHING""",
            (uuid4(),*recipe))
        return self.db.execute("""SELECT id FROM lb.processing_run WHERE receipt_id=%s AND lottery_id=%s AND adapter_version=%s
            AND code_version=%s AND canonicalization_version=%s AND validation_policy_version=%s AND catalog_fingerprint=%s FOR UPDATE""",recipe).fetchone()["id"]

    def observation(self, processing_id):
        return self.db.execute("""SELECT o.id AS observation_id,o.draw_id,o.revision_id,o.decision AS outcome,r.revision_no
            FROM lb.candidate_observation o LEFT JOIN lb.draw_revision r ON r.id=o.revision_id
            WHERE o.processing_run_id=%s AND o.row_locator='/'""",(processing_id,)).fetchone()

    def record(self, processing_id, key, request_hash, outcome):
        ordinal = self.db.execute("SELECT coalesce(max(ordinal),0)+1 AS n FROM lb.processing_attempt WHERE processing_run_id=%s",(processing_id,)).fetchone()["n"]
        now = self.db.execute("SELECT clock_timestamp() AS now").fetchone()["now"]
        insert(self.db,"processing_attempt",id=uuid4(),processing_run_id=processing_id,ordinal=ordinal,
               command_key=key,request_hash=request_hash,outcome=outcome,started_at=now,finished_at=now)

    def quarantine(self, binding, processing_id, issues):
        now = self.db.execute("SELECT clock_timestamp() AS now").fetchone()["now"]
        observation = insert(self.db,"candidate_observation",id=uuid4(),processing_run_id=processing_id,row_locator="/",
            lottery_id=binding.lottery_id,decision="quarantined",completed_at=now,
            diagnostic_payload=Jsonb({"codes":[i.code for i in issues]}))
        for issue in issues:
            insert(self.db,"validation_issue",id=uuid4(),processing_run_id=processing_id,observation_id=observation,
                   code=issue.code,severity="error",field_path=issue.path)
        return dict(observation_id=observation,draw_id=None,revision_id=None,revision_no=None,outcome="quarantined")

    def complete(self, processing_id):
        # Replay possui sua própria tentativa; não reescreve o instante original
        # em que a interpretação ficou disponível.
        self.db.execute("UPDATE lb.processing_run SET status='completed',finished_at=clock_timestamp() WHERE id=%s AND status='running'",(processing_id,))
