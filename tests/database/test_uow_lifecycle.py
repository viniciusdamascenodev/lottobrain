"""Falhas de infraestrutura simuladas; complementam, não substituem testes PG."""
import unittest
import psycopg

from app.application.persistence import PersistenceError
from app.infrastructure.postgres.uow import PgUnitOfWork


class Connection:
    def __init__(self, commit_error=None,rollback_error=None,execute_error=None):
        self.commit_error,self.rollback_error,self.execute_error = commit_error,rollback_error,execute_error
        self.closed = False
        self.commits,self.rollbacks = 0,0
    def execute(self,*args):
        if self.execute_error: raise self.execute_error
    def commit(self):
        self.commits += 1
        if self.commit_error: raise self.commit_error
    def rollback(self):
        self.rollbacks += 1
        if self.rollback_error: raise self.rollback_error
    def close(self): self.closed = True


class UnitOfWorkLifecycleTests(unittest.TestCase):
    def test_success_closes_and_commits_once(self):
        conn = Connection()
        with PgUnitOfWork(lambda:conn): pass
        self.assertEqual((True,1,0),(conn.closed,conn.commits,conn.rollbacks))

    def test_body_error_closes_even_when_rollback_fails(self):
        conn = Connection(rollback_error=OSError("test-rollback-failure"))
        with self.assertRaisesRegex(PersistenceError,"test-body"):
            with PgUnitOfWork(lambda:conn): raise PersistenceError("test-body")
        self.assertEqual((True,0,1),(conn.closed,conn.commits,conn.rollbacks))

    def test_commit_constraint_error_is_known_failure_and_closes(self):
        conn = Connection(commit_error=psycopg.errors.CheckViolation("test-constraint"))
        with self.assertRaisesRegex(PersistenceError,"invalid_revision"):
            with PgUnitOfWork(lambda:conn): pass
        self.assertEqual((True,1,1),(conn.closed,conn.commits,conn.rollbacks))

    def test_commit_io_error_is_ambiguous_not_automatic_retry(self):
        conn = Connection(commit_error=OSError("test-lost-commit"))
        with self.assertRaisesRegex(PersistenceError,"commit_outcome_unknown"):
            with PgUnitOfWork(lambda:conn): pass
        self.assertTrue(conn.closed)

    def test_initialization_failure_also_closes(self):
        conn = Connection(execute_error=psycopg.OperationalError("test-init-error"))
        with self.assertRaisesRegex(PersistenceError,"database_unavailable"):
            with PgUnitOfWork(lambda:conn): pass
        self.assertTrue(conn.closed)
