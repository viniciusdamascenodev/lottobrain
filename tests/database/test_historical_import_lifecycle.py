"""Dublês SQL, sem conexão: não substituem a carga real no runner isolado.

Mantidos com as dependências opcionais de banco, não na suíte pura/comum.
"""
import unittest
from unittest.mock import Mock

from app.infrastructure.postgres.historical_import import PgHistoricalImportRepository


class HistoricalImportLifecycleTests(unittest.TestCase):
    def assert_terminal_preserved(self,status,qualified):
        db = Mock()
        db.execute.return_value.fetchone.return_value = {"status":status}
        repository = PgHistoricalImportRepository(db,lambda *args:None)
        repository._coverage = Mock(return_value={"qualified":qualified,"run_status":status})
        report = repository.finish({"run_id":"unit-test-run","receipt_id":"unit-test-receipt"},None)
        self.assertEqual({"qualified":qualified,"run_status":status},report)
        self.assertFalse(any(call.args[0].startswith("UPDATE") for call in db.execute.call_args_list))

    def test_completed_with_current_audit_rejected_is_not_rewritten(self):
        self.assert_terminal_preserved("completed",False)

    def test_stopped_with_current_audit_qualified_is_not_promoted(self):
        self.assert_terminal_preserved("stopped",True)

    def test_failed_with_current_audit_qualified_is_not_promoted(self):
        self.assert_terminal_preserved("failed",True)
