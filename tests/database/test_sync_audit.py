"""Auditor somente leitura com aprovação/carga reais em cluster descartável."""
import json
import os
from uuid import UUID, uuid4

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from app.application.activate_mega_sena_baseline import ActivateMegaSenaBaseline, BaselineRequest
from app.application.audit_sync_postgres import AuditMegaSenaPostgres, SyncAuditRequest
from app.application.historical_import import ImportMegaSenaHistory, prepare_history_file
from app.application.persistence import PersistenceError, transact
from app.application.sync_postgres import SyncBatchRequest, SyncMegaSenaPostgres
from app.application.sync_mega_sena import SyncPolicy
from app.infrastructure.postgres.sync_audit import PgSyncAuditReader
from baseline_support import BaselineCase
from persistence_support import Source
from support import ROOT
from sync_fixture_support import approved_fixture, publish_approved_fixture

BODY2955 = (ROOT / "tests/fixtures/mega_sena_api_2955.json").read_bytes()
BODY3071 = (ROOT / "tests/fixtures/mega_sena_api_3071.json").read_bytes()


class PostgreSQLSyncAuditTests(BaselineCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cached = approved_fixture()
        cls.raw_body = (ROOT / "data/raw/mega_sena/mega_sena_resultados.xlsx").read_bytes()
        if cached:
            cls.template, cls.catalog = cached["template"], cached["catalog"]
            cls.checkpoint_id = cached["checkpoint"]
        else:
            seed = cls("test_01_completed_batch_is_healthy_and_all_tables_unchanged")
            seed.setUp()
            try:
                plan = prepare_history_file(ROOT / "data/raw/mega_sena/mega_sena_resultados.xlsx")
                def progress(stage, row):
                    if stage == "after_row" and int(row.contest) % 500 == 0:
                        print(f"SPEC0032_FIXTURE: {row.contest}/2954 real records committed", flush=True)
                result = ImportMegaSenaHistory(seed.factory, seed.storage, progress).execute(plan, "audit-history")
                seed.assertTrue(result["qualified"])
                activation = ActivateMegaSenaBaseline(seed.bootstrap_units(), seed.storage).execute(
                    BaselineRequest("audit-approval", "audit-history", plan.fingerprint, "TEST_ONLY: SPEC-0032 fixture"))
                cls.checkpoint_id = UUID(activation["checkpoint_id"])
                publish_approved_fixture(seed, cls.checkpoint_id)
                cls.template = approved_fixture()["template"]
            finally:
                seed.tearDown()
        with psycopg.connect(os.environ["LOTTOBRAIN_TEST_ADMIN_DSN"], autocommit=True) as admin:
            if not admin.execute("SELECT 1 FROM pg_roles WHERE rolname='lb_test_auditor'").fetchone():
                admin.execute(sql.SQL("CREATE ROLE lb_test_auditor LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {}")
                              .format(sql.Literal(cls.owner["password"])))
            admin.execute("GRANT lottobrain_audit TO lb_test_auditor")

    def setUp(self):
        super().setUp()
        self.storage.put(self.raw_body)

    def audit_connection(self):
        db = psycopg.connect(**dict(self.owner_args, user="lb_test_auditor"), row_factory=dict_row)
        self.connections.append(db)
        return db

    def audit(self, *, reader=None, storage=None, **limits):
        return AuditMegaSenaPostgres(reader or PgSyncAuditReader(connect=self.audit_connection),
                                    storage or self.storage).execute(SyncAuditRequest(self.checkpoint_id, **limits))

    def sync(self, key="batch", source=None, observe=lambda stage, op: None, units=None):
        return SyncMegaSenaPostgres(units or self.factory, self.storage, source or Source(BODY2955),
                                   wait=lambda seconds: None, observe=observe).execute(
                                       SyncBatchRequest(self.checkpoint_id, key, SyncPolicy(1, 0, 2)))

    def footprint(self):
        with psycopg.connect(**self.owner_args) as db:
            tables = db.execute("SELECT tablename FROM pg_tables WHERE schemaname='lb' ORDER BY tablename").fetchall()
            return {name: db.execute(sql.SQL("SELECT md5(coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]')::text) FROM lb.{} t")
                                     .format(sql.Identifier(name))).fetchone()[0] for name, in tables}

    def test_01_completed_batch_is_healthy_and_all_tables_unchanged(self):
        self.sync()
        before = self.footprint()
        files = {p.relative_to(self.storage.root): p.read_bytes() for p in self.storage.root.rglob("*") if p.is_file()}
        report = self.audit()
        self.assertEqual(("healthy", 2955, 1), (report["status"], report["cursor_claimed"], report["steps_checked"]))
        self.assertEqual([], report["issues"])
        self.assertEqual(before, self.footprint())
        self.assertEqual(files, {p.relative_to(self.storage.root): p.read_bytes() for p in self.storage.root.rglob("*") if p.is_file()})
        self.assertTrue(all(c.closed for c in self.connections))
        print("SPEC0032_REPORT=" + json.dumps(report, sort_keys=True, separators=(",", ":")), flush=True)

    def test_02_not_found_and_unapproved_checkpoint(self):
        reader = PgSyncAuditReader(connect=self.audit_connection)
        report = AuditMegaSenaPostgres(reader, self.storage).execute(SyncAuditRequest(uuid4()))
        self.assertEqual("not_found", report["status"])
        self.process(self.capture())
        referenced = self.checkpoint()
        report = AuditMegaSenaPostgres(reader, self.storage).execute(SyncAuditRequest(referenced))
        self.assertEqual("inconsistent", report["status"])
        self.assertIn("approved_baseline_missing", report["issue_counts"])

    def test_03_receipt_committed_before_attach_is_diagnosed_without_recovery(self):
        def stop(stage, op):
            if stage == "receipt_committed":
                raise RuntimeError("TEST_ONLY: attachment response interrupted")
        with self.assertRaises(RuntimeError):
            self.sync(observe=stop)
        before = self.footprint()
        report = self.audit()
        self.assertEqual("attention", report["status"])
        self.assertIn("operation_receipt_unattached", report["issue_counts"])
        self.assertIn("running_interrupted", report["issue_counts"])
        self.assertEqual(before, self.footprint())

    def test_04_inconclusive_capture_never_gets_again(self):
        source = Source(BODY2955)
        original = self.storage.put
        self.storage.put = lambda body: (_ for _ in ()).throw(PersistenceError("storage_unavailable"))
        with self.assertRaises(PersistenceError):
            self.sync(source=source)
        self.storage.put = original
        report = self.audit()
        self.assertEqual("attention", report["status"])
        self.assertIn("operation_capture_unresolved", report["issue_counts"])
        self.assertEqual(1, source.calls)
        self.assertIn({"action": "investigate_capture_without_reissuing_http", "automatic": False}, report["recommendations"])

    def test_05_missing_and_corrupt_bytes_do_not_change_sql(self):
        self.sync()
        path = next(p for p in self.storage.root.rglob("*.bin") if p.read_bytes() == BODY2955)
        before = self.footprint()
        path.unlink()  # Dano apenas no storage temporário do teste.
        report = self.audit()
        self.assertEqual("inconsistent", report["status"])
        self.assertIn("artifact_bytes_missing", report["issue_counts"])
        path.write_bytes(b"TEST_ONLY: corrupt object")
        report = self.audit()
        self.assertIn("artifact_bytes_mismatch", report["issue_counts"])
        self.assertEqual(before, self.footprint())

    def test_06_old_terminal_and_blocked_source_remain_readable(self):
        first = self.sync("first", source=Source(BODY3071))
        self.sync("second")
        self.query("UPDATE lb.data_source SET readiness='blocked' WHERE key='caixa_mega_sena_json' RETURNING id")
        report = self.audit()
        self.assertEqual("attention", report["status"])
        self.assertIn("source_not_qualified_for_collection", report["issue_counts"])
        self.assertFalse(any(i["severity"] == "error" for i in report["issues"]))
        self.assertEqual(first["cursor_after"], report["batches"][0]["cursor_verified_at_end"])
        self.assertEqual((2954, 2955), (first["cursor_after"], report["cursor_claimed"]))

    def test_07_bounded_snapshot_never_reports_healthy(self):
        self.sync("first")
        self.sync("second")
        report = self.audit(max_batches=1)
        self.assertEqual(("incomplete", ["batches"]), (report["status"], report["truncated"]))

    def test_08_repeatable_snapshot_and_storage_outside_connection(self):
        case = self
        class ConcurrentConnection:
            autocommit = False
            def __init__(self):
                self.db = case.audit_connection()
                self.triggered = False
            def execute(self, statement, params=None):
                cursor = self.db.execute(statement, params)
                if statement.startswith("SELECT * FROM lb.sync_checkpoint") and not self.triggered:
                    self.triggered = True
                    case.sync("concurrent")
                return cursor
            def rollback(self): self.db.rollback()
            def close(self): self.db.close()
        class AuditStorage:
            def read(self, *args):
                case.assertTrue(all(c.closed for c in case.connections), "auditor leu storage com SQL aberto")
                return case.storage.read(*args)
        # Escritor concorrente usa seu storage normalmente enquanto o snapshot
        # de leitura está aberto. A guarda observa somente o I/O do auditor.
        report = self.audit(reader=PgSyncAuditReader(connect=ConcurrentConnection), storage=AuditStorage())
        self.assertEqual(("healthy", 2954, []), (report["status"], report["cursor_claimed"], report["batches"]))
        self.assertEqual(2955, self.query("SELECT cursor_sequence FROM lb.sync_checkpoint")[0][0])

    def test_09_audit_role_and_read_only_transaction_reject_writes(self):
        with self.audit_connection() as db:
            privileges = db.execute("""SELECT
                has_table_privilege(current_user,'lb.sync_checkpoint','UPDATE') AS checkpoint_write,
                has_table_privilege(current_user,'lb.sync_batch','INSERT') AS batch_write,
                has_table_privilege(current_user,'lb.ingestion_baseline','INSERT') AS bootstrap""").fetchone()
            self.assertEqual((False, False, False), tuple(privileges.values()))
        class WriterProbe(PgSyncAuditReader):
            def _snapshot(self, db, request):
                db.execute("UPDATE lb.sync_checkpoint SET row_version=row_version+1")
        # Mesmo um login escritor fica bloqueado pelo modo READ ONLY do adaptador.
        def owner_connect():
            db = psycopg.connect(**self.owner_args, row_factory=dict_row)
            self.connections.append(db)
            return db
        with self.assertRaisesRegex(PersistenceError, "audit_database_unavailable"):
            self.audit(reader=WriterProbe(connect=owner_connect))
        self.assertTrue(all(c.closed for c in self.connections))

    def test_10_summary_pending_and_cooldown_are_attention(self):
        def stop(stage, db):
            if stage == "after_batch_finished":
                raise RuntimeError("TEST_ONLY: summary interrupted")
        with self.assertRaises(RuntimeError):
            self.sync(units=self.units(stop))
        report = self.audit()
        self.assertEqual("attention", report["status"])
        self.assertIn("batch_summary_or_next_operation_pending", report["issue_counts"])
        self.sync()  # Recuperação explícita apenas pelo teste, nunca pelo auditor.
        self.sync("cooldown", source=Source(b"{}", 429))
        report = self.audit()
        self.assertEqual("attention", report["status"])
        self.assertIn("source_cooldown", report["issue_counts"])
