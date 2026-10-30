"""Transação comum das seis modalidades, sobre o conteúdo/ledger SQL existentes."""

from uuid import uuid4

from psycopg.types.json import Jsonb

from app.application.historical_content import VERSION, canonical_bytes, digest
from app.application.mega_sena_bridge import decide as bridge_decision
from app.application.persistence import PersistenceError
from app.infrastructure.postgres.common import advisory_command, insert
from app.infrastructure.postgres.content_reader import read_contents
from app.infrastructure.postgres.draws import PgDrawRepository
from app.infrastructure.postgres.processing import PgProcessingRepository
from app.infrastructure.postgres.profile_catalog import PgProfileCatalogRepository

CODE_VERSION = "etapa-6-qualified-result-v1"


class PgResultRepository:
    def __init__(self, db, observe):
        self.db, self.observe = db, observe
        self.catalog = PgProfileCatalogRepository(db)

    def store(self, prepared, key, object_key, *, allow_correction=False):
        content, evidence = prepared.row.content, prepared.row.evidence
        binding = self.catalog.qualify(prepared.source_key, content["rule_version"])
        request_hash = prepared.request_hash(binding.fingerprint, allow_correction)
        processing = PgProcessingRepository(self.db)
        prior = processing.lock_command(key, request_hash)
        if prior:
            result = self.db.execute(
                """SELECT o.id AS observation_id,o.draw_id,o.revision_id,
                o.decision AS outcome,r.revision_no FROM lb.candidate_observation o
                LEFT JOIN lb.draw_revision r ON r.id=o.revision_id
                WHERE o.processing_run_id=%s AND o.row_locator=%s""",
                (prior["processing_run_id"], prepared.row.locator),
            ).fetchone()
            if not result:
                raise PersistenceError("invalid_revision")
            return dict(result)
        alias = content["identity"]
        advisory_command(
            self.db,
            "qualified-result-identity",
            f"{binding.lottery_id}:{alias['namespace']}:{alias['value']}",
        )
        identity = self.db.execute(
            """SELECT draw_id,assurance,active FROM lb.draw_identity
            WHERE lottery_id=%s AND namespace=%s AND value=%s""",
            (binding.lottery_id, alias["namespace"], alias["value"]),
        ).fetchone()
        if identity and (not identity["active"] or identity["assurance"] != alias["assurance"]):
            raise PersistenceError("identity_conflict")
        draw_id = (
            identity["draw_id"]
            if identity
            else insert(
                self.db,
                "draw",
                id=uuid4(),
                lottery_id=binding.lottery_id,
                created_at=self.db.execute("SELECT clock_timestamp() AS t").fetchone()["t"],
            )
        )
        draw = self.db.execute(
            "SELECT * FROM lb.draw WHERE id=%s FOR UPDATE", (draw_id,)
        ).fetchone()
        head = self.db.execute(
            "SELECT * FROM lb.draw_revision WHERE id=%s", (draw["latest_candidate_revision_id"],)
        ).fetchone()
        if (
            not head
            and self.db.execute(
                "SELECT 1 FROM lb.draw_revision WHERE draw_id=%s", (draw_id,)
            ).fetchone()
        ):
            raise PersistenceError("invalid_revision")
        previous = read_contents(self.db, [head["id"]])[head["id"]] if head else None
        incoming_hash = digest(content)
        decision = "new"
        if head:
            if head["canonicalization_version"] != VERSION:
                decision, _ = bridge_decision(previous, content)
            elif incoming_hash == head["content_hash"]:
                decision = "support"
            else:
                decision = "correction" if allow_correction else "quarantined"
        output_version = head["canonicalization_version"] if decision == "support" else VERSION
        now = self.db.execute("SELECT clock_timestamp() AS t").fetchone()["t"]
        run = insert(
            self.db,
            "ingestion_run",
            id=uuid4(),
            lottery_id=binding.lottery_id,
            source_id=binding.source_id,
            idempotency_key=key,
            request_hash=request_hash,
            source_config_snapshot=Jsonb(binding.source_snapshot),
            mode="qualified_result",
            status="running",
            started_at=now,
            correlation_id=uuid4(),
        )
        self.db.execute(
            """INSERT INTO lb.raw_artifact(id,sha256,byte_count,object_key,storage_state,registered_at)
            VALUES (%s,%s,%s,%s,'available',clock_timestamp()) ON CONFLICT(sha256) DO NOTHING""",
            (uuid4(), prepared.sha256, len(prepared.body), object_key),
        )
        artifact = self.db.execute(
            "SELECT * FROM lb.raw_artifact WHERE sha256=%s", (prepared.sha256,)
        ).fetchone()
        if (artifact["byte_count"], artifact["object_key"], artifact["storage_state"]) != (
            len(prepared.body),
            object_key,
            "available",
        ):
            raise PersistenceError("artifact_hash_mismatch")
        receipt = insert(
            self.db,
            "capture_receipt",
            id=uuid4(),
            lottery_id=binding.lottery_id,
            source_id=binding.source_id,
            artifact_id=artifact["id"],
            capture_kind="legacy_import",
            captured_at=now,
            effective_url=f"urn:lottobrain:qualified:{prepared.sha256}",
            content_type="application/octet-stream",
            byte_count=len(prepared.body),
            legacy_reference=canonical_bytes(
                {
                    "schema_version": "qualified-result-receipt-v1",
                    "run_id": str(run),
                    "artifact_name": prepared.artifact_name,
                }
            ).decode(),
        )
        pid = insert(
            self.db,
            "processing_run",
            id=uuid4(),
            receipt_id=receipt,
            lottery_id=binding.lottery_id,
            adapter_version=prepared.adapter_version,
            code_version=CODE_VERSION,
            canonicalization_version=output_version,
            validation_policy_version=CODE_VERSION,
            catalog_fingerprint=binding.fingerprint,
            status="running",
            started_at=now,
        )
        revision, number = None, None
        if decision == "support":
            revision, number, output_hash = head["id"], head["revision_no"], head["content_hash"]
            outcome = "unchanged"
        elif decision == "quarantined":
            output_hash, outcome = incoming_hash, "quarantined"
        else:
            number = head["revision_no"] + 1 if head else 1
            texts = {
                (m["tier"], m["kind"]): m["source_text"] for m in evidence["money_source_texts"]
            }
            revision = PgDrawRepository(self.db, self.observe)._append(
                binding,
                draw_id,
                number,
                content,
                incoming_hash,
                texts,
                canonicalization_version=VERSION,
                qualify=lambda: self.catalog.qualify(prepared.source_key, content["rule_version"]),
            )
            if read_contents(self.db, [revision])[revision] != content:
                raise PersistenceError("artifact_hash_mismatch")
            output_hash, outcome = incoming_hash, "correction_candidate" if head else "new"
        payload = {
            "schema_version": "qualified-result-observation-v1",
            "input_content": content,
            "input_hash": incoming_hash,
            "source_evidence": evidence,
            "evidence_hash": digest(evidence),
            "decision": decision,
            "allow_correction": allow_correction,
        }
        if len(canonical_bytes(payload)) > 32768:
            raise PersistenceError("observation_evidence_too_large")
        observation = insert(
            self.db,
            "candidate_observation",
            id=uuid4(),
            processing_run_id=pid,
            row_locator=prepared.row.locator,
            lottery_id=binding.lottery_id,
            draw_id=draw_id,
            revision_id=revision,
            decision=outcome,
            semantic_hash=output_hash,
            diagnostic_payload=Jsonb(payload),
            completed_at=now,
        )
        if outcome == "quarantined":
            insert(
                self.db,
                "validation_issue",
                id=uuid4(),
                processing_run_id=pid,
                observation_id=observation,
                code="qualified_result.conflicting_facts",
                severity="error",
                field_path="draw",
            )
        self.observe("after_observation")
        if revision and decision not in {"support", "quarantined"}:
            self.db.execute(
                "UPDATE lb.draw_revision SET seal_state='sealed',sealed_at=clock_timestamp() WHERE id=%s",
                (revision,),
            )
            self.db.execute(
                "UPDATE lb.draw SET latest_candidate_revision_id=%s,row_version=row_version+1 WHERE id=%s",
                (revision, draw_id),
            )
        if not identity:
            insert(
                self.db,
                "draw_identity",
                id=uuid4(),
                lottery_id=binding.lottery_id,
                draw_id=draw_id,
                namespace=alias["namespace"],
                value=alias["value"],
                assurance=alias["assurance"],
                active=True,
                evidence_observation_id=observation,
            )
        for reference in evidence["external_references"]:
            prior_reference = self.db.execute(
                """SELECT draw_id FROM lb.external_draw_reference
                WHERE source_id=%s AND namespace=%s AND value=%s""",
                (binding.source_id, reference["namespace"], reference["value"]),
            ).fetchone()
            if prior_reference and prior_reference["draw_id"] != draw_id:
                raise PersistenceError("identity_conflict")
            if not prior_reference:
                insert(
                    self.db,
                    "external_draw_reference",
                    id=uuid4(),
                    lottery_id=binding.lottery_id,
                    source_id=binding.source_id,
                    draw_id=draw_id,
                    namespace=reference["namespace"],
                    value=reference["value"],
                    evidence_observation_id=observation,
                )
        processing.record(pid, key, request_hash, outcome)
        self.db.execute(
            "UPDATE lb.processing_run SET status='completed',finished_at=clock_timestamp() WHERE id=%s",
            (pid,),
        )
        self.db.execute(
            "UPDATE lb.ingestion_run SET status=%s,finished_at=clock_timestamp() WHERE id=%s",
            ("stopped" if outcome == "quarantined" else "completed", run),
        )
        self.observe("after_qualified_result")
        return {
            "observation_id": observation,
            "draw_id": draw_id,
            "revision_id": revision,
            "revision_no": number,
            "outcome": outcome,
        }
