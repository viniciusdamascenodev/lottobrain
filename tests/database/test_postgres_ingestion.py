"""SPEC-0025: casos de uso reais, login restrito e conexões independentes."""
from concurrent.futures import ThreadPoolExecutor
import json
from threading import Barrier, Event
import time
import unittest

import psycopg

from app.application.collect_mega_sena import CollectionError
from app.application.mega_sena_content import digest
from app.application.persist_mega_sena import CaptureMegaSena, CollectMegaSenaPostgres
from app.application.persistence import Advance, PersistenceError, transact
from support import ROOT
from persistence_support import BODY, Source, changed_body, IsolatedPersistenceCase

class PostgreSQLIngestionTests(IsolatedPersistenceCase):

    def test_01_capture_roundtrip_and_restricted_login(self):
        source = Source()
        result = CollectMegaSenaPostgres(self.factory,self.storage,source).execute(2954,"test-roundtrip")
        vector = json.loads((ROOT/"tests/fixtures/mega_sena_relational_v1.json").read_text(encoding="utf-8"))
        actual = transact(self.factory,lambda u:u.draws.read_content(result.revision_id))
        self.assertEqual(vector["content"],actual)
        self.assertEqual(vector["sha256"],digest(actual))
        self.assertEqual((1,1,1,1),(source.calls,self.count("draw"),self.count("draw_revision"),self.count("candidate_observation")))
        self.assertEqual([(None,)],self.query("SELECT published_revision_id FROM lb.draw"))
        self.assertEqual([("completed",)],self.query("SELECT status FROM lb.ingestion_run"))
        self.assertEqual("lb_test_ingestor",transact(self.factory,lambda u:u.connection.execute("SELECT current_user AS u").fetchone()["u"]))

    def test_02_same_command_does_not_get_or_write_again(self):
        source = Source(); collector = CollectMegaSenaPostgres(self.factory,self.storage,source)
        first = collector.execute(2954,"same-command")
        second = collector.execute(2954,"same-command")
        self.assertEqual(first,second)
        self.assertEqual((1,1,1,1),(source.calls,self.count("capture_receipt"),self.count("processing_attempt"),self.count("draw_revision")))

    def test_03_reused_key_different_parameters_is_conflict(self):
        source = Source(); capture = CaptureMegaSena(self.factory,self.storage,source)
        a = capture.execute(2954,"same-key")
        with self.assertRaisesRegex(PersistenceError,"idempotency_conflict"): capture.execute(None,"same-key")
        self.process(a,"process-key")
        b = self.capture()
        with self.assertRaisesRegex(PersistenceError,"idempotency_conflict"): self.process(b,"process-key")
        self.assertEqual(1,self.count("processing_attempt"))

    def test_04_distinct_capture_same_content_keeps_two_observations(self):
        a = self.process(self.capture()); b = self.process(self.capture())
        self.assertEqual(("new","unchanged"),(a.outcome,b.outcome))
        self.assertEqual(a.revision_id,b.revision_id)
        self.assertEqual((1,2,2),(self.count("raw_artifact"),self.count("capture_receipt"),self.count("candidate_observation")))

    def test_05_a_b_a_and_old_replay_never_regresses_head(self):
        receipt_a = self.capture(); a = self.process(receipt_a)
        first_finished = self.query("SELECT finished_at FROM lb.processing_run")[0][0]
        b = self.process(self.capture(changed_body()))
        replay = self.process(receipt_a)
        self.assertEqual([(first_finished,)],self.query("SELECT finished_at FROM lb.processing_run WHERE receipt_id=%s",(receipt_a,)))
        self.assertEqual(("replayed",a.revision_id),(replay.outcome,replay.revision_id))
        self.assertEqual([(b.revision_id,)],self.query("SELECT latest_candidate_revision_id FROM lb.draw"))
        again = self.process(self.capture())
        self.assertEqual((1,2,3),(a.revision_no,b.revision_no,again.revision_no))
        self.assertEqual([("new",),("correction_candidate",),("replayed",),("correction_candidate",)],
                         self.query("SELECT outcome FROM lb.processing_attempt ORDER BY started_at"))
        self.assertEqual(3,self.count("candidate_observation"))

    def test_06_quarantine_keeps_receipt_without_draw(self):
        result = self.process(self.capture(b'{"wrong":"schema"}'))
        self.assertEqual("quarantined",result.outcome)
        self.assertEqual((0,1),(self.count("draw"),self.count("capture_receipt")))
        self.assertGreater(self.count("validation_issue"),0)

    def test_07_bodyless_failure_is_recorded_without_artifact_or_retry(self):
        source = Source(error=CollectionError("http.transport_failure"))
        capture = CaptureMegaSena(self.factory,self.storage,source)
        with self.assertRaises(CollectionError): capture.execute(2954,"transport-failure")
        with self.assertRaisesRegex(PersistenceError,"http.transport_failure"): capture.execute(2954,"transport-failure")
        self.assertEqual((1,0,0),(source.calls,self.count("raw_artifact"),self.count("capture_receipt")))
        self.assertEqual([("failed",)],self.query("SELECT status FROM lb.ingestion_run"))

    def test_08_io_runs_with_no_open_sql_connection(self):
        def probe():
            self.assertTrue(all(c.closed for c in self.connections))
            self.assertEqual(1,self.count("fetch_attempt"))  # T1 visível por outra conexão.
        source = Source(probe=probe)
        original_put,original_read = self.storage.put,self.storage.read
        def put(body): probe(); return original_put(body)
        def read(*args): probe(); return original_read(*args)
        self.storage.put,self.storage.read = put,read
        CollectMegaSenaPostgres(self.factory,self.storage,source).execute(2954,"external-io")

    def test_09_forward_is_atomic_and_same_command_retries_after_commit(self):
        receipt = self.capture(); checkpoint = self.checkpoint(); lease = self.claim(checkpoint)
        advance = Advance(checkpoint,lease.cursor,lease.token)
        result = self.process(receipt,"forward",advance=advance)
        self.assertEqual((2954,1),(result.advanced_to,self.count("sync_step")))
        self.assertEqual([(2954,)],self.query("SELECT cursor_sequence FROM lb.sync_checkpoint"))
        self.assertEqual(result,self.process(receipt,"forward",advance=advance))

    def test_10_failures_rollback_whole_t3_keep_captured_bytes(self):
        receipt = self.capture(); checkpoint = self.checkpoint(); lease = self.claim(checkpoint)
        advance = Advance(checkpoint,lease.cursor,lease.token)
        for stage in ("after_revision","after_content","after_observation","after_step","after_cursor","after_processing","before_commit"):
            armed = [False]
            def observe(actual,db):
                if actual == "before_recipe_claim": armed[0] = True
                if actual == stage and armed[0]: raise RuntimeError("explicit-test-interruption")
            with self.subTest(stage=stage),self.assertRaisesRegex(RuntimeError,"explicit-test-interruption"):
                self.process(receipt,"interrupted-"+stage,units=self.units(observe),advance=advance)
            self.assertEqual((0,0,0,1),(self.count("draw"),self.count("processing_run"),self.count("sync_step"),self.count("capture_receipt")))
            self.assertEqual([(2953,)],self.query("SELECT cursor_sequence FROM lb.sync_checkpoint"))
        self.assertEqual(2954,self.process(receipt,advance=advance).advanced_to)

    def test_11_same_identity_race_rolls_back_losing_draw(self):
        a,b = self.capture(),self.capture()
        barrier = Barrier(2)
        def observe(stage,db):
            if stage == "before_identity_claim": barrier.wait(timeout=8)
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_a = executor.submit(self.process,a,"race-a",self.units(observe))
            future_b = executor.submit(self.process,b,"race-b",self.units(observe))
            results = [future_a.result(timeout=15),future_b.result(timeout=15)]
        self.assertEqual({"new","unchanged"},{r.outcome for r in results})
        self.assertEqual((1,1,2,1),(self.count("draw"),self.count("draw_revision"),self.count("candidate_observation"),self.count("draw_identity")))

    def test_12_commit_response_lost_is_recovered_without_duplicate_effects(self):
        receipt = self.capture(); armed = [False]; triggered = [False]
        def observe(stage,db):
            if stage == "after_processing": armed[0] = True
            if stage == "after_commit" and armed[0] and not triggered[0]:
                triggered[0] = True
                raise OSError("simulated-lost-response")
        with self.assertRaisesRegex(PersistenceError,"commit_outcome_unknown"):
            self.process(receipt,"lost-commit",units=self.units(observe))
        result = self.process(receipt,"lost-commit")
        self.assertEqual(("new",1,1),(result.outcome,self.count("draw_revision"),self.count("processing_attempt")))

    def test_13_concurrent_different_corrections_read_head_after_lock(self):
        initial = self.process(self.capture())
        a,b = self.capture(changed_body(1)),self.capture(changed_body(2))
        held,second_ready,release = Event(),Event(),Event()
        pids = {}
        def first_hook(stage,db):
            if stage == "after_draw_lock":
                pids["first"] = db.info.backend_pid; held.set()
                if not release.wait(8): raise RuntimeError("test-release-timeout")
        def second_hook(stage,db):
            if stage == "before_draw_lock":
                pids["second"] = db.info.backend_pid; second_ready.set()
        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(self.process,a,"correction-a",self.units(first_hook))
            self.assertTrue(held.wait(8))
            second = executor.submit(self.process,b,"correction-b",self.units(second_hook))
            try:
                self.assertTrue(second_ready.wait(8))
                deadline = time.monotonic()+5
                blocked = False
                while time.monotonic() < deadline:
                    if pids["first"] in self.query("SELECT pg_blocking_pids(%s)",(pids["second"],))[0][0]:
                        blocked = True; break
                    # Aguarda estado real do servidor, não presume corrida pelo tempo.
                    Event().wait(0.01)
                self.assertTrue(blocked,"segunda conexão não foi observada bloqueada no draw")
            finally:
                release.set()
            results = [first.result(timeout=15),second.result(timeout=15)]
        self.assertEqual([2,3],[r.revision_no for r in results])
        self.assertEqual(initial.draw_id,results[-1].draw_id)
        self.assertEqual([(results[-1].revision_id,)],self.query("SELECT latest_candidate_revision_id FROM lb.draw"))
        self.assertEqual([(None,)],self.query("SELECT published_revision_id FROM lb.draw"))

    def test_14_two_commands_same_recipe_keep_one_observation(self):
        receipt = self.capture(); barrier = Barrier(2)
        def observe(stage,db):
            if stage == "before_recipe_claim": barrier.wait(8)
        with ThreadPoolExecutor(max_workers=2) as executor:
            a = executor.submit(self.process,receipt,"recipe-a",self.units(observe))
            b = executor.submit(self.process,receipt,"recipe-b",self.units(observe))
            results = [a.result(15),b.result(15)]
        self.assertEqual({"new","replayed"},{r.outcome for r in results})
        self.assertEqual((1,1,1,2),(self.count("processing_run"),self.count("candidate_observation"),self.count("draw_revision"),self.count("processing_attempt")))

    def test_15_stale_worker_loses_lease_but_capture_is_kept(self):
        receipt = self.capture(); cp = self.checkpoint(); old = self.claim(cp)
        with psycopg.connect(**self.owner_args) as db:
            db.execute("UPDATE lb.sync_checkpoint SET lease_until=clock_timestamp()-interval '1 second',row_version=row_version+1 WHERE id=%s",(cp,))
        current = self.claim(cp)
        self.assertGreater(current.token,old.token)
        with self.assertRaisesRegex(PersistenceError,"lease_lost"):
            self.process(receipt,"stale-worker",advance=Advance(cp,old.cursor,old.token))
        self.assertEqual((1,0,0),(self.count("capture_receipt"),self.count("draw_revision"),self.count("sync_step")))
        result = self.process(receipt,"current-worker",advance=Advance(cp,current.cursor,current.token))
        self.assertEqual(2954,result.advanced_to)

    def test_16_lease_busy_and_checkpoint_conflict_do_not_write(self):
        receipt = self.capture(); cp = self.checkpoint(); lease = self.claim(cp)
        with self.assertRaisesRegex(PersistenceError,"lease_busy"): self.claim(cp)
        with self.assertRaisesRegex(PersistenceError,"checkpoint_conflict"):
            self.process(receipt,advance=Advance(cp,2954,lease.token))
        self.assertEqual((0,0),(self.count("draw"),self.count("sync_step")))

    def test_17_ahead_candidate_and_later_replay_forward(self):
        receipt = self.capture(); cp = self.checkpoint()
        candidate = self.process(receipt,"discovery")
        self.assertEqual([(2953,)],self.query("SELECT cursor_sequence FROM lb.sync_checkpoint"))
        lease = self.claim(cp)
        forward = self.process(receipt,"reuse-discovery",advance=Advance(cp,lease.cursor,lease.token))
        self.assertEqual(("replayed",candidate.revision_id,2954),(forward.outcome,forward.revision_id,forward.advanced_to))
        self.assertEqual((1,1),(self.count("draw_revision"),self.count("candidate_observation")))

    def test_18_429_cooldown_survives_t3_failure_and_blocks_new_gets(self):
        # Uma captura válida prepara apenas a evidência de baseline técnica.
        self.capture(); cp = self.checkpoint(); lease = self.claim(cp)
        receipt = self.capture(status=429)
        def fail(stage,db):
            if stage == "before_recipe_claim": raise RuntimeError("simulated-t3-failure")
        with self.assertRaisesRegex(RuntimeError,"simulated-t3-failure"):
            self.process(receipt,"throttled",units=self.units(fail),advance=Advance(cp,lease.cursor,lease.token))
        self.assertEqual([(2953,True)],self.query("SELECT cursor_sequence,cooldown_until > clock_timestamp() FROM lb.sync_checkpoint"))
        source = Source()
        with self.assertRaisesRegex(PersistenceError,"source_cooldown"):
            CaptureMegaSena(self.factory,self.storage,source).execute(2954,"new-during-cooldown")
        self.assertEqual(0,source.calls)
        result = self.process(receipt,"throttled",advance=Advance(cp,lease.cursor,lease.token))
        self.assertEqual(("quarantined",None),(result.outcome,result.advanced_to))
        self.assertEqual(0,self.count("sync_step"))

    def test_19_404_body_is_saved_and_quarantined(self):
        result = self.process(self.capture(body=b'{"test":"404-body"}',status=404))
        self.assertEqual("quarantined",result.outcome)
        self.assertEqual((1,1,0),(self.count("raw_artifact"),self.count("capture_receipt"),self.count("draw")))
        self.assertEqual([("http.status_404",)],self.query("SELECT code FROM lb.validation_issue"))

    def test_20_retry_is_only_sql_and_limited_to_three_attempts(self):
        source = Source(); receipt = CaptureMegaSena(self.factory,self.storage,source).execute(2954,"retry-capture")
        failures = [0]
        def once(stage,db):
            if stage == "after_revision" and failures[0] == 0:
                failures[0] += 1
                raise psycopg.errors.SerializationFailure("explicit-test-retry")
        self.process(receipt,"sql-retry",units=self.units(once))
        self.assertEqual((1,1,1),(source.calls,self.count("draw_revision"),self.count("processing_attempt")))
        tries = [0]
        def always(stage,db):
            if stage == "before_recipe_claim":
                tries[0] += 1
                raise psycopg.errors.DeadlockDetected("explicit-test-exhaustion")
        with self.assertRaisesRegex(PersistenceError,"transaction_conflict"):
            self.process(receipt,"retry-exhaustion",units=self.units(always))
        self.assertEqual((3,1,1),(tries[0],source.calls,self.count("processing_attempt")))

    def test_21_missing_or_corrupted_artifact_is_never_processed(self):
        receipt = self.capture()
        key, = self.query("SELECT object_key FROM lb.raw_artifact")[0]
        target = self.storage.root/key
        with target.open("wb") as output: output.write(b"explicit-test-corruption")
        with self.assertRaisesRegex(PersistenceError,"artifact_hash_mismatch"): self.process(receipt)
        target.unlink()
        with self.assertRaisesRegex(PersistenceError,"evidence_missing"): self.process(receipt)
        self.assertEqual(0,self.count("processing_run"))

    def test_22_unqualified_catalog_fails_before_network(self):
        source = Source()
        with psycopg.connect(**self.owner_args) as db:
            db.execute("UPDATE lb.component_definition SET max_value=59 WHERE id=%s",(self.catalog["mega_sena"]["rules"]["baseline_1996"]["series"]["primary"]["components"]["main"],))
        with self.assertRaisesRegex(PersistenceError,"catalog_not_qualified"):
            CaptureMegaSena(self.factory,self.storage,source).execute(2954,"bad-catalog")
        self.assertEqual((0,0),(source.calls,self.count("ingestion_run")))

    def test_23_lease_lost_at_commit_rolls_back_revision_and_cursor(self):
        receipt = self.capture(); cp = self.checkpoint(); lease = self.claim(cp)
        def expire(stage,db):
            if stage == "after_cursor":
                # Injeção explícita de perda de validade, sem esperar pelo relógio.
                db.execute("UPDATE lb.sync_checkpoint SET lease_until=clock_timestamp()-interval '1 second',row_version=row_version+1 WHERE id=%s",(cp,))
        with self.assertRaisesRegex(PersistenceError,"lease_lost"):
            self.process(receipt,"expired-at-commit",units=self.units(expire),advance=Advance(cp,lease.cursor,lease.token))
        self.assertEqual((0,0,1),(self.count("draw_revision"),self.count("sync_step"),self.count("capture_receipt")))
        self.assertEqual([(2953,)],self.query("SELECT cursor_sequence FROM lb.sync_checkpoint"))

    def test_24_429_without_checkpoint_still_blocks_new_capture_intents(self):
        source = Source(status=429)
        collector = CollectMegaSenaPostgres(self.factory,self.storage,source)
        first = collector.execute(2954,"429-no-baseline")
        self.assertEqual("quarantined",first.outcome)
        self.assertEqual(first,collector.execute(2954,"429-no-baseline"))
        with self.assertRaisesRegex(PersistenceError,"source_cooldown"):
            collector.execute(2954,"another-429-intent")
        self.assertEqual((1,1),(source.calls,self.count("capture_receipt")))

    def test_25_interrupted_after_put_keeps_orphan_without_fabricating_receipt(self):
        source = Source(); original = self.storage.put
        def interrupted(body):
            original(body)
            raise RuntimeError("explicit-interruption-after-put")
        self.storage.put = interrupted
        capture = CaptureMegaSena(self.factory,self.storage,source)
        with self.assertRaisesRegex(RuntimeError,"explicit-interruption-after-put"):
            capture.execute(2954,"interrupted-acquisition")
        self.storage.put = original
        with self.assertRaisesRegex(PersistenceError,"capture_in_progress"):
            capture.execute(2954,"interrupted-acquisition")
        self.assertEqual((1,0,0),(source.calls,self.count("capture_receipt"),self.count("raw_artifact")))
        self.assertEqual(1,len(list(self.storage.root.rglob("*.bin"))))

    def test_26_lost_t2_commit_response_resumes_without_another_get(self):
        source = Source(); armed = [False]; raised = [False]
        def lose(stage,db):
            if stage == "before_commit" and not raised[0]:
                armed[0] = bool(db.execute("SELECT 1 FROM lb.capture_receipt LIMIT 1").fetchone())
            if stage == "after_commit" and armed[0] and not raised[0]:
                raised[0] = True
                raise OSError("explicit-lost-t2-response")
        collector = CollectMegaSenaPostgres(self.units(lose),self.storage,source)
        with self.assertRaisesRegex(PersistenceError,"commit_outcome_unknown"):
            collector.execute(2954,"lost-t2")
        self.assertEqual((1,0),(self.count("capture_receipt"),self.count("draw_revision")))
        result = CollectMegaSenaPostgres(self.factory,self.storage,source).execute(2954,"lost-t2")
        self.assertEqual(("new",1,1),(result.outcome,source.calls,self.count("capture_receipt")))

    def test_27_unknown_money_and_known_zero_roundtrip(self):
        payload = json.loads(BODY)
        payload["valorArrecadado"] = None  # Ausência simulada sobre fixture real.
        result = self.process(self.capture(json.dumps(payload,ensure_ascii=False).encode()))
        content = transact(self.factory,lambda u:u.draws.read_content(result.revision_id))
        sales = next(m for m in content["money"] if m["kind"] == "sales_total")
        self.assertEqual(("unknown",None,None),(sales["status"],sales["amount"],sales["currency"]))
        sena = next(t for t in content["prize_tiers"] if t["key"] == "sena")
        self.assertEqual((0,"0"),(sena["winners"],sena["prize"]["amount"]))


if __name__ == "__main__":
    unittest.main()
