"""Reconciliação sob lock do draw; perdedor da identidade desfaz o savepoint inteiro."""
from uuid import uuid4

from psycopg.errors import UniqueViolation
from psycopg.types.json import Jsonb

from app.application.mega_sena_content import VERSION, digest
from app.application.historical_content import VERSION as HISTORICAL_VERSION
from app.application.historical_content import canonical_bytes
from app.application.mega_sena_incremental import POLICY_VERSION, decide_incremental
from app.application.persistence import PersistenceError
from app.infrastructure.postgres.catalog import PgCatalogRepository
from app.infrastructure.postgres.common import insert
from app.infrastructure.postgres.content_reader import read_contents


class PgDrawRepository:
    def __init__(self, db, observe):
        self.db = db
        self.observe = observe

    def _identity(self, binding, number):
        return self.db.execute("""SELECT draw_id,active,assurance FROM lb.draw_identity WHERE lottery_id=%s
            AND namespace='official_draw_number' AND value=%s""",(binding.lottery_id,number)).fetchone()

    def _number(self, content):
        return content["identity"]

    def reconcile(self, binding, processing_id, content, content_hash, source_texts, *, evidence=None):
        identity = self._identity(binding,self._number(content))
        if identity is not None:
            if not identity["active"] or identity["assurance"] != "official":
                raise PersistenceError("identity_conflict")
            result = self._apply(binding,processing_id,identity["draw_id"],content,content_hash,source_texts,evidence=evidence)
            self._reference(binding,result,self._number(content))
            return result
        try:
            with self.db.transaction():  # savepoint: inclui draw/revisão/filhos/observação/alias
                draw_id = insert(self.db,"draw",id=uuid4(),lottery_id=binding.lottery_id,
                                 created_at=self.db.execute("SELECT clock_timestamp() AS t").fetchone()["t"])
                result = self._apply(binding,processing_id,draw_id,content,content_hash,source_texts,evidence=evidence)
                self.observe("before_identity_claim")
                insert(self.db,"draw_identity",id=uuid4(),lottery_id=binding.lottery_id,draw_id=draw_id,
                    namespace="official_draw_number",value=self._number(content),assurance="official",active=True,
                    evidence_observation_id=result["observation_id"])
                self._reference(binding,result,self._number(content))
                return result
        except UniqueViolation as error:
            if error.diag.constraint_name != "draw_identity_lottery_id_namespace_value_key":
                raise
        identity = self._identity(binding,self._number(content))
        if not identity or not identity["active"] or identity["assurance"] != "official":
            raise PersistenceError("identity_conflict")
        result = self._apply(binding,processing_id,identity["draw_id"],content,content_hash,source_texts,evidence=evidence)
        self._reference(binding,result,self._number(content))
        return result

    def _apply(self, binding, processing_id, draw_id, content, content_hash, source_texts, *, evidence=None):
        self.observe("before_draw_lock")
        draw = self.db.execute("SELECT * FROM lb.draw WHERE id=%s AND lottery_id=%s FOR UPDATE",(draw_id,binding.lottery_id)).fetchone()
        if not draw:
            raise PersistenceError("identity_conflict")
        self.observe("after_draw_lock")
        head = self.db.execute("SELECT id,revision_no,content_hash,canonicalization_version FROM lb.draw_revision WHERE id=%s",
                               (draw["latest_candidate_revision_id"],)).fetchone()
        if not head and self.db.execute("SELECT 1 FROM lb.draw_revision WHERE draw_id=%s LIMIT 1",(draw_id,)).fetchone():
            raise PersistenceError("invalid_revision")
        previous = self.read_content(head["id"],allowed_version=head["canonicalization_version"]) if head else None
        decision, comparison = decide_incremental(previous,content)
        payload = {"schema_version":"mega-sena-incremental-observation-v1", "policy_version":POLICY_VERSION,
            "reconciliation":decision,"input_contract":VERSION,"input_hash":content_hash,
            "source_evidence":evidence,"evidence_hash":digest(evidence) if evidence is not None else None,
            "head": {"version":head["canonicalization_version"],"hash":head["content_hash"],"revision_no":head["revision_no"]} if head else None,
            "comparison":comparison}
        if len(canonical_bytes(payload)) > 32768:
            raise PersistenceError("observation_evidence_too_large")
        if decision == "quarantined":
            observation = insert(self.db,"candidate_observation",id=uuid4(),processing_run_id=processing_id,row_locator="/",
                lottery_id=binding.lottery_id,draw_id=draw_id,decision="quarantined",semantic_hash=content_hash,
                diagnostic_payload=Jsonb(payload),completed_at=self.db.execute("SELECT clock_timestamp() AS t").fetchone()["t"])
            insert(self.db,"validation_issue",id=uuid4(),processing_run_id=processing_id,observation_id=observation,
                   code="bridge.incompatible_historical_facts",severity="error",field_path="draw")
            self.observe("after_observation")
            return dict(observation_id=observation,draw_id=draw_id,revision_id=None,revision_no=None,outcome="quarantined")
        changed = decision != "unchanged"
        revision_no = head["revision_no"] + 1 if head and changed else head["revision_no"] if head else 1
        revision_id = self._append(binding,draw_id,revision_no,content,content_hash,source_texts) if changed else head["id"]
        if changed and self.read_content(revision_id) != content:
            raise PersistenceError("artifact_hash_mismatch")
        outcome = "correction_candidate" if head and changed else "new" if changed else "unchanged"
        observation = insert(self.db,"candidate_observation",id=uuid4(),processing_run_id=processing_id,row_locator="/",
            lottery_id=binding.lottery_id,draw_id=draw_id,revision_id=revision_id,decision=outcome,semantic_hash=content_hash,
            diagnostic_payload=Jsonb(payload),completed_at=self.db.execute("SELECT clock_timestamp() AS t").fetchone()["t"])
        self.observe("after_observation")
        if changed:
            self.db.execute("UPDATE lb.draw_revision SET seal_state='sealed',sealed_at=clock_timestamp() WHERE id=%s",(revision_id,))
            updated = self.db.execute("UPDATE lb.draw SET latest_candidate_revision_id=%s,row_version=row_version+1 WHERE id=%s AND row_version=%s",
                                      (revision_id,draw_id,draw["row_version"]))
            if updated.rowcount != 1:
                raise PersistenceError("identity_conflict")
        return dict(observation_id=observation,draw_id=draw_id,revision_id=revision_id,revision_no=revision_no,outcome=outcome)

    def _reference(self, binding, result, number):
        reference = self.db.execute("""SELECT draw_id FROM lb.external_draw_reference WHERE source_id=%s
            AND namespace='official_draw_number' AND value=%s""",(binding.source_id,number)).fetchone()
        if reference and reference["draw_id"] != result["draw_id"]:
            raise PersistenceError("identity_conflict")
        if not reference:
            insert(self.db,"external_draw_reference",id=uuid4(),lottery_id=binding.lottery_id,source_id=binding.source_id,
                draw_id=result["draw_id"],namespace="official_draw_number",value=number,evidence_observation_id=result["observation_id"])

    def _append(self, binding, draw_id, number, content, content_hash, source_texts, *,
                canonicalization_version=VERSION, qualify=None):
        if canonicalization_version not in (VERSION, HISTORICAL_VERSION):
            raise PersistenceError("canonicalization_conflict")
        now = self.db.execute("SELECT clock_timestamp() AS t").fetchone()["t"]
        revision = insert(self.db,"draw_revision",id=uuid4(),draw_id=draw_id,lottery_id=binding.lottery_id,revision_no=number,
            draw_date_local=content["draw_date"],rule_version_id=binding.rule_id,content_hash=content_hash,
            canonicalization_version=canonicalization_version,seal_state="building",created_at=now,
            metadata=Jsonb({**content["metadata"],"_canonical_identity":content["identity"]}))
        # INSERT acima trava a regra pelo guard existente. Agora a releitura é estável
        # frente a edições de componentes/séries/faixas do catálogo.
        if (qualify or PgCatalogRepository(self.db).qualify)().fingerprint != binding.fingerprint:
            raise PersistenceError("catalog_changed")
        self.observe("after_revision")
        series = insert(self.db,"result_series",id=uuid4(),revision_id=revision,rule_version_id=binding.rule_id,
                        lottery_id=binding.lottery_id,series_definition_id=binding.series_id)
        for value in content["series"][0]["components"][0]["values"]:
            insert(self.db,"component_value",result_series_id=series,revision_id=revision,
                series_definition_id=binding.series_id,component_definition_id=binding.component_id,**value)
        for tier in content["prize_tiers"]:
            tier_id = insert(self.db,"prize_tier_result",id=uuid4(),revision_id=revision,rule_version_id=binding.rule_id,
                lottery_id=binding.lottery_id,tier_definition_id=dict(binding.tiers)[tier["key"]],scope_id=binding.scope_id,
                variant_key=tier["variant"],winners_status=tier["winners_status"],winners=tier["winners"])
            if tier["prize"]:
                self._money(binding,revision,tier["prize"],source_texts.get((tier["key"],tier["prize"]["kind"])),tier_id)
        for money in content["money"]:
            self._money(binding,revision,money,source_texts.get((None,money["kind"])))
        self.observe("after_content")
        return revision

    def _money(self, binding, revision, money, source_text, tier_id=None):
        insert(self.db,"monetary_fact",id=uuid4(),revision_id=revision,lottery_id=binding.lottery_id,rule_version_id=binding.rule_id,
            tier_result_id=tier_id,scope_id=binding.scope_id,kind=money["kind"],payout_form=money["payout_form"],
            status=money["status"],amount=money["amount"],currency=money["currency"],source_text=source_text)

    def read_content(self, revision_id, *, allowed_version=VERSION):
        return read_contents(self.db,[revision_id],allowed_versions=(allowed_version,))[revision_id]
