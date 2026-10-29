"""Recusas rápidas antes da prova de carga integral; nenhum relatório falso promove baseline."""
from dataclasses import replace
import os
from uuid import uuid4
import psycopg

from app.application.activate_mega_sena_baseline import ActivateMegaSenaBaseline, BaselineRequest
from app.application.historical_import import prepare_history_file
from app.application.persistence import PersistenceError, transact
from baseline_support import BaselineCase
from support import ROOT, insert, NOW
from sqlalchemy.engine import make_url
from test_integrity import migrate


class BaselineActivationSmokeTests(BaselineCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.plan = prepare_history_file(ROOT/"data/raw/mega_sena/mega_sena_resultados.xlsx")

    def register_only(self):
        _,object_key = self.storage.put(self.plan.body)
        return transact(self.factory,lambda u:u.history.register(self.plan,"history",object_key))

    def request(self):
        return BaselineRequest("activate","history",self.plan.fingerprint,"TEST_ONLY: smoke")

    def assert_empty(self):
        self.assertEqual((0,0,0),(self.count("ingestion_baseline"),self.count("baseline_activation"),self.count("sync_checkpoint")))

    def test_01_migration_and_separate_roles(self):
        self.assertEqual([("0033_01",)],self.query("SELECT version_num FROM alembic_version"))
        with psycopg.connect(**dict(self.owner_args,user="lb_test_ingestor")) as db:
            self.assertEqual((False,False,False),db.execute("""SELECT
                has_table_privilege(current_user,'lb.ingestion_baseline','INSERT'),
                has_table_privilege(current_user,'lb.baseline_activation','INSERT'),
                has_table_privilege(current_user,'lb.sync_checkpoint','INSERT')""").fetchone())
            for table in ("ingestion_baseline","baseline_activation","sync_checkpoint"):
                with self.assertRaises(psycopg.errors.InsufficientPrivilege),db.transaction():
                    db.execute(f"INSERT INTO lb.{table} SELECT * FROM lb.{table} LIMIT 0")
        with psycopg.connect(**dict(self.owner_args,user="lb_test_bootstrap")) as db:
            self.assertEqual((True,False,False,False),db.execute("""SELECT
                has_table_privilege(current_user,'lb.baseline_activation','INSERT'),
                has_table_privilege(current_user,'lb.ingestion_baseline','UPDATE'),
                has_table_privilege(current_user,'lb.data_source','UPDATE'),
                has_table_privilege(current_user,'lb.draw','UPDATE')""").fetchone())

    def test_02_missing_partial_and_stopped_are_not_approval(self):
        service = ActivateMegaSenaBaseline(self.bootstrap_units(),self.storage)
        with self.assertRaisesRegex(PersistenceError,"historical_plan_not_found"): service.execute(self.request())
        self.register_only()
        with self.assertRaisesRegex(PersistenceError,"baseline_not_eligible"): service.execute(self.request())
        self.query("UPDATE lb.ingestion_run SET status='stopped',finished_at=clock_timestamp() WHERE mode='historical_import' RETURNING id")
        with self.assertRaisesRegex(PersistenceError,"baseline_not_eligible"): service.execute(self.request())
        self.assert_empty()

    def test_03_manifest_raw_and_current_target_are_checked(self):
        self.register_only()
        service = ActivateMegaSenaBaseline(self.bootstrap_units(),self.storage)
        with self.assertRaisesRegex(PersistenceError,"historical_manifest_mismatch"):
            service.execute(replace(self.request(),expected_plan_hash="0"*64))
        self.query("UPDATE lb.data_source SET readiness='blocked' WHERE key='caixa_mega_sena_json' RETURNING id")
        with self.assertRaisesRegex(PersistenceError,"catalog_not_qualified"): service.execute(self.request())
        self.storage.read = lambda *args: (_ for _ in ()).throw(PersistenceError("artifact_hash_mismatch"))
        with self.assertRaisesRegex(PersistenceError,"artifact_hash_mismatch"): service.execute(self.request())
        self.storage.read = lambda *args: (_ for _ in ()).throw(PersistenceError("evidence_missing"))
        with self.assertRaisesRegex(PersistenceError,"evidence_missing"): service.execute(self.request())
        self.assert_empty()

    def test_04_cross_source_checkpoint_without_handoff_is_rejected(self):
        registration = self.register_only()
        cat = self.catalog["mega_sena"]
        with psycopg.connect(**self.owner_args) as db:
            artifact = db.execute("SELECT artifact_id FROM lb.capture_receipt WHERE id=%s",(registration["receipt_id"],)).fetchone()[0]
            baseline = insert(db,"ingestion_baseline",id=uuid4(),lottery_id=cat["lottery"],source_id=cat["sources"][self.plan.source_key],
                artifact_id=artifact,first_sequence=1,last_sequence=2954,manifest_hash=self.plan.fingerprint,
                audit_reference="TEST_ONLY: unapproved reference",audited_at=NOW,materialization_status="referenced")
            with self.assertRaises(psycopg.errors.CheckViolation):
                with db.transaction():
                    insert(db,"sync_checkpoint",id=uuid4(),lottery_id=cat["lottery"],source_id=cat["sources"]["caixa_mega_sena_json"],
                        stream_key="unsafe_test",strategy="official_numeric_sequence",baseline_id=baseline,cursor_sequence=2954,review_next=2955)
            with self.assertRaises(psycopg.errors.CheckViolation):
                with db.transaction(): db.execute("UPDATE lb.ingestion_baseline SET materialization_status='loaded' WHERE id=%s",(baseline,))

    def test_05_upgrade_preserves_previous_referenced_baseline_and_checkpoint(self):
        registration = self.register_only()
        url = make_url(os.environ["LOTTOBRAIN_DATABASE_URL"]).set(database=self.database).render_as_string(hide_password=False)
        migrate(url,"0024_03",down=True)
        cat = self.catalog["mega_sena"]
        with psycopg.connect(**self.owner_args) as db:
            artifact = db.execute("SELECT artifact_id FROM lb.capture_receipt WHERE id=%s",(registration["receipt_id"],)).fetchone()[0]
            baseline = insert(db,"ingestion_baseline",id=uuid4(),lottery_id=cat["lottery"],source_id=cat["sources"][self.plan.source_key],
                artifact_id=artifact,first_sequence=1,last_sequence=2954,manifest_hash=self.plan.fingerprint,
                audit_reference="TEST_ONLY: old reference",audited_at=NOW,materialization_status="referenced")
            insert(db,"sync_checkpoint",id=uuid4(),lottery_id=cat["lottery"],source_id=cat["sources"][self.plan.source_key],
                stream_key="legacy",strategy="official_numeric_sequence",baseline_id=baseline,cursor_sequence=2954,review_next=2955)
        before = (self.query("SELECT * FROM lb.ingestion_baseline"),self.query("SELECT * FROM lb.sync_checkpoint"))
        migrate(url)
        self.assertEqual(before,(self.query("SELECT * FROM lb.ingestion_baseline"),self.query("SELECT * FROM lb.sync_checkpoint")))
        self.assertEqual(0,self.count("baseline_activation"))
