"""SQL do piloto explícito; não é batch operacional nem substitui o coletor JSON."""
import json
from uuid import uuid4

from psycopg.types.json import Jsonb

from app.application.historical_content import canonical_bytes, digest
from app.application.historical_pilot import CODE_VERSION, JSON_SOURCE
from app.application.mega_sena_bridge import POLICY_VERSION, decide
from app.application.persistence import PersistenceError
from app.infrastructure.postgres.catalog import PgCatalogRepository
from app.infrastructure.postgres.common import advisory_command, insert
from app.infrastructure.postgres.draws import PgDrawRepository
from app.infrastructure.postgres.processing import PgProcessingRepository


def _row_key(run, row, namespace="pilot-row"):
    return namespace + ":" + digest({"run":str(run),"locator":row.locator})


class PgHistoricalDrawRepository(PgDrawRepository):
    """Escrita conservadora comum ao piloto e à importação completa Mega-Sena."""
    def __init__(self, db, observe, plan, row, registration, claim, *, observation_schema="historical-pilot-observation-v1"):
        super().__init__(db,observe)
        self.plan, self.row, self.registration, self.claim = plan, row, registration, claim
        self.observation_schema = observation_schema

    def _number(self, content):
        identity = content["identity"]
        return identity["value"] if isinstance(identity,dict) else identity

    def _apply(self, binding, processing_id, draw_id, content, content_hash, source_texts, *, evidence=None):
        self.observe("before_draw_lock")
        draw = self.db.execute("SELECT * FROM lb.draw WHERE id=%s AND lottery_id=%s FOR UPDATE",
                               (draw_id,binding.lottery_id)).fetchone()
        self.observe("after_draw_lock")
        if not draw:
            raise PersistenceError("identity_conflict")
        head = self.db.execute("SELECT id,revision_no,canonicalization_version,content_hash FROM lb.draw_revision WHERE id=%s",
                               (draw["latest_candidate_revision_id"],)).fetchone()
        if not head and self.db.execute("SELECT 1 FROM lb.draw_revision WHERE draw_id=%s",(draw_id,)).fetchone():
            raise PersistenceError("invalid_revision")
        previous = self.read_content(head["id"],allowed_version=head["canonicalization_version"]) if head else None
        decision, comparison = decide(previous,content)
        version = head["canonicalization_version"] if decision == "support" else content["schema_version"]
        processing_id = self.claim(version)
        payload = {"schema_version":self.observation_schema, "policy_version":POLICY_VERSION,
            "plan_hash":self.plan.fingerprint, "reconciliation":decision, "comparison":comparison,
            "input_contract":content["schema_version"], "input_hash":content_hash, "input_content":content,
            "evidence_hash":digest(self.row.evidence), "source_evidence":self.row.evidence}
        if len(canonical_bytes(payload)) > 32768:
            raise PersistenceError("pilot_evidence_too_large")
        now = self.db.execute("SELECT clock_timestamp() AS t").fetchone()["t"]
        if decision == "quarantined":
            revision, number, output_hash, outcome = None, None, content_hash, "quarantined"
        elif decision == "support":
            revision, number, output_hash, outcome = head["id"], head["revision_no"], head["content_hash"], "unchanged"
        else:
            number = head["revision_no"] + 1 if head else 1
            revision = self._append(binding,draw_id,number,content,content_hash,source_texts,
                canonicalization_version=version,qualify=lambda:PgCatalogRepository(self.db).qualify(self.plan.source_key))
            # Roundtrip real antes de selar: campos persistidos devem reconstruir o hash.
            if self.read_content(revision,allowed_version=version) != content:
                raise PersistenceError("artifact_hash_mismatch")
            output_hash, outcome = content_hash, "correction_candidate" if head else "new"
        observation = insert(self.db,"candidate_observation",id=uuid4(),processing_run_id=processing_id,
            row_locator=self.row.locator,lottery_id=binding.lottery_id,draw_id=draw_id,revision_id=revision,
            decision=outcome,semantic_hash=output_hash,diagnostic_payload=Jsonb(payload),completed_at=now)
        if decision == "quarantined":
            insert(self.db,"validation_issue",id=uuid4(),processing_run_id=processing_id,observation_id=observation,
                   code="bridge.conflicting_facts",severity="error",field_path="draw")
        self.observe("after_observation")
        if decision in ("new","enrichment"):
            self.db.execute("UPDATE lb.draw_revision SET seal_state='sealed',sealed_at=clock_timestamp() WHERE id=%s",(revision,))
            changed = self.db.execute("UPDATE lb.draw SET latest_candidate_revision_id=%s,row_version=row_version+1 WHERE id=%s AND row_version=%s",
                                      (revision,draw_id,draw["row_version"]))
            if changed.rowcount != 1:
                raise PersistenceError("identity_conflict")
        return {"observation_id":observation,"processing_id":processing_id,"draw_id":draw_id,
                "revision_id":revision,"revision_no":number,"outcome":outcome}


class PgHistoricalPilotRepository:
    # Perfis explícitos, com dois consumidores concretos. O plano piloto mantém
    # os seus próprios limites; o perfil completo é uma subclasse separada.
    run_mode = "historical_pilot"
    code_version = CODE_VERSION
    receipt_schema = "historical-pilot-receipt-v1"
    observation_schema = "historical-pilot-observation-v1"
    command_namespace = "pilot-plan"
    row_namespace = "pilot-row"
    row_event = "after_pilot_row"

    def __init__(self, db, observe):
        self.db, self.observe = db, observe
        self.processing = PgProcessingRepository(db)

    def describe(self, source_key, key):
        binding = PgCatalogRepository(self.db).qualify(source_key)
        run = self.db.execute("SELECT id FROM lb.ingestion_run WHERE source_id=%s AND idempotency_key=%s AND mode=%s",
                              (binding.source_id,key,self.run_mode)).fetchone()
        if not run:
            raise PersistenceError("pilot_plan_not_found")
        receipts = self.db.execute("""SELECT c.legacy_reference,a.object_key,a.sha256,a.byte_count
            FROM lb.ingestion_run run JOIN lb.capture_receipt c ON c.source_id=run.source_id
            JOIN lb.raw_artifact a ON a.id=c.artifact_id
            WHERE run.source_id=%s AND run.idempotency_key=%s AND run.mode=%s
            AND c.capture_kind='legacy_import' AND c.legacy_reference LIKE %s""",
            (binding.source_id,key,self.run_mode,f'%"run_id":"{run["id"]}"%')).fetchall()
        if len(receipts) != 1:
            raise PersistenceError("pilot_plan_not_found")
        receipt = receipts[0]
        return {"manifest":json.loads(receipt["legacy_reference"])["manifest"],
                "object_key":receipt["object_key"],"sha256":receipt["sha256"],"byte_count":receipt["byte_count"]}

    def register(self, plan, key, object_key):
        binding = PgCatalogRepository(self.db).qualify(plan.source_key)
        request_hash = digest({"plan":plan.fingerprint,"catalog":binding.fingerprint})
        advisory_command(self.db,self.command_namespace,key)
        run = self.db.execute("SELECT id,request_hash FROM lb.ingestion_run WHERE source_id=%s AND idempotency_key=%s",
                              (binding.source_id,key)).fetchone()
        if run and run["request_hash"] != request_hash:
            raise PersistenceError("idempotency_conflict")
        if not run:
            now = self.db.execute("SELECT clock_timestamp() AS t").fetchone()["t"]
            run = {"id":insert(self.db,"ingestion_run",id=uuid4(),lottery_id=binding.lottery_id,source_id=binding.source_id,
                idempotency_key=key,request_hash=request_hash,source_config_snapshot=Jsonb(binding.source_snapshot),
                mode=self.run_mode,status="running",started_at=now,correlation_id=uuid4())}
        legacy_reference = canonical_bytes({"schema_version":self.receipt_schema,"run_id":str(run["id"]),
            "manifest":plan.manifest,"catalog_fingerprint":binding.fingerprint}).decode()
        receipt = self.db.execute("SELECT id FROM lb.capture_receipt WHERE source_id=%s AND legacy_reference=%s",
                                  (binding.source_id,legacy_reference)).fetchone()
        if not receipt:
            self.db.execute("""INSERT INTO lb.raw_artifact(id,sha256,byte_count,object_key,storage_state,registered_at)
                VALUES (%s,%s,%s,%s,'available',clock_timestamp()) ON CONFLICT(sha256) DO NOTHING""",
                (uuid4(),plan.sha256,len(plan.body),object_key))
            artifact = self.db.execute("SELECT * FROM lb.raw_artifact WHERE sha256=%s",(plan.sha256,)).fetchone()
            if (artifact["byte_count"],artifact["object_key"],artifact["storage_state"]) != (len(plan.body),object_key,"available"):
                raise PersistenceError("artifact_hash_mismatch")
            receipt = {"id":insert(self.db,"capture_receipt",id=uuid4(),lottery_id=binding.lottery_id,
                source_id=binding.source_id,artifact_id=artifact["id"],capture_kind="legacy_import",
                captured_at=self.db.execute("SELECT clock_timestamp() AS t").fetchone()["t"],
                effective_url=f"urn:lottobrain:legacy:{plan.sha256}",http_status=None,
                content_type="application/json" if plan.source_key == JSON_SOURCE else
                             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                byte_count=len(plan.body),legacy_reference=legacy_reference)}
        return {"run_id":run["id"],"receipt_id":receipt["id"],"request_hash":request_hash,
                "catalog_fingerprint":binding.fingerprint}

    def _observation(self, processing_id, locator):
        return self.db.execute("""SELECT o.id AS observation_id,o.processing_run_id AS processing_id,o.draw_id,
            o.revision_id,r.revision_no,o.decision AS outcome FROM lb.candidate_observation o
            LEFT JOIN lb.draw_revision r ON r.id=o.revision_id WHERE o.processing_run_id=%s AND o.row_locator=%s""",
            (processing_id,locator)).fetchone()

    def process(self, registration, plan, row):
        key = _row_key(registration["run_id"],row,self.row_namespace)
        request_hash = digest({"plan_request":registration["request_hash"],"locator":row.locator})
        prior = self.processing.lock_command(key,request_hash)
        if prior:
            return self._observation(prior["processing_run_id"],row.locator)
        binding = PgCatalogRepository(self.db).qualify(plan.source_key)
        if binding.fingerprint != registration["catalog_fingerprint"]:
            raise PersistenceError("catalog_changed")

        def claim(output_version):
            # Apoio entre contratos usa a versão da revisão; entrada original fica no payload.
            policy = f"{POLICY_VERSION}:{plan.fingerprint}"
            recipe = (registration["receipt_id"],plan.adapter_version,self.code_version,output_version,policy,binding.fingerprint)
            self.db.execute("""INSERT INTO lb.processing_run(id,receipt_id,lottery_id,adapter_version,code_version,
                canonicalization_version,validation_policy_version,catalog_fingerprint,status,started_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'running',clock_timestamp())
                ON CONFLICT(receipt_id,adapter_version,code_version,canonicalization_version,validation_policy_version,catalog_fingerprint)
                DO NOTHING""",(uuid4(),recipe[0],binding.lottery_id,*recipe[1:]))
            processing = self.db.execute("""SELECT id FROM lb.processing_run WHERE receipt_id=%s AND adapter_version=%s
                AND code_version=%s AND canonicalization_version=%s AND validation_policy_version=%s AND catalog_fingerprint=%s FOR UPDATE""",
                recipe).fetchone()
            return processing["id"]

        content, evidence = row.content, row.evidence
        texts = {(m["tier"],m["kind"]):m["source_text"] for m in evidence["money_source_texts"]}
        result = PgHistoricalDrawRepository(self.db,self.observe,plan,row,registration,claim,observation_schema=self.observation_schema).reconcile(
            binding,None,content,digest(content),texts)
        self.processing.record(result["processing_id"],key,request_hash,result["outcome"])
        self.observe(self.row_event)
        return result

    def finish(self, registration, plan):
        # Ledger de comandos por localizador é a retomada, não max(concurso).
        outcomes = []
        for row in plan.rows:
            item = self.db.execute("SELECT outcome FROM lb.processing_attempt WHERE command_key=%s",
                                   (_row_key(registration["run_id"],row,self.row_namespace),)).fetchone()
            if not item:
                raise PersistenceError("pilot_incomplete")
            outcomes.append(item["outcome"])
        status = "stopped" if "quarantined" in outcomes else "completed"
        # Bloqueia o mesmo run para dois finalizadores concordarem sem reescrever tempos.
        self.db.execute("SELECT id FROM lb.ingestion_run WHERE id=%s FOR UPDATE",(registration["run_id"],))
        self.db.execute("UPDATE lb.ingestion_run SET status=%s,finished_at=clock_timestamp() WHERE id=%s AND status='running'",
                        (status,registration["run_id"]))
        self.db.execute("UPDATE lb.processing_run SET status='completed',finished_at=clock_timestamp() WHERE receipt_id=%s AND status='running'",
                        (registration["receipt_id"],))
        return {"run_id":str(registration["run_id"]),"receipt_id":str(registration["receipt_id"]),
                "plan_hash":plan.fingerprint,"status":status,"selected_records":len(plan.rows),"outcomes":outcomes}
