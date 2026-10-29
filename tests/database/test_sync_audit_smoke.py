"""Guardas finais do leitor em PostgreSQL real, sem precisar de carga histórica."""
from uuid import uuid4
import psycopg
from psycopg.rows import dict_row

from app.application.audit_sync_postgres import SyncAuditRequest
from app.application.persistence import PersistenceError
from app.infrastructure.postgres.sync_audit import PgSyncAuditReader
from persistence_support import IsolatedPersistenceCase


class PostgreSQLSyncAuditSmokeTests(IsolatedPersistenceCase):
    def connect(self, *, autocommit=False):
        db = psycopg.connect(**self.owner_args, row_factory=dict_row, autocommit=autocommit)
        self.connections.append(db)
        return db

    def test_real_read_only_snapshot_rollback_and_close(self):
        case = self
        class Probe(PgSyncAuditReader):
            def _snapshot(self, db, request):
                settings = db.execute("SELECT current_setting('transaction_read_only') AS ro, current_setting('transaction_isolation') AS isolation").fetchone()
                case.assertEqual({"ro": "on", "isolation": "repeatable read"}, settings)
                return super()._snapshot(db, request)
        snapshot = Probe(connect=self.connect).read(SyncAuditRequest(uuid4()))
        self.assertIsNone(snapshot["checkpoint"])
        self.assertTrue(all(c.closed for c in self.connections))

    def test_real_writer_cannot_mutate_in_read_only_snapshot(self):
        class Probe(PgSyncAuditReader):
            def _snapshot(self, db, request):
                db.execute("UPDATE lb.data_source SET readiness=readiness")
        before = self.query("SELECT id,readiness FROM lb.data_source ORDER BY id")
        with self.assertRaisesRegex(PersistenceError, "^audit_database_unavailable$"):
            Probe(connect=self.connect).read(SyncAuditRequest(uuid4()))
        self.assertEqual(before, self.query("SELECT id,readiness FROM lb.data_source ORDER BY id"))
        self.assertTrue(all(c.closed for c in self.connections))

    def test_real_autocommit_is_refused_and_closed(self):
        with self.assertRaisesRegex(PersistenceError, "audit_requires_transactional_connection"):
            PgSyncAuditReader(connect=lambda: self.connect(autocommit=True)).read(SyncAuditRequest(uuid4()))
        self.assertTrue(all(c.closed for c in self.connections))
