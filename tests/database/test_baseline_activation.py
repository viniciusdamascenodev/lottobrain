"""SPEC-0030: histórico completo real, aprovação e passagem JSON sem rede externa."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import hashlib
import json
import os
from threading import Barrier, Lock, local
from uuid import UUID, uuid4

import psycopg
from sqlalchemy.engine import make_url

from app.application.activate_mega_sena_baseline import ActivateMegaSenaBaseline, BaselineRequest
from app.application.historical_import import ImportMegaSenaHistory, prepare_history_file
from app.application.persist_mega_sena import CaptureMegaSena, ProcessMegaSena
from app.application.persistence import Advance, PersistenceError, transact
from baseline_support import BaselineCase
from persistence_support import Source
from support import ROOT, insert, NOW
from test_integrity import migrate


class BaselineActivationTests(BaselineCase):
    def test_01_full_history_activation_and_real_json_continuity(self):
        plan = prepare_history_file(ROOT/"data/raw/mega_sena/mega_sena_resultados.xlsx")
        def progress(stage,row):
            if stage == "after_row" and int(row.contest)%500 == 0:
                print(f"SPEC0030_PROGRESS: {row.contest}/2954 committed",flush=True)
        imported = ImportMegaSenaHistory(self.factory,self.storage,progress).execute(plan,"history")
        self.assertTrue(imported["qualified"],imported)
        cat = self.catalog["mega_sena"]
        bodies = {}
        for contest,sha in ((2955,"06529163206f05fcaecdc6dc589eee5026ab2183f4c072bd072d7079e43b0c6d"),
                            (3071,"7a4d0c4e3decee29a652b5d9a417c97b10c88daebd975b00db056ca0bec701e8")):
            body = (ROOT/f"tests/fixtures/mega_sena_api_{contest}.json").read_bytes()
            self.assertEqual(sha,hashlib.sha256(body).hexdigest())
            self.assertEqual(contest,json.loads(body)["numero"])
            bodies[contest] = body
        # Reutilização de bytes REAIS locais em resposta HTTP dublê; nenhum GET.
        ahead_receipt = CaptureMegaSena(self.factory,self.storage,Source(bodies[3071])).execute(3071,"ahead")
        ProcessMegaSena(self.factory,self.storage).execute(ahead_receipt,"ahead")

        # Referência prévia não aprovada: criar uma nova loaded, jamais promovê-la.
        with psycopg.connect(**self.owner_args) as db:
            artifact = db.execute("SELECT id FROM lb.raw_artifact WHERE sha256=%s",(plan.sha256,)).fetchone()[0]
            referenced = insert(db,"ingestion_baseline",id=uuid4(),lottery_id=cat["lottery"],
                source_id=cat["sources"][plan.source_key],artifact_id=artifact,first_sequence=1,last_sequence=2954,
                manifest_hash=plan.manifest["records_manifest_sha256"],audit_reference="TEST_ONLY: preserved reference",
                audited_at=NOW,materialization_status="referenced")
        reference_before = self.query("SELECT * FROM lb.ingestion_baseline WHERE id=%s",(referenced,))
        self.query("UPDATE lb.data_source SET readiness='blocked' WHERE key=%s RETURNING id",(plan.source_key,))
        request = BaselineRequest("approve-history","history",plan.fingerprint,"TEST_ONLY: SPEC-0030 approval")
        service = ActivateMegaSenaBaseline(self.bootstrap_units(),self.storage)

        def assert_uninitialized():
            self.assertEqual((1,0,0),(self.count("ingestion_baseline"),self.count("baseline_activation"),self.count("sync_checkpoint")))
        for failure in ("after_baseline_insert","after_activation_insert","after_checkpoint_insert","before_commit"):
            active = {"value":False}
            def fault(stage,db):
                if stage == "after_baseline_insert": active["value"] = True
                if active["value"] and stage == failure: raise RuntimeError("TEST_ONLY: activation rollback")
            with self.subTest(failure=failure),self.assertRaisesRegex(RuntimeError,"activation rollback"):
                ActivateMegaSenaBaseline(self.bootstrap_units(fault),self.storage).execute(request)
            assert_uninitialized()
        with self.assertRaises(PersistenceError):
            ActivateMegaSenaBaseline(self.factory,self.storage).execute(request)
        assert_uninitialized()

        # Mutações NEGATIVAS, isoladas e revertidas, nunca aprovações fictícias.
        self.query("UPDATE lb.draw_identity SET active=false WHERE namespace='official_draw_number' AND value='1' RETURNING draw_id")
        with self.assertRaisesRegex(PersistenceError,"baseline_not_eligible"): service.execute(request)
        self.query("UPDATE lb.draw_identity SET active=true WHERE namespace='official_draw_number' AND value='1' RETURNING draw_id")
        self.query("UPDATE lb.ingestion_run SET status='stopped' WHERE mode='historical_import' RETURNING id")
        with self.assertRaisesRegex(PersistenceError,"baseline_not_eligible"): service.execute(request)
        self.query("UPDATE lb.ingestion_run SET status='completed' WHERE mode='historical_import' RETURNING id")
        assert_uninitialized()

        barrier,thread_state,lost_lock = Barrier(2),local(),Lock()
        lost = {"fired":False}
        def concurrent_probe(stage,db):
            if stage == "before_baseline_command_lock" and not getattr(thread_state,"arrived",False):
                thread_state.arrived = True
                barrier.wait(timeout=30)
            if stage == "after_checkpoint_insert": thread_state.created = True
            if stage == "after_commit" and getattr(thread_state,"created",False):
                with lost_lock:
                    if not lost["fired"]:
                        lost["fired"] = True
                        raise OSError("TEST_ONLY: committed activation response lost")
        def activate_concurrently(_):
            try:
                return ActivateMegaSenaBaseline(self.bootstrap_units(concurrent_probe),self.storage).execute(request)
            except PersistenceError as error:
                if error.code != "commit_outcome_unknown": raise
                return {"error":error.code}
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(activate_concurrently,range(2)))
        self.assertEqual(1,sum(o.get("error")=="commit_outcome_unknown" for o in outcomes))
        result = service.execute(request)
        self.assertIn(result,outcomes)
        self.assertEqual((2,1,1),(self.count("ingestion_baseline"),self.count("baseline_activation"),self.count("sync_checkpoint")))
        self.assertEqual(reference_before,self.query("SELECT * FROM lb.ingestion_baseline WHERE id=%s",(referenced,)))
        with self.assertRaisesRegex(PersistenceError,"idempotency_conflict"):
            service.execute(replace(request,approval_reference="TEST_ONLY: another approval"))
        with self.assertRaisesRegex(PersistenceError,"checkpoint_already_initialized"):
            service.execute(replace(request,command="another-command"))

        checkpoint = UUID(result["checkpoint_id"])
        activation = self.query("SELECT coverage_report,coverage_hash,approved_by,approved_at FROM lb.baseline_activation")[0]
        self.assertTrue(activation[0]["qualified"])
        self.assertEqual("lb_test_bootstrap",activation[2])
        self.assertEqual([(cat["sources"][plan.source_key],"loaded",artifact)],self.query(
            "SELECT source_id,materialization_status,artifact_id FROM lb.ingestion_baseline WHERE id=%s",(UUID(result["baseline_id"]),)))
        self.assertEqual([(cat["sources"]["caixa_mega_sena_json"],2954,2955,0,None,None)],self.query(
            "SELECT source_id,cursor_sequence,review_next,lease_token,lease_until,cooldown_until FROM lb.sync_checkpoint"))
        self.assertEqual(0,self.count("sync_step"))
        # Compartilha uma cópia consistente, ainda sem lease/avanço, somente
        # com os testes de orquestração deste mesmo processo/cluster isolado.
        from sync_fixture_support import publish_approved_fixture
        publish_approved_fixture(self,checkpoint)
        with psycopg.connect(**self.owner_args) as db:
            for table in ("ingestion_baseline","baseline_activation"):
                with self.assertRaises(psycopg.errors.CheckViolation),db.transaction():
                    db.execute(f"DELETE FROM lb.{table}")
        url = make_url(os.environ["LOTTOBRAIN_DATABASE_URL"]).set(database=self.database)
        with self.assertRaisesRegex(Exception,"Rollback bloqueado"):
            migrate(url.render_as_string(hide_password=False),"0024_03",down=True)
        self.assertEqual([("0031_01",)],self.query("SELECT version_num FROM alembic_version"))

        lease = transact(self.factory,lambda u:u.sync.claim_lease(checkpoint,u.catalog.qualify(),300))
        intent = Advance(checkpoint,2954,lease.token)
        receipt = CaptureMegaSena(self.factory,self.storage,Source(bodies[2955])).execute(2955,"real-2955")
        def fail_after_step(stage,db):
            if stage == "after_step": raise RuntimeError("TEST_ONLY: forward rollback")
        with self.assertRaisesRegex(RuntimeError,"forward rollback"):
            ProcessMegaSena(self.units(fail_after_step),self.storage).execute(receipt,"advance-2955",advance=intent)
        self.assertEqual([(2954,)],self.query("SELECT cursor_sequence FROM lb.sync_checkpoint"))
        self.assertEqual(0,self.count("sync_step"))
        processed = ProcessMegaSena(self.factory,self.storage).execute(receipt,"advance-2955",advance=intent)
        self.assertEqual(2955,processed.advanced_to)
        self.assertEqual([(2955,processed.observation_id)],self.query("SELECT sequence_no,observation_id FROM lb.sync_step"))
        self.assertEqual(processed,ProcessMegaSena(self.factory,self.storage).execute(receipt,"advance-2955",advance=intent))
        cp_before = self.query("SELECT * FROM lb.sync_checkpoint")
        self.assertEqual(result,service.execute(request))
        self.assertEqual(cp_before,self.query("SELECT * FROM lb.sync_checkpoint"))
        self.assertEqual(activation,self.query("SELECT coverage_report,coverage_hash,approved_by,approved_at FROM lb.baseline_activation")[0])
        with self.assertRaisesRegex(PersistenceError,"checkpoint_conflict"):
            ProcessMegaSena(self.factory,self.storage).execute(ahead_receipt,"no-skip",advance=Advance(checkpoint,2955,lease.token))
        self.query("UPDATE lb.data_source SET readiness='blocked' WHERE key='caixa_mega_sena_json' RETURNING id")
        self.assertEqual(result,service.execute(request))
        with self.assertRaisesRegex(PersistenceError,"catalog_not_qualified"):
            transact(self.factory,lambda u:u.sync.claim_lease(checkpoint,u.catalog.qualify(),300))
        self.assertEqual(0,self.query("SELECT count(*) FROM lb.draw WHERE published_revision_id IS NOT NULL")[0][0])
        report = {"report_version":"mega-sena-baseline-verification-v1","mode":"controlled_no_external_requests",
            "activation":result,"historical_coverage":activation[0],"approval_actor":activation[2],
            "historical_source":plan.source_key,"target_source":"caixa_mega_sena_json","materialization_status":"loaded",
            "initial_cursor":2954,"cursor_after":self.query("SELECT cursor_sequence FROM lb.sync_checkpoint")[0][0],
            "steps":self.count("sync_step"),"draws":self.count("draw"),"baselines":self.count("ingestion_baseline"),
            "activations":self.count("baseline_activation"),"checkpoints":self.count("sync_checkpoint"),
            "existing_reference_preserved":True,"concurrent_initialization_and_ambiguous_commit_recovered":True,
            "rollback_after_each_insert":True,"checkpoint_not_reset_by_replay":True,"cross_source_origin_preserved":True,
            "current_source_block_does_not_reauthorize_past_activation":True,"new_publications":0,
            "local_json_sha256":{str(k):hashlib.sha256(v).hexdigest() for k,v in bodies.items()}}
        print("SPEC0030_REPORT="+json.dumps(report,sort_keys=True,ensure_ascii=True,separators=(",",":")),flush=True)
