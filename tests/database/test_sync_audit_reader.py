"""Dublês de ciclo de conexão; não substituem as provas reais em test_sync_audit."""
import unittest
from uuid import uuid4

from app.application.audit_sync_postgres import SyncAuditRequest
from app.application.persistence import PersistenceError
from app.infrastructure.postgres.sync_audit import PgSyncAuditReader


class Connection:
    autocommit = False

    def __init__(self, *, rollback_error=False, close_error=False):
        self.statements = []
        self.closed = False
        self.rollbacks = 0
        self.rollback_error, self.close_error = rollback_error, close_error

    def execute(self, statement): self.statements.append(statement)
    def rollback(self):
        self.rollbacks += 1
        if self.rollback_error: raise OSError("TEST_ONLY: rollback failure")
    def close(self):
        self.closed = True
        if self.close_error: raise OSError("TEST_ONLY: secret connection detail")


class Reader(PgSyncAuditReader):
    def _snapshot(self, db, request):
        return {"TEST_ONLY": "snapshot"}


class SyncAuditReaderLifecycleTests(unittest.TestCase):
    def test_success_sets_read_only_before_queries_and_closes_without_commit(self):
        db = Connection()
        self.assertEqual({"TEST_ONLY": "snapshot"}, Reader(connect=lambda: db).read(SyncAuditRequest(uuid4())))
        self.assertEqual("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY", db.statements[0])
        self.assertEqual((1, True), (db.rollbacks, db.closed))

    def test_snapshot_error_is_sanitized_and_connection_closed(self):
        db = Connection()
        class Failure(Reader):
            def _snapshot(self, db, request): raise OSError("TEST_ONLY: secret SQL DSN")
        with self.assertRaisesRegex(PersistenceError, "^audit_database_unavailable$"):
            Failure(connect=lambda: db).read(SyncAuditRequest(uuid4()))
        self.assertTrue(db.closed)

    def test_rollback_error_cannot_hide_primary_error_or_prevent_close(self):
        db = Connection(rollback_error=True)
        class Failure(Reader):
            def _snapshot(self, db, request): raise ValueError("primary bug")
        with self.assertRaisesRegex(ValueError, "primary bug"):
            Failure(connect=lambda: db).read(SyncAuditRequest(uuid4()))
        self.assertTrue(db.closed)

    def test_connect_failure_is_sanitized(self):
        def connect(): raise OSError("TEST_ONLY: secret DSN")
        with self.assertRaisesRegex(PersistenceError, "^audit_database_unavailable$"):
            Reader(connect=connect).read(SyncAuditRequest(uuid4()))

    def test_close_failure_is_sanitized_instead_of_returning_success(self):
        db = Connection(close_error=True)
        with self.assertRaisesRegex(PersistenceError, "^audit_database_unavailable$"):
            Reader(connect=lambda: db).read(SyncAuditRequest(uuid4()))

    def test_autocommit_connection_is_refused_before_queries(self):
        db = Connection()
        db.autocommit = True
        with self.assertRaisesRegex(PersistenceError, "audit_requires_transactional_connection"):
            Reader(connect=lambda: db).read(SyncAuditRequest(uuid4()))
        self.assertEqual([], db.statements)
        self.assertTrue(db.closed)
