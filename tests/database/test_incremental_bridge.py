"""SPEC-0028: integração real, com mutações negativas explicitamente simuladas."""
from concurrent.futures import ThreadPoolExecutor
import json
import re
from threading import Barrier, Event
import time
from unittest.mock import patch

import psycopg

from app.application.historical_content import VERSION as HISTORICAL, digest
from app.application.historical_pilot import ImportHistoricalPilot, prepare_xlsx
from app.application.mega_sena_content import VERSION, CODE_VERSION as LEGACY_CODE, POLICY_VERSION as LEGACY_POLICY
from app.application.mega_sena_incremental import CODE_VERSION, POLICY_VERSION
from app.application.persistence import Advance, PersistenceError, transact
from persistence_support import BODY, IsolatedPersistenceCase, changed_body
from support import ROOT, Graph


class PostgreSQLIncrementalBridgeTests(IsolatedPersistenceCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.plan = prepare_xlsx(ROOT/"data/raw/mega_sena/mega_sena_resultados.xlsx",(2954,))

    def historical(self, key="historical", units=None):
        return ImportHistoricalPilot(units or self.factory,self.storage).execute(self.plan,key)

    def head(self):
        return self.query("""SELECT r.id,r.content_hash,r.canonicalization_version FROM lb.draw d
            JOIN lb.draw_revision r ON r.id=d.latest_candidate_revision_id""")[0]

    def advancing(self, receipt):
        cp = self.checkpoint()
        lease = self.claim(cp)
        return Advance(cp,lease.cursor,lease.token)

    def test_01_json_enriches_history_and_cursor_atomically(self):
        self.historical()
        old = self.head()
        receipt = self.capture(); advance = self.advancing(receipt)
        result = self.process(receipt,"enrich-forward",advance=advance)
        self.assertEqual(("correction_candidate",2954),(result.outcome,result.advanced_to))
        self.assertEqual((2,2,1),(self.count("draw_revision"),self.count("candidate_observation"),self.count("sync_step")))
        self.assertEqual(self.plan.rows[0].content,transact(self.factory,lambda u:u.draws.read_content(old[0],allowed_version=HISTORICAL)))
        self.assertEqual(VERSION,self.head()[2])
        self.assertEqual("62755ae7c8057839aa4fcb97c2840afbc6e0a296844f7b02fb6d66f81bbe6477",self.head()[1])
        self.assertEqual(result,self.process(receipt,"enrich-forward",advance=advance))
        self.assertEqual([(None,)],self.query("SELECT published_revision_id FROM lb.draw"))
        self.assertEqual([("referenced",)],self.query("SELECT materialization_status FROM lb.ingestion_baseline"))

    def test_02_conflicting_history_commits_quarantine_without_step_then_correct_receipt_advances(self):
        self.historical(); before = self.head()
        payload = json.loads(BODY); payload["valorArrecadado"] += 1  # NEGATIVO, não dado real.
        receipt = self.capture(json.dumps(payload).encode()); advance = self.advancing(receipt)
        result = self.process(receipt,"conflicting-forward",advance=advance)
        self.assertEqual(("quarantined",None,None),(result.outcome,result.revision_id,result.advanced_to))
        self.assertEqual(before,self.head())
        self.assertEqual(0,self.count("sync_step"))
        self.assertEqual([(2953,)],self.query("SELECT cursor_sequence FROM lb.sync_checkpoint"))
        diagnostic = self.query("SELECT diagnostic_payload FROM lb.candidate_observation WHERE decision='quarantined'")[0][0]
        self.assertEqual("quarantined",diagnostic["reconciliation"])
        self.assertTrue(diagnostic["comparison"]["different"])
        self.assertEqual(result,self.process(receipt,"conflicting-forward",advance=advance))
        self.assertEqual(1,self.count("validation_issue"))
        accepted = self.process(self.capture(),"corrected-new-receipt",advance=advance)
        self.assertEqual(2954,accepted.advanced_to)
        self.assertEqual(1,self.count("sync_step"))

    def test_03_json_corrections_a_b_a_and_replay_keep_history_and_latest_head(self):
        self.historical()
        receipt_a = self.capture(); first = self.process(receipt_a,"json-a")
        self.process(self.capture(changed_body()),"json-b")
        last = self.process(self.capture(),"json-a-again")
        self.assertEqual(4,self.count("draw_revision"))
        self.assertNotEqual(first.revision_id,last.revision_id)
        self.assertEqual(first,self.process(receipt_a,"json-a"))
        self.assertEqual("replayed",self.process(receipt_a,"old-receipt-new-key").outcome)
        self.historical("late-partial-support")
        self.assertEqual(last.revision_id,self.head()[0])
        self.assertEqual(4,self.count("draw_revision"))

    def test_04_all_t3_faults_rollback_enrichment_step_and_cursor(self):
        self.historical(); before = self.head()
        receipt = self.capture(); advance = self.advancing(receipt)
        for stage in ("after_revision","after_content","after_observation","after_step","after_cursor","after_processing","before_commit"):
            armed = False
            def fail(actual,db):
                nonlocal armed
                if actual == "before_recipe_claim": armed = True
                if armed and actual == stage: raise RuntimeError("negative-test-t3-interruption")
            with self.subTest(stage=stage),self.assertRaises(RuntimeError):
                self.process(receipt,"fail-"+stage,units=self.units(fail),advance=advance)
            self.assertEqual(before,self.head())
            self.assertEqual((1,1,0),(self.count("draw_revision"),self.count("candidate_observation"),self.count("sync_step")))
            self.assertEqual([(2953,)],self.query("SELECT cursor_sequence FROM lb.sync_checkpoint"))
        self.assertEqual(2954,self.process(receipt,"successful-resume",advance=advance).advanced_to)

    def test_05_lease_lost_at_commit_keeps_historical_head_and_receipt(self):
        self.historical(); before = self.head()
        receipt = self.capture(); advance = self.advancing(receipt)
        def expire(stage,db):
            if stage == "after_cursor":
                db.execute("UPDATE lb.sync_checkpoint SET lease_until=clock_timestamp()-interval '1 second',row_version=row_version+1 WHERE id=%s",(advance.checkpoint_id,))
        with self.assertRaises(PersistenceError):
            self.process(receipt,"expired-commit",units=self.units(expire),advance=advance)
        self.assertEqual(before,self.head())
        self.assertEqual(0,self.count("sync_step"))
        self.assertEqual(2,self.count("capture_receipt"))
        self.assertEqual(2954,self.process(receipt,"valid-resume",advance=advance).advanced_to)

    def test_06_stale_token_rejected_before_enrichment(self):
        self.historical(); before = self.head()
        receipt = self.capture(); advance = self.advancing(receipt)
        with psycopg.connect(**self.owner_args) as db:
            db.execute("UPDATE lb.sync_checkpoint SET lease_token=lease_token+1,lease_until=clock_timestamp()+interval '5 minutes',row_version=row_version+1 WHERE id=%s",(advance.checkpoint_id,))
        with self.assertRaisesRegex(PersistenceError,"lease_lost"):
            self.process(receipt,"stale-worker",advance=advance)
        self.assertEqual(before,self.head())
        self.assertEqual(0,self.count("sync_step"))
        fresh = Advance(advance.checkpoint_id,advance.expected_cursor,advance.lease_token+1)
        self.assertEqual(2954,self.process(receipt,"fresh-worker",advance=fresh).advanced_to)

    def test_07_concurrent_json_enrichment_is_serialized_under_draw_lock(self):
        self.historical()
        a,b = self.capture(),self.capture()
        held,ready,release = Event(),Event(),Event(); pids = {}
        def first(stage,db):
            if stage == "after_draw_lock":
                pids["first"] = db.info.backend_pid; held.set()
                if not release.wait(15): raise RuntimeError("test-release-timeout")
        def second(stage,db):
            if stage == "before_draw_lock": pids["second"] = db.info.backend_pid; ready.set()
        with ThreadPoolExecutor(2) as executor:
            one = executor.submit(self.process,a,"first-json",self.units(first))
            self.assertTrue(held.wait(15))
            two = executor.submit(self.process,b,"second-json",self.units(second))
            try:
                self.assertTrue(ready.wait(15))
                deadline = time.monotonic()+8; blocked = False
                while time.monotonic() < deadline:
                    if pids["first"] in self.query("SELECT pg_blocking_pids(%s)",(pids["second"],))[0][0]:
                        blocked = True; break
                    Event().wait(0.01)
                self.assertTrue(blocked)
            finally: release.set()
            results = [one.result(30),two.result(30)]
        self.assertEqual({"correction_candidate","unchanged"},{r.outcome for r in results})
        self.assertEqual((2,3),(self.count("draw_revision"),self.count("candidate_observation")))

    def test_08_pilot_and_incremental_race_with_advance_converge(self):
        receipt = self.capture(); advance = self.advancing(receipt)
        barrier = Barrier(2)
        def coordinate(stage,db):
            if stage == "before_identity_claim": barrier.wait(15)
        with ThreadPoolExecutor(2) as executor:
            historical = executor.submit(self.historical,"racing-history",self.units(coordinate))
            current = executor.submit(self.process,receipt,"racing-incremental",self.units(coordinate),advance)
            self.assertEqual("completed",historical.result(35)["status"])
            self.assertEqual(2954,current.result(35).advanced_to)
        self.assertEqual((1,1,1),(self.count("draw"),self.count("draw_identity"),self.count("sync_step")))
        self.assertEqual(VERSION,self.head()[2])

    def test_09_upgrade_replays_legacy_commands_and_receipts_without_reinterpretation(self):
        receipt = self.capture(); advance = self.advancing(receipt)
        # Simula fingerprints/receita anteriores, não executa binário antigo nem
        # inventa dados históricos. Fixture real e SQL/commit são reais.
        with patch("app.application.persist_mega_sena.CODE_VERSION",LEGACY_CODE),patch("app.application.persist_mega_sena.POLICY_VERSION",LEGACY_POLICY),\
             patch("app.infrastructure.postgres.processing.CODE_VERSION",LEGACY_CODE),patch("app.infrastructure.postgres.processing.POLICY_VERSION",LEGACY_POLICY):
            old = self.process(receipt,"legacy-command",advance=advance)
        finished = self.query("SELECT finished_at FROM lb.processing_run")[0][0]
        newest = self.process(self.capture(changed_body()),"new-policy-correction")
        self.assertEqual(old,self.process(receipt,"legacy-command",advance=advance))
        replay = self.process(receipt,"legacy-receipt-new-key")
        self.assertEqual(("replayed",old.revision_id),(replay.outcome,replay.revision_id))
        self.assertEqual(newest.revision_id,self.head()[0])
        self.assertEqual(finished,self.query("SELECT finished_at FROM lb.processing_run WHERE code_version=%s",(LEGACY_CODE,))[0][0])
        self.assertEqual(2,self.count("processing_run"))
        with self.assertRaisesRegex(PersistenceError,"idempotency_conflict"):
            self.process(self.capture(),"legacy-command",advance=advance)
        self.assertEqual(1,self.count("sync_step"))

    def test_10_same_content_keeps_distinct_source_evidence_without_changing_money(self):
        first = self.process(self.capture(),"original-text")
        money_before = self.query("SELECT id,source_text FROM lb.monetary_fact ORDER BY id")
        alternate = re.sub(rb'("valorArrecadado"\s*:\s*)([0-9]+)(?:\.0+)?',lambda m:m[1]+m[2]+b'.00',BODY)
        self.assertNotEqual(BODY,alternate)
        second = self.process(self.capture(alternate),"alternate-decimal-text")
        self.assertEqual(first.revision_id,second.revision_id)
        diagnostics = self.query("SELECT diagnostic_payload FROM lb.candidate_observation ORDER BY completed_at")
        self.assertNotEqual(diagnostics[0][0]["evidence_hash"],diagnostics[1][0]["evidence_hash"])
        self.assertEqual(money_before,self.query("SELECT id,source_text FROM lb.monetary_fact ORDER BY id"))

    def test_11_unknown_head_version_is_not_silently_recanonicalized(self):
        # Grafo legado de teste já existente, com versão não suportada pelo writer.
        with psycopg.connect(**self.owner_args) as db:
            g = Graph(db,self.catalog,index=2); g.support(); g.alias(); g.seal()
            db.execute("UPDATE lb.draw SET latest_candidate_revision_id=%s WHERE id=%s",(g.revision,g.draw))
        before = self.head(); receipt = self.capture()
        with self.assertRaisesRegex(PersistenceError,"canonicalization_conflict"):
            self.process(receipt,"unknown-version")
        self.assertEqual(before,self.head())
        self.assertEqual(1,self.count("candidate_observation"))

    def test_12_oversized_evidence_preserves_receipt_and_historical_head(self):
        self.historical(); before = self.head()
        payload = json.loads(BODY); payload["observacao"] = "negative-test:" + "x"*40000
        receipt = self.capture(json.dumps(payload).encode())
        with self.assertRaisesRegex(PersistenceError,"observation_evidence_too_large"):
            self.process(receipt,"oversized-evidence")
        self.assertEqual(before,self.head())
        self.assertEqual(2,self.count("capture_receipt"))
        self.assertEqual(1,self.count("candidate_observation"))
