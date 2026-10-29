"""Harness compartilhado de persistência; somente clusters criados pelo runner."""
from datetime import datetime, timezone
import os
import json
from pathlib import Path
import tempfile
import unittest
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from sqlalchemy.engine import make_url

from app.application.persist_mega_sena import CaptureMegaSena, ProcessMegaSena
from app.application.collect_mega_sena import FetchResponse
from app.application.persistence import transact
from app.infrastructure.postgres.uow import PgUnitOfWorkFactory
from app.infrastructure.postgres.catalog import ENDPOINT
from app.infrastructure.raw_storage import LocalRawStorage
from support import ROOT, insert, seed_catalog, seed_tiers
from test_integrity import migrate

BODY = (ROOT / "tests/fixtures/mega_sena_api_2954.json").read_bytes()


def changed_body(delta=1):
    # Correção SIMULADA de um campo sobre fixture real, nunca dado operacional.
    payload = json.loads(BODY)
    payload["valorEstimadoProximoConcurso"] += delta
    return json.dumps(payload,ensure_ascii=False).encode("utf-8")


class Source:
    def __init__(self, body=BODY, status=200, probe=lambda:None, error=None):
        self.body,self.status,self.probe,self.error = body,status,probe,error
        self.calls = 0

    def fetch(self, contest):
        self.calls += 1
        self.probe()
        if self.error:
            raise self.error
        return FetchResponse(self.body,ENDPOINT if contest is None else f"{ENDPOINT}/{contest}",self.status,
                             "application/json",datetime.now(timezone.utc))


class IsolatedPersistenceCase(unittest.TestCase):
    @classmethod
    def prepare_catalog(cls, db):
        catalog = seed_catalog(db)
        seed_tiers(db, catalog)
        return catalog

    @classmethod
    def setUpClass(cls):
        url = os.environ.get("LOTTOBRAIN_DATABASE_URL")
        expected = os.environ.get("LOTTOBRAIN_TEST_ISOLATED")
        if not url or not expected:
            raise RuntimeError("Use o runner PostgreSQL isolado; não executar em banco operacional.")
        parsed = make_url(url)
        cls.owner = dict(host=parsed.host,port=parsed.port,user=parsed.username,password=parsed.password)
        cls.template = "lottobrain_test_" + cls.__name__.lower()
        with psycopg.connect(os.environ["LOTTOBRAIN_TEST_ADMIN_DSN"],autocommit=True) as admin:
            actual = Path(admin.execute("SHOW data_directory").fetchone()[0]).resolve()
            if actual != Path(expected).resolve() or not actual.is_relative_to((ROOT/".local-postgres/runs").resolve()):
                raise RuntimeError("Cluster não autorizado para testes.")
            admin.execute(sql.SQL("CREATE DATABASE {} OWNER lb_migrator").format(sql.Identifier(cls.template)))
        migrate(parsed.set(database=cls.template).render_as_string(hide_password=False))
        with psycopg.connect(**cls.owner,dbname=cls.template) as db:
            cls.catalog = cls.prepare_catalog(db)
        with psycopg.connect(os.environ["LOTTOBRAIN_TEST_ADMIN_DSN"],autocommit=True) as admin:
            if not admin.execute("SELECT 1 FROM pg_roles WHERE rolname='lb_test_ingestor'").fetchone():
                admin.execute(sql.SQL("CREATE ROLE lb_test_ingestor LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {}")
                              .format(sql.Literal(parsed.password)))
        with psycopg.connect(**dict(cls.owner,user="lb_admin"),dbname=cls.template,autocommit=True) as admin:
            admin.execute((ROOT/"scripts/database/roles.sql").read_text(encoding="utf-8"))
            admin.execute("GRANT lottobrain_ingest TO lb_test_ingestor")

    def setUp(self):
        self.database = "lottobrain_test_case_" + uuid4().hex
        with psycopg.connect(os.environ["LOTTOBRAIN_TEST_ADMIN_DSN"],autocommit=True) as admin:
            admin.execute(sql.SQL("CREATE DATABASE {} TEMPLATE {} OWNER lb_migrator")
                          .format(sql.Identifier(self.database),sql.Identifier(self.template)))
        self.owner_args = dict(self.owner,dbname=self.database)
        self.connections = []
        self.temporary = tempfile.TemporaryDirectory()
        self.storage = LocalRawStorage(Path(self.temporary.name))
        self.factory = self.units()

    def tearDown(self):
        self.assertTrue(all(c.closed for c in self.connections),"UoW deixou conexão aberta")
        self.temporary.cleanup()

    def units(self, observe=lambda stage,db:None):
        def connect():
            connection = psycopg.connect(**dict(self.owner_args,user="lb_test_ingestor"),row_factory=dict_row,
                                         application_name="lottobrain-pg-ingestion",connect_timeout=10)
            self.connections.append(connection)
            return connection
        return PgUnitOfWorkFactory(connect=connect,observe=observe)

    def query(self, statement, params=()):
        with psycopg.connect(**self.owner_args) as db:
            return db.execute(statement,params).fetchall()

    def count(self, table):
        return self.query(sql.SQL("SELECT count(*) FROM lb.{}").format(sql.Identifier(table)))[0][0]

    def capture(self, body=BODY, status=200, key=None):
        return CaptureMegaSena(self.factory,self.storage,Source(body,status)).execute(2954,key or str(uuid4()))

    def process(self, receipt, key=None, units=None, advance=None):
        return ProcessMegaSena(units or self.factory,self.storage).execute(receipt,key or str(uuid4()),advance=advance)

    def checkpoint(self):
        cat = self.catalog["mega_sena"]
        source = cat["sources"]["caixa_mega_sena_json"]
        with psycopg.connect(**self.owner_args) as db:
            artifact = db.execute("SELECT id,sha256 FROM lb.raw_artifact LIMIT 1").fetchone()
            baseline = insert(db,"ingestion_baseline",id=uuid4(),lottery_id=cat["lottery"],source_id=source,
                artifact_id=artifact[0],first_sequence=1,last_sequence=2953,manifest_hash=artifact[1],
                audit_reference="TEST_ONLY: fronteira simulada, não baseline histórica aprovada",audited_at=datetime.now(timezone.utc),
                materialization_status="referenced")
            return insert(db,"sync_checkpoint",id=uuid4(),lottery_id=cat["lottery"],source_id=source,
                stream_key="test_forward",strategy="official_numeric_sequence",baseline_id=baseline,cursor_sequence=2953,review_next=2954)

    def claim(self, checkpoint):
        return transact(self.factory,lambda unit: unit.sync.claim_lease(checkpoint,unit.catalog.qualify(),300))
