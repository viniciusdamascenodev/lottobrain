"""Admissão/migration rápidas; baseline referenciada não autoriza o orquestrador."""
import os
from uuid import uuid4
import psycopg
from sqlalchemy.engine import make_url

from app.application.persistence import PersistenceError
from app.application.sync_postgres import SyncBatchRequest, SyncMegaSenaPostgres
from baseline_support import BaselineCase
from persistence_support import Source
from test_integrity import migrate


class SyncBatchSmokeTests(BaselineCase):
    def test_01_no_implicit_bootstrap_or_http(self):
        source=Source()
        service=SyncMegaSenaPostgres(self.factory,self.storage,source,wait=lambda seconds:None)
        with self.assertRaisesRegex(PersistenceError,"checkpoint_conflict"):
            service.execute(SyncBatchRequest(uuid4(),"missing"))
        self.process(self.capture())
        checkpoint=self.checkpoint()
        with self.assertRaisesRegex(PersistenceError,"sync_not_initialized"):
            service.execute(SyncBatchRequest(checkpoint,"referenced"))
        self.assertEqual(0,source.calls)
        self.assertEqual((0,0),(self.count("sync_batch"),self.count("sync_batch_operation")))

    def test_02_ingestor_cannot_bootstrap_and_bootstrap_cannot_run_batches(self):
        for user,expected in (("lb_test_ingestor",(True,False)),("lb_test_bootstrap",(False,True))):
            with psycopg.connect(**dict(self.owner_args,user=user)) as db:
                self.assertEqual(expected,db.execute("""SELECT has_table_privilege(current_user,'lb.sync_batch','INSERT'),
                    has_table_privilege(current_user,'lb.ingestion_baseline','INSERT')""").fetchone())

    def test_03_empty_downgrade_and_reupgrade(self):
        url=make_url(os.environ["LOTTOBRAIN_DATABASE_URL"]).set(database=self.database).render_as_string(hide_password=False)
        migrate(url,"0030_01",down=True)
        migrate(url)
        self.assertEqual([("0031_01",)],self.query("SELECT version_num FROM alembic_version"))
        self.assertEqual(0,self.count("sync_batch"))
