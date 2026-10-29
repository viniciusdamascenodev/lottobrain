"""Orquestrador real em clones de uma baseline carregada/auditada uma única vez."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
from threading import Event
from uuid import UUID

from app.application.activate_mega_sena_baseline import ActivateMegaSenaBaseline, BaselineRequest
from app.application.collect_mega_sena import CollectionError
from app.application.historical_import import ImportMegaSenaHistory, prepare_history_file
from app.application.persistence import BatchIntent, PersistenceError, transact
from app.application.persist_mega_sena import CaptureMegaSena, ProcessMegaSena
from app.application.sync_postgres import SyncBatchRequest, SyncMegaSenaPostgres
from app.application.sync_mega_sena import SyncPolicy
from baseline_support import BaselineCase
from persistence_support import Source
from support import ROOT
from sync_fixture_support import approved_fixture

BODY2955=(ROOT/"tests/fixtures/mega_sena_api_2955.json").read_bytes()
BODY3071=(ROOT/"tests/fixtures/mega_sena_api_3071.json").read_bytes()


class ScriptedSource:
    def __init__(self,case,responses,probe=lambda:None):
        self.case,self.responses,self.probe=case,list(responses),probe
        self.calls=[]

    def fetch(self,contest):
        self.case.assertTrue(all(c.closed for c in self.case.connections),"HTTP com conexão SQL aberta")
        self.calls.append(contest)
        expected,body,status=self.responses.pop(0)
        self.case.assertEqual(expected,contest)
        self.probe()
        if isinstance(body,Exception): raise body
        return Source(body,status).fetch(contest)


class PostgreSQLSyncBatchTests(BaselineCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cached=approved_fixture()
        if cached:
            cls.template,cls.catalog=cached["template"],cached["catalog"]
            cls.checkpoint_id=cached["checkpoint"]
            cls.raw_body=(ROOT/"data/raw/mega_sena/mega_sena_resultados.xlsx").read_bytes()
            print("SPEC0031_FIXTURE: cloned approved SQL fixture from SPEC0030 scenario",flush=True)
            return
        seed=cls("test_01_discovery_reuse_and_terminal_replay")
        seed.setUp()
        try:
            plan=prepare_history_file(ROOT/"data/raw/mega_sena/mega_sena_resultados.xlsx")
            def progress(stage,row):
                if stage=="after_row" and int(row.contest)%500==0:
                    print(f"SPEC0031_FIXTURE: {row.contest}/2954 real records committed",flush=True)
            imported=ImportMegaSenaHistory(seed.factory,seed.storage,progress).execute(plan,"sync-history")
            seed.assertTrue(imported["qualified"])
            activation=ActivateMegaSenaBaseline(seed.bootstrap_units(),seed.storage).execute(
                BaselineRequest("sync-approval","sync-history",plan.fingerprint,"TEST_ONLY: SPEC-0031 fixture"))
            cls.checkpoint_id=UUID(activation["checkpoint_id"])
            cls.raw_body=plan.body
            cls.template=seed.database
        finally:
            seed.tearDown()

    def setUp(self):
        super().setUp()
        if hasattr(self,"raw_body"): self.storage.put(self.raw_body)
        self.waits=[]
        self.initial_attempts=self.count("fetch_attempt")
        self.initial_receipts=self.count("capture_receipt")

    def request(self,key="batch",budget=1,window=0):
        return SyncBatchRequest(self.checkpoint_id,key,SyncPolicy(budget,window,2))

    def service(self,source,units=None,observe=lambda stage,op:None):
        def wait(seconds):
            self.assertTrue(all(c.closed for c in self.connections),"espera com conexão SQL aberta")
            self.waits.append(seconds)
        return SyncMegaSenaPostgres(units or self.factory,self.storage,source,wait=wait,observe=observe)

    def cursor(self): return self.query("SELECT cursor_sequence FROM lb.sync_checkpoint")[0][0]

    def test_01_discovery_reuse_and_terminal_replay(self):
        source=ScriptedSource(self,[(None,BODY2955,200)])
        request=self.request()
        service=self.service(source)
        report=service.execute(request)
        self.assertEqual(("caught_up",2955,1),(report["stop_reason"],report["cursor_after"],report["request_slots_used"]))
        self.assertEqual([None],source.calls)
        self.assertEqual([2],self.waits)
        self.assertTrue(report["operations"][1]["reused_discovery"])
        self.assertEqual((1,2,1),(self.count("fetch_attempt")-self.initial_attempts,self.count("sync_batch_operation"),self.count("sync_step")))
        before=self.query("SELECT * FROM lb.sync_checkpoint")
        self.query("UPDATE lb.data_source SET readiness='blocked' WHERE key='caixa_mega_sena_json' RETURNING id")
        self.assertEqual(report,service.execute(request))
        self.assertEqual(before,self.query("SELECT * FROM lb.sync_checkpoint"))
        with self.assertRaisesRegex(PersistenceError,"idempotency_conflict"):
            service.execute(replace(request,policy=SyncPolicy(2,0,2)))
        print("SPEC0031_REPORT="+json.dumps(report,sort_keys=True,separators=(",",":")),flush=True)

    def test_02_backlog_budget_never_jumps_to_3071(self):
        source=ScriptedSource(self,[(None,BODY3071,200),(2955,BODY2955,200),(None,BODY3071,200)])
        service=self.service(source)
        report=service.execute(self.request(budget=2))
        self.assertEqual((2955,116,2),(report["cursor_after"],report["remaining"],report["request_slots_used"]))
        second=service.execute(self.request("next",budget=1))
        self.assertEqual((2955,"budget_exhausted"),(second["cursor_after"],second["stop_reason"]))
        self.assertEqual([None,2955,None],source.calls)
        self.assertEqual([2,2,2],self.waits)
        self.assertEqual([(2955,)],self.query("SELECT sequence_no FROM lb.sync_step"))

    def test_03_review_reuses_current_discovery_and_never_advances(self):
        self.service(ScriptedSource(self,[(None,BODY2955,200)])).execute(self.request("seed-forward"))
        source=ScriptedSource(self,[(None,BODY2955,200)])
        steps=self.count("sync_step")
        report=self.service(source).execute(self.request("review",window=1))
        self.assertEqual(["discovery","review"],[o["phase"] for o in report["operations"]])
        self.assertEqual((2955,2955,steps),(self.cursor(),report["review_next"],self.count("sync_step")))
        self.assertEqual([None],source.calls)

    def test_04_discovery_429_stops_and_blocks_other_batch_without_get(self):
        source=ScriptedSource(self,[(None,b"{}",429)])
        report=self.service(source).execute(self.request())
        self.assertEqual(("stopped","source_cooldown",2954),(report["status"],report["stop_reason"],self.cursor()))
        self.assertIsNotNone(report["cooldown_until"])
        with self.assertRaisesRegex(PersistenceError,"source_cooldown"):
            self.service(source).execute(self.request("new"))
        self.assertEqual([None],source.calls)
        self.assertEqual(0,self.count("sync_step"))

    def test_05_bad_response_and_transport_are_not_retried(self):
        for index,(body,status) in enumerate(((b"{}",404),(b"{}",200),(CollectionError("http.transport_failure"),200))):
            source=ScriptedSource(self,[(None,body,status)])
            request=self.request(f"bad-{index}")
            service=self.service(source)
            report=service.execute(request)
            self.assertEqual(("stopped",2954),(report["status"],self.cursor()))
            self.assertEqual(report,service.execute(request))
            self.assertEqual([None],source.calls)
        self.assertEqual(0,self.count("sync_step"))

    def test_06_response_committed_before_summary_failure_is_reused(self):
        source=ScriptedSource(self,[(None,BODY2955,200)])
        def fault(stage,op):
            if stage=="receipt_committed": raise RuntimeError("TEST_ONLY: lost receipt summary")
        with self.assertRaisesRegex(RuntimeError,"lost receipt summary"):
            self.service(source,observe=fault).execute(self.request())
        self.assertEqual((1,0),(self.count("capture_receipt")-self.initial_receipts,self.count("sync_step")))
        report=self.service(source).execute(self.request())
        self.assertEqual(2955,report["cursor_after"])
        self.assertEqual([None],source.calls)

    def test_07_forward_rollback_preserves_receipt_and_recovery_budget(self):
        source=ScriptedSource(self,[(None,BODY2955,200)])
        def fault(stage,db):
            if stage=="after_step": raise RuntimeError("TEST_ONLY: forward aborted")
        with self.assertRaisesRegex(RuntimeError,"forward aborted"):
            self.service(source,self.units(fault)).execute(self.request())
        self.assertEqual((2954,0),(self.cursor(),self.count("sync_step")))
        self.assertEqual(1,self.query("SELECT count(*) FROM lb.sync_batch_operation WHERE state='done'")[0][0])
        report=self.service(source).execute(self.request())
        self.assertEqual((2955,1),(report["cursor_after"],report["request_slots_used"]))
        self.assertEqual([None],source.calls)

    def test_08_expired_discovery_at_commit_rolls_back_operation_and_data(self):
        source=ScriptedSource(self,[(None,BODY2955,200)])
        def expire(stage,db):
            if stage=="after_batch_operation":
                db.execute("""UPDATE lb.sync_checkpoint SET lease_until=clock_timestamp()-interval '1 second',
                    row_version=row_version+1 WHERE id=%s""",(self.checkpoint_id,))
        with self.assertRaisesRegex(PersistenceError,"lease_lost"):
            self.service(source,self.units(expire)).execute(self.request())
        self.assertEqual((2954,0),(self.cursor(),self.query("SELECT count(*) FROM lb.sync_batch_operation WHERE state='done'")[0][0]))
        report=self.service(source).execute(self.request())
        self.assertEqual(2955,report["cursor_after"])
        self.assertEqual([None],source.calls)

    def test_09_t2_and_t3_ambiguous_commits_recover_without_http(self):
        source=ScriptedSource(self,[(None,BODY2955,200)])
        fired={"armed":False,"done":False}
        original_put=self.storage.put
        def put(body):
            result=original_put(body); fired["armed"]=True; return result
        self.storage.put=put
        def lose(stage,db):
            if stage=="after_commit" and fired["armed"] and not fired["done"]:
                fired["done"]=True
                raise OSError("TEST_ONLY: T2 response lost")
        with self.assertRaisesRegex(PersistenceError,"commit_outcome_unknown"):
            self.service(source,self.units(lose)).execute(self.request())
        report=self.service(source).execute(self.request())
        self.assertEqual((2955,[None]),(report["cursor_after"],source.calls))
        # Nova invocação, mesma fronteira, perda de resposta depois da descoberta T3.
        second=ScriptedSource(self,[(None,BODY2955,200)])
        state={"armed":False,"done":False}
        def lose_t3(stage,db):
            if stage=="after_batch_operation": state["armed"]=True
            if stage=="after_commit" and state["armed"] and not state["done"]:
                state["done"]=True; raise OSError("TEST_ONLY: T3 response lost")
        request=self.request("lost-t3")
        with self.assertRaisesRegex(PersistenceError,"commit_outcome_unknown"):
            self.service(second,self.units(lose_t3)).execute(request)
        self.assertEqual("caught_up",self.service(second).execute(request)["stop_reason"])
        self.assertEqual([None],second.calls)

    def test_10_concurrent_invocations_cannot_share_lease(self):
        entered,release=Event(),Event()
        def block():
            entered.set()
            if not release.wait(20): raise RuntimeError("TEST_ONLY: release timeout")
        source=ScriptedSource(self,[(None,BODY2955,200)],block)
        service=self.service(source)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(service.execute,self.request())
            try:
                self.assertTrue(entered.wait(15))
                with self.assertRaisesRegex(PersistenceError,"lease_busy"): service.execute(self.request())
                with self.assertRaisesRegex(PersistenceError,"sync_batch_in_progress"): service.execute(self.request("other"))
            finally: release.set()
            self.assertEqual(2955,future.result(timeout=20)["cursor_after"])
        self.assertEqual([None],source.calls)

    def test_11_unknown_capture_is_never_reissued(self):
        source=ScriptedSource(self,[(None,BODY2955,200)])
        original=self.storage.put
        self.storage.put=lambda body: (_ for _ in ()).throw(PersistenceError("storage_unavailable"))
        with self.assertRaisesRegex(PersistenceError,"storage_unavailable"):
            self.service(source).execute(self.request())
        self.storage.put=original
        report=self.service(source).execute(self.request())
        self.assertEqual(("capture_unresolved",2954,1),(report["stop_reason"],self.cursor(),report["request_slots_used"]))
        self.assertEqual([None],source.calls)

    def test_12_cooldown_survives_t3_failure(self):
        source=ScriptedSource(self,[(None,b"{}",429)])
        def abort(stage,db):
            if stage=="after_batch_operation": raise RuntimeError("TEST_ONLY: quarantine aborted")
        with self.assertRaisesRegex(RuntimeError,"quarantine aborted"):
            self.service(source,self.units(abort)).execute(self.request())
        with self.assertRaisesRegex(PersistenceError,"source_cooldown"):
            self.service(source).execute(self.request())
        self.assertIsNotNone(self.query("SELECT cooldown_until FROM lb.sync_checkpoint")[0][0])
        self.assertEqual([None],source.calls)

    def test_13_lost_terminal_summary_recovers_without_reprocessing(self):
        source=ScriptedSource(self,[(None,BODY2955,200)])
        def abort(stage,db):
            if stage=="after_batch_finished": raise RuntimeError("TEST_ONLY: summary aborted")
        with self.assertRaisesRegex(RuntimeError,"summary aborted"):
            self.service(source,self.units(abort)).execute(self.request())
        self.assertEqual((2955,1),(self.cursor(),self.count("sync_step")))
        report=self.service(source).execute(self.request())
        self.assertEqual((2955,[None]),(report["cursor_after"],source.calls))
        second=ScriptedSource(self,[(None,BODY2955,200)])
        state={"armed":False,"fired":False}
        def lost(stage,db):
            if stage=="after_batch_finished": state["armed"]=True
            if stage=="after_commit" and state["armed"] and not state["fired"]:
                state["fired"]=True; raise OSError("TEST_ONLY: terminal commit response lost")
        request=self.request("terminal-lost")
        with self.assertRaisesRegex(PersistenceError,"commit_outcome_unknown"):
            self.service(second,self.units(lost)).execute(request)
        self.assertEqual("caught_up",self.service(second).execute(request)["stop_reason"])
        self.assertEqual([None],second.calls)

    def test_14_forward_429_never_advances(self):
        source=ScriptedSource(self,[(None,BODY3071,200),(2955,b"{}",429)])
        report=self.service(source).execute(self.request(budget=2))
        self.assertEqual(("source_cooldown",2954,0),(report["stop_reason"],self.cursor(),self.count("sync_step")))
        self.assertEqual([None,2955],source.calls)

    def test_15_review_429_t3_preserves_rotation_and_cooldown(self):
        self.service(ScriptedSource(self,[(None,BODY2955,200)])).execute(self.request("seed-forward"))
        source=ScriptedSource(self,[(None,BODY3071,200)])
        request=self.request("review-t3",budget=3,window=1)
        def stop_after_discovery(stage,op):
            if stage=="operation_committed": raise RuntimeError("TEST_ONLY: inspect review boundary")
        with self.assertRaisesRegex(RuntimeError,"inspect review boundary"):
            self.service(source,observe=stop_after_discovery).execute(request)
        # Exercita diretamente a fronteira T3 de revisão: não inventa um JSON
        # 2956 bem-sucedido só para alcançar a revisão pelo planejador público.
        opened=transact(self.factory,lambda u:u.batches.open(request))
        batch,token=opened["id"],opened["lease_token"]
        op=transact(self.factory,lambda u:u.batches.reserve(batch,token,
            {"phase":"review","contest":2955,"reuse_id":None,"review_after":2955}))
        receipt=CaptureMegaSena(self.factory,self.storage,Source(b"{}",429)).execute(2955,op["capture_key"])
        transact(self.factory,lambda u:u.batches.attach(batch,token,op["id"],receipt))
        op=transact(self.factory,lambda u:u.batches.prepare_operation(batch,token,op["id"]))
        ProcessMegaSena(self.factory,self.storage).execute(receipt,op["processing_key"],
            batch=BatchIntent(self.checkpoint_id,2955,token,op["id"]))
        report=transact(self.factory,lambda u:u.batches.finish(batch,token,"quarantined"))
        self.assertEqual((2955,2955,"source_cooldown"),(report["cursor_after"],report["review_next"],report["stop_reason"]))
        self.assertIsNotNone(report["cooldown_until"])

    def test_16_source_behind_and_blocked_never_regress_or_fetch(self):
        self.service(ScriptedSource(self,[(None,BODY2955,200)])).execute(self.request("seed-forward"))
        body=(ROOT/"tests/fixtures/mega_sena_api_2954.json").read_bytes()
        source=ScriptedSource(self,[(None,body,200)])
        report=self.service(source).execute(self.request("behind"))
        self.assertEqual(("source_behind_cursor",2955),(report["stop_reason"],self.cursor()))
        self.query("UPDATE lb.data_source SET readiness='blocked' WHERE key='caixa_mega_sena_json' RETURNING id")
        with self.assertRaisesRegex(PersistenceError,"catalog_not_qualified"):
            self.service(source).execute(self.request("blocked"))
        self.assertEqual([None],source.calls)
