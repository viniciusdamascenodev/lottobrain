"""Papel de bootstrap somente em cluster descartável; sem credenciais persistidas."""
import os
import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from app.infrastructure.postgres.uow import PgUnitOfWorkFactory
from persistence_support import IsolatedPersistenceCase


class BaselineCase(IsolatedPersistenceCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with psycopg.connect(os.environ["LOTTOBRAIN_TEST_ADMIN_DSN"],autocommit=True) as admin:
            if not admin.execute("SELECT 1 FROM pg_roles WHERE rolname='lb_test_bootstrap'").fetchone():
                admin.execute(sql.SQL("CREATE ROLE lb_test_bootstrap LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {}")
                              .format(sql.Literal(cls.owner["password"])))
            admin.execute("GRANT lottobrain_bootstrap TO lb_test_bootstrap")

    def bootstrap_units(self, observe=lambda stage,db:None):
        def connect():
            connection = psycopg.connect(**dict(self.owner_args,user="lb_test_bootstrap"),row_factory=dict_row,
                                         application_name="lottobrain-test-baseline",connect_timeout=10)
            self.connections.append(connection)
            return connection
        return PgUnitOfWorkFactory(connect=connect,observe=observe)
