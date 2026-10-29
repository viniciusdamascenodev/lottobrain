"""SPEC-0027: poucas linhas reais, PostgreSQL descartável e login restrito."""
from concurrent.futures import ThreadPoolExecutor
import json
from threading import Barrier

from app.application.historical_content import VERSION as HISTORICAL, digest
from app.application.historical_pilot import ImportHistoricalPilot, prepare_xlsx, prepare_json
from app.application.mega_sena_content import VERSION as JSON_V1
from app.application.persistence import PersistenceError, transact
from persistence_support import BODY, IsolatedPersistenceCase
from support import ROOT


class PostgreSQLHistoricalPilotTests(IsolatedPersistenceCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.all_rows = prepare_xlsx(ROOT / "data/raw/mega_sena/mega_sena_resultados.xlsx")
        cls.last_row = prepare_xlsx(ROOT / "data/raw/mega_sena/mega_sena_resultados.xlsx",(2954,))
        cls.json_plan = prepare_json(BODY,origin="test-fixture:mega_sena_api_2954.json-not-original-wire")

    def run_plan(self, plan=None, key="pilot", units=None, observe=lambda stage,row:None):
        return ImportHistoricalPilot(units or self.factory,self.storage,observe).execute(plan or self.all_rows,key)

    def head(self):
        return self.query("""SELECT r.id,r.canonicalization_version,r.content_hash,r.revision_no
            FROM lb.draw d JOIN lb.draw_revision r ON r.id=d.latest_candidate_revision_id""")[0]

    def test_01_real_xlsx_roundtrip_manifest_evidence_and_no_http(self):
        original_put, original_read = self.storage.put,self.storage.read
        def put(body):
            self.assertTrue(all(c.closed for c in self.connections))
            return original_put(body)
        def read(*args):
            self.assertTrue(all(c.closed for c in self.connections))
            return original_read(*args)
        self.storage.put,self.storage.read = put,read
        result = self.run_plan()
        self.assertEqual(("completed",3), (result["status"],result["selected_records"]))
        self.assertEqual((3,3,3,0),(self.count("draw"),self.count("draw_revision"),self.count("candidate_observation"),self.count("fetch_attempt")))
        self.assertEqual([("legacy_import",None,None)],self.query("SELECT capture_kind,http_status,fetch_attempt_id FROM lb.capture_receipt"))
        manifest = json.loads(self.query("SELECT legacy_reference FROM lb.capture_receipt")[0][0])["manifest"]
        self.assertEqual(self.all_rows.manifest,manifest)
        for row in self.all_rows.rows:
            stored = self.query("SELECT revision_id,diagnostic_payload FROM lb.candidate_observation WHERE row_locator=%s",(row.locator,))[0]
            actual = transact(self.factory,lambda u:u.draws.read_content(stored[0],allowed_version=HISTORICAL))
            self.assertEqual(row.content,actual)
            self.assertEqual(digest(row.evidence),stored[1]["evidence_hash"])
            self.assertEqual(row.evidence,stored[1]["source_evidence"])
        self.assertEqual([(None,)]*3,self.query("SELECT published_revision_id FROM lb.draw"))
        self.assertEqual(0,self.count("sync_checkpoint"))
        self.assertEqual(0,self.count("ingestion_baseline"))
        self.assertEqual(1,self.count("raw_artifact"))

    def test_02_json_then_xlsx_supports_without_rewriting_sealed_content(self):
        previous = self.process(self.capture(),"existing-json")
        before = self.query("SELECT id,amount,source_text FROM lb.monetary_fact ORDER BY id")
        result = self.run_plan(self.last_row)
        self.assertEqual(["unchanged"],result["outcomes"])
        self.assertEqual(1,self.count("draw_revision"))
        self.assertEqual(previous.revision_id,self.head()[0])
        self.assertEqual(before,self.query("SELECT id,amount,source_text FROM lb.monetary_fact ORDER BY id"))
        row = self.query("""SELECT p.canonicalization_version,o.semantic_hash,o.diagnostic_payload
            FROM lb.candidate_observation o JOIN lb.processing_run p ON p.id=o.processing_run_id WHERE o.row_locator='data_record:2954'""")[0]
        self.assertEqual(JSON_V1,row[0])
        self.assertNotEqual(row[1],row[2]["input_hash"])
        self.assertEqual(HISTORICAL,row[2]["input_contract"])
        self.assertEqual("support",row[2]["reconciliation"])

    def test_03_xlsx_then_json_enriches_and_old_replay_never_regresses(self):
        self.run_plan(self.last_row,"xlsx-first")
        historical = self.head()
        self.run_plan(self.json_plan,"json-second")
        richer = self.head()
        self.assertEqual((JSON_V1,2),(richer[1],richer[3]))
        self.assertEqual("62755ae7c8057839aa4fcb97c2840afbc6e0a296844f7b02fb6d66f81bbe6477",richer[2])
        self.assertEqual(self.last_row.rows[0].content,transact(self.factory,
            lambda u:u.draws.read_content(historical[0],allowed_version=HISTORICAL)))
        self.run_plan(self.last_row,"xlsx-first")
        self.run_plan(self.last_row,"xlsx-another-intention")
        self.assertEqual(richer,self.head())
        self.assertEqual(2,self.count("draw_revision"))
        self.assertEqual(3,self.count("candidate_observation"))
        actual = transact(self.factory,lambda u:u.draws.read_content(richer[0]))
        self.assertEqual(self.json_plan.rows[0].content,actual)
        self.assertEqual([2,6,1,5,3,4],[v["extraction_ordinal"] for v in actual["series"][0]["components"][0]["values"]])

    def test_04_interruption_between_rows_is_resumable_and_key_is_bound_to_plan(self):
        def stop(stage,row):
            if stage == "after_row" and row.contest == "1":
                raise RuntimeError("negative-test-interrupted-between-rows")
        with self.assertRaises(RuntimeError):
            self.run_plan(observe=stop)
        self.assertEqual(1,self.count("candidate_observation"))
        self.assertEqual([("running",None)],self.query("SELECT status,finished_at FROM lb.ingestion_run"))
        self.assertEqual("completed",ImportHistoricalPilot(self.factory,self.storage).resume(
            self.all_rows.source_key,"pilot")["status"])
        self.assertEqual(3,self.count("processing_attempt"))
        before = self.query("SELECT status,finished_at FROM lb.ingestion_run")
        self.run_plan()
        self.assertEqual(before,self.query("SELECT status,finished_at FROM lb.ingestion_run"))
        with self.assertRaisesRegex(PersistenceError,"idempotency_conflict"):
            self.run_plan(self.last_row)
        self.assertEqual(3,self.count("candidate_observation"))

    def test_05_t3_faults_rollback_all_row_effects_but_keep_registered_evidence(self):
        for stage in ("after_revision","after_content","after_observation","after_pilot_row","before_commit"):
            with self.subTest(stage=stage):
                def fail(actual,db):
                    ready = actual != "before_commit" or db.execute("SELECT 1 FROM lb.processing_attempt LIMIT 1").fetchone()
                    if actual == stage and ready:
                        raise RuntimeError("negative-test-rollback-row")
                with self.assertRaises(RuntimeError):
                    self.run_plan(self.last_row,"fail-"+stage,units=self.units(fail))
                self.assertEqual(0,self.count("draw"))
                self.assertEqual(0,self.count("draw_revision"))
                self.assertEqual(0,self.count("candidate_observation"))
                self.assertEqual(0,self.count("processing_attempt"))
        self.assertEqual(1,self.count("raw_artifact"))
        self.assertEqual(5,self.count("capture_receipt"))
        self.assertEqual("completed",self.run_plan(self.last_row,"fail-before_commit")["status"])

    def test_06_lost_row_commit_response_recovers_same_intention(self):
        injected = False
        def lose(stage,db):
            nonlocal injected
            if stage == "after_commit" and not injected and db.execute("SELECT 1 FROM lb.processing_attempt LIMIT 1").fetchone():
                injected = True
                raise OSError("negative-test-response-lost-after-real-commit")
        with self.assertRaisesRegex(PersistenceError,"commit_outcome_unknown"):
            self.run_plan(self.last_row,units=self.units(lose))
        self.assertEqual(1,self.count("candidate_observation"))
        self.assertEqual("completed",self.run_plan(self.last_row)["status"])
        self.assertEqual(1,self.count("draw_revision"))
        self.assertEqual(1,self.count("processing_attempt"))

    def test_07_conflicting_finance_is_quarantined_without_overwriting(self):
        self.run_plan(self.last_row,"historical")
        previous = self.head()
        payload = json.loads(BODY)
        payload["valorArrecadado"] += 1  # Mutação NEGATIVA de teste, não novo resultado real.
        changed = prepare_json(json.dumps(payload).encode(),origin="negative-test:simulated-financial-conflict")
        result = self.run_plan(changed,"negative-json")
        self.assertEqual(("stopped",["quarantined"]),(result["status"],result["outcomes"]))
        self.assertEqual(previous,self.head())
        self.assertEqual(1,self.count("validation_issue"))
        diagnostic = self.query("SELECT diagnostic_payload FROM lb.candidate_observation WHERE decision='quarantined'")[0][0]
        self.assertEqual(digest(changed.rows[0].content),diagnostic["input_hash"])
        self.assertTrue(diagnostic["comparison"]["different"])
        self.assertEqual(2,self.count("raw_artifact"))

    def test_08_changed_source_catalog_stops_before_next_row(self):
        import psycopg
        changed = False
        def change(stage,row):
            nonlocal changed
            if stage == "after_row" and not changed:
                changed = True
                with psycopg.connect(**self.owner_args) as db:
                    db.execute("UPDATE lb.data_source SET readiness='disabled' WHERE key='caixa_mega_sena_xlsx'")
        with self.assertRaisesRegex(PersistenceError,"catalog_not_qualified"):
            self.run_plan(observe=change)
        self.assertEqual(1,self.count("candidate_observation"))
        with psycopg.connect(**self.owner_args) as db:
            db.execute("UPDATE lb.data_source SET readiness='contract_observed' WHERE key='caixa_mega_sena_xlsx'")
        self.assertEqual("completed",self.run_plan()["status"])

    def test_09_concurrent_sources_claim_one_identity_and_json_wins_completeness(self):
        barrier = Barrier(2)
        def coordinate(stage,db):
            if stage == "before_identity_claim":
                barrier.wait(15)
        with ThreadPoolExecutor(2) as executor:
            a = executor.submit(self.run_plan,self.last_row,"race-xlsx",self.units(coordinate))
            b = executor.submit(self.run_plan,self.json_plan,"race-json",self.units(coordinate))
            self.assertEqual("completed",a.result(30)["status"])
            self.assertEqual("completed",b.result(30)["status"])
        self.assertEqual(1,self.count("draw"))
        self.assertEqual(1,self.count("draw_identity"))
        self.assertEqual(2,self.count("external_draw_reference"))
        self.assertEqual(2,self.count("candidate_observation"))
        self.assertEqual(JSON_V1,self.head()[1])

    def test_10_same_plan_concurrent_resume_has_single_ledger_effect(self):
        with ThreadPoolExecutor(2) as executor:
            a = executor.submit(self.run_plan,self.last_row,"same-pilot")
            b = executor.submit(self.run_plan,self.last_row,"same-pilot")
            self.assertEqual(a.result(30),b.result(30))
        self.assertEqual(1,self.count("capture_receipt"))
        self.assertEqual(1,self.count("candidate_observation"))
        self.assertEqual(1,self.count("processing_attempt"))

    def test_11_lost_registration_response_can_resume_from_persisted_manifest(self):
        injected = False
        def lose(stage,db):
            nonlocal injected
            if stage == "after_commit" and not injected and db.execute("SELECT 1 FROM lb.capture_receipt LIMIT 1").fetchone():
                injected = True
                raise OSError("negative-test-registration-committed-response-lost")
        with self.assertRaisesRegex(PersistenceError,"commit_outcome_unknown"):
            self.run_plan(self.last_row,units=self.units(lose))
        self.assertEqual(0,self.count("candidate_observation"))
        result = ImportHistoricalPilot(self.factory,self.storage).resume(self.last_row.source_key,"pilot")
        self.assertEqual("completed",result["status"])
        self.assertEqual(1,self.count("capture_receipt"))

    def test_12_resume_refuses_corrupt_object_without_mutating_sql(self):
        self.run_plan(self.last_row)
        object_key = self.query("SELECT object_key FROM lb.raw_artifact")[0][0]
        (self.storage.root/object_key).write_bytes(b"negative-test-corruption-in-temporary-store-only")
        with self.assertRaisesRegex(PersistenceError,"artifact_hash_mismatch"):
            ImportHistoricalPilot(self.factory,self.storage).resume(self.last_row.source_key,"pilot")
        self.assertEqual(1,self.count("candidate_observation"))
        self.assertEqual(1,self.count("processing_attempt"))

    def test_13_existing_json_collector_enriches_history_after_spec_0028_integration(self):
        self.run_plan(self.last_row)
        previous = self.head()
        result = self.process(self.capture(),"integrated-writer")
        self.assertEqual("correction_candidate",result.outcome)
        self.assertNotEqual(previous[0],self.head()[0])
        self.assertEqual(JSON_V1,self.head()[1])
        self.assertEqual(2,self.count("candidate_observation"))
