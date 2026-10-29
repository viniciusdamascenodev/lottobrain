"""SPEC-0029: uma carga integral real, interrompida e auditada em cluster descartável."""
import json

from app.application.historical_import import ImportMegaSenaHistory, prepare_history_file
from app.application.historical_pilot import ImportHistoricalPilot, prepare_xlsx
from app.application.mega_sena_content import VERSION
from app.application.persistence import PersistenceError, transact
from persistence_support import IsolatedPersistenceCase, changed_body
from support import ROOT


class PostgreSQLFullHistoryTests(IsolatedPersistenceCase):
    def test_01_full_import_interruption_resume_coverage_and_json_overlap(self):
        plan = prepare_history_file(ROOT/"data/raw/mega_sena/mega_sena_resultados.xlsx")
        # JSON real já disponível: a carga não pode substituir sua extração/metadados.
        json_receipt = self.capture(); json_result = self.process(json_receipt,"existing-json")
        initial_json = self.query("SELECT content_hash FROM lb.draw_revision WHERE id=%s",(json_result.revision_id,))[0][0]

        def interrupt(stage,row):
            if stage == "after_row" and row.contest == "100":
                raise RuntimeError("negative-test-interruption-after-100-real-records")
        with self.assertRaises(RuntimeError):
            ImportMegaSenaHistory(self.factory,self.storage,interrupt).execute(plan,"complete-history")
        service = ImportMegaSenaHistory(self.factory,self.storage)
        partial = service.audit("complete-history")
        self.assertFalse(partial["qualified"])
        self.assertEqual((100,2854),(partial["verified_records"],len(partial["missing"])))
        self.assertEqual("running",partial["run_status"])
        self.assertEqual(101,self.count("candidate_observation"))
        print("SPEC0029_PROGRESS: 100/2954 committed; partial audit correctly incomplete",flush=True)

        def progress(stage,row):
            if stage == "after_row" and int(row.contest) % 500 == 0:
                print(f"SPEC0029_PROGRESS: {row.contest}/2954 real records committed",flush=True)
        # Nova instância e plano reconstruído dos objetos/manifesto persistidos.
        resumed = ImportMegaSenaHistory(self.units(),self.storage,progress).resume("complete-history")
        self.assertTrue(resumed["qualified"],resumed)
        self.assertEqual((2954,2954,0),(resumed["expected_records"],resumed["verified_records"],resumed["quarantined_records"]))
        self.assertEqual("completed",resumed["run_status"])
        self.assertEqual({"new":2953,"unchanged":1},resumed["outcome_counts"])
        self.assertEqual((2954,2954,2955),(self.count("draw"),self.count("draw_revision"),self.count("candidate_observation")))
        self.assertEqual((0,0,0),(self.count("ingestion_baseline"),self.count("sync_checkpoint"),self.count("sync_step")))
        self.assertEqual([(json_result.revision_id,)],self.query("SELECT latest_candidate_revision_id FROM lb.draw WHERE id=%s",(json_result.draw_id,)))
        self.assertEqual([(initial_json,VERSION)],self.query("SELECT content_hash,canonicalization_version FROM lb.draw_revision WHERE id=%s",(json_result.revision_id,)))

        before = self.query("SELECT finished_at FROM lb.ingestion_run WHERE mode='historical_import'")
        again = service.resume("complete-history")
        self.assertEqual(resumed,again)
        self.assertEqual(before,self.query("SELECT finished_at FROM lb.ingestion_run WHERE mode='historical_import'"))
        self.assertEqual(2955,self.count("processing_attempt"))
        self.assertEqual(resumed,service.audit("complete-history"))
        # Relatório sem UUIDs/relógios, derivado desta carga SQL real, não esperado fictício.
        print("SPEC0029_REPORT="+json.dumps(resumed,sort_keys=True,ensure_ascii=True,separators=(",",":")),flush=True)

        small = prepare_xlsx(ROOT/"data/raw/mega_sena/mega_sena_resultados.xlsx",(2954,))
        with self.assertRaisesRegex(PersistenceError,"idempotency_conflict"):
            ImportHistoricalPilot(self.factory,self.storage).execute(small,"complete-history")
        # Correção SIMULADA posterior, para provar interoperabilidade após a carga integral.
        newer = self.process(self.capture(changed_body()),"post-import-negative-test-correction")
        self.assertEqual("correction_candidate",newer.outcome)
        self.assertTrue(service.audit("complete-history")["qualified"])
        self.assertEqual(newer.revision_id,self.query("SELECT latest_candidate_revision_id FROM lb.draw WHERE id=%s",(json_result.draw_id,))[0][0])

        # Evolução SIMULADA de configuração: leitura histórica não reautoriza
        # a fonte e não compara receitas antigas com o fingerprint de hoje.
        self.query("""UPDATE lb.data_source SET readiness='approved',policy_reference='TEST_ONLY: evolved policy'
            WHERE key=%s RETURNING id""",(plan.source_key,))
        approved = service.audit("complete-history")
        self.assertTrue(approved["qualified"],approved)
        with self.assertRaisesRegex(PersistenceError,"idempotency_conflict"):
            service.resume("complete-history")
        self.query("UPDATE lb.data_source SET readiness='blocked' WHERE key=%s RETURNING id",(plan.source_key,))
        self.assertEqual(approved,service.audit("complete-history"))
        with self.assertRaisesRegex(PersistenceError,"catalog_not_qualified"):
            service.resume("complete-history")
        self.assertEqual(before,self.query("SELECT finished_at FROM lb.ingestion_run WHERE mode='historical_import'"))

    def test_02_incomplete_finish_stays_stopped_on_repeat(self):
        plan = prepare_history_file(ROOT/"data/raw/mega_sena/mega_sena_resultados.xlsx")
        sha,object_key = self.storage.put(plan.body)
        self.assertEqual(plan.sha256,sha)
        registration = transact(self.factory,lambda u:u.history.register(plan,"incomplete",object_key))
        first = transact(self.factory,lambda u:u.history.finish(registration,plan))
        self.assertFalse(first["qualified"])
        self.assertEqual(("stopped",2954),(first["run_status"],len(first["missing"])))
        before = self.query("SELECT status,finished_at FROM lb.ingestion_run")
        again = transact(self.factory,lambda u:u.history.finish(registration,plan))
        self.assertEqual(first,again)
        self.assertEqual(before,self.query("SELECT status,finished_at FROM lb.ingestion_run"))
        self.assertEqual(first,ImportMegaSenaHistory(self.factory,self.storage).audit("incomplete"))
        self.assertEqual((0,0),(self.count("draw"),self.count("processing_attempt")))
