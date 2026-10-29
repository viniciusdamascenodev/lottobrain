"""Amostras reais e falhas controladas; sem coleta ou carga histórica integral."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from hashlib import sha256
import json
import os
from contextlib import closing, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from app.application.datasets import DatasetService
from app.application.historical_content import canonical_bytes
from app.application.historical_pilot import PreparedRow
from app.application.persistence import PersistenceError
from app.application.result_persistence import (
    MAX_ARTIFACT_BYTES,
    PersistQualifiedResult,
    PreparedResult,
)
from app.infrastructure.persistence_samples import prepare_sample
from app.infrastructure.postgres.content_reader import read_contents
from app.infrastructure.postgres.profile_catalog import bootstrap_catalog
from app.infrastructure.postgres.uow import PgUnitOfWorkFactory
from app.infrastructure.raw_storage import LocalRawStorage
from app.ingestion import mega_sena
from app.interfaces.persistence import main as persistence_main
from persistence_support import IsolatedPersistenceCase
from support import ROOT, real_fixture


class SixLotteryPersistenceTests(IsolatedPersistenceCase):
    @classmethod
    def prepare_catalog(cls, db):
        db.row_factory = dict_row
        return bootstrap_catalog(db)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with psycopg.connect(os.environ["LOTTOBRAIN_TEST_ADMIN_DSN"], autocommit=True) as admin:
            for name, group in (
                ("lb_stage6_approver", "lottobrain_dataset_approver"),
                ("lb_stage6_reader", "lottobrain_reader"),
                ("lb_stage6_catalog", "lottobrain_catalog_admin"),
            ):
                admin.execute(
                    sql.SQL(
                        "CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {}"
                    ).format(sql.Identifier(name), sql.Literal(cls.owner["password"]))
                )
                admin.execute(
                    sql.SQL("GRANT {} TO {}").format(sql.Identifier(group), sql.Identifier(name))
                )

    def setUp(self):
        super().setUp()
        self.storage = LocalRawStorage(Path(self.temporary.name), max_bytes=MAX_ARTIFACT_BYTES)

    def role_units(self, user, observe=lambda stage, db: None):
        def connect():
            db = psycopg.connect(**dict(self.owner_args, user=user), row_factory=dict_row)
            self.connections.append(db)
            return db

        return PgUnitOfWorkFactory(connect=connect, observe=observe)

    def prepared(self, slug="mega_sena", index=0):
        candidate, body = real_fixture(slug, index)
        return PreparedResult.from_candidate(
            candidate, body, f"fixture-row:{index}", f"{slug}_rows.json"
        )

    def persist(self, prepared=None, key=None, units=None, allow_correction=False):
        return PersistQualifiedResult(units or self.factory, self.storage).execute(
            prepared or self.prepared(), key or str(uuid4()), allow_correction=allow_correction
        )

    def approver(self, observe=lambda stage, db: None):
        return DatasetService(self.role_units("lb_stage6_approver", observe))

    def reader(self):
        return DatasetService(self.role_units("lb_stage6_reader"))

    def approve(self, slug, results, source=None):
        service = self.approver()
        source = source or self.prepared(slug).source_key
        policy = service.policy(slug, "samples_v1", [source], "test-operator")
        return service.approve(
            policy, [r["revision_id"] for r in results], "test-operator", str(uuid4())
        )

    def simulated_correction(self):
        # Correção SIMULADA apenas neste teste, com bytes e normalização coerentes.
        candidate, body = real_fixture("mega_sena")
        rows = json.loads(body)
        rows[0]["Bola1"] = 1
        changed = json.dumps(rows, ensure_ascii=False).encode("utf-8")
        provenance = replace(candidate.provenance, raw_sha256=sha256(changed).hexdigest())
        normalized = mega_sena.normalize_row(rows[0], provenance)
        self.assertTrue(normalized.is_valid)
        return PreparedResult.from_candidate(
            normalized.candidate, changed, "fixture-row:0", "SIMULATED-correction.json"
        )

    def test_01_operational_bootstrap_is_idempotent_and_preserves_source_versions(self):
        with psycopg.connect(**self.owner_args, row_factory=dict_row) as db:
            self.assertEqual({"lotteries": 6, "rules": 20}, bootstrap_catalog(db))
            self.assertEqual({"lotteries": 6, "rules": 20}, bootstrap_catalog(db))
        self.assertEqual(6, self.count("lottery"))
        self.assertEqual(20, self.count("rule_version"))
        urls = dict(
            self.query(
                "SELECT key,base_url FROM lb.data_source WHERE key IN ('caixa_mega_sena_json','caixa_mega_sena_current')"
            )
        )
        self.assertIn("servicebus2", urls["caixa_mega_sena_json"])
        self.assertIn("servicebus3", urls["caixa_mega_sena_current"])

    def test_02_six_real_results_roundtrip_and_replay(self):
        for slug in (
            "mega_sena",
            "lotofacil",
            "mais_milionaria",
            "powerball",
            "mega_millions",
            "euro_millions",
        ):
            with self.subTest(lottery=slug):
                prepared = self.prepared(slug)
                key = str(uuid4())
                result = self.persist(prepared, key)
                self.assertEqual("new", result["outcome"])
                self.assertEqual(result, self.persist(prepared, key))
                second = self.persist(prepared)
                self.assertEqual("unchanged", second["outcome"])
                self.assertEqual(result["revision_id"], second["revision_id"])
                with psycopg.connect(**self.owner_args, row_factory=dict_row) as db:
                    content = read_contents(db, [result["revision_id"]])[result["revision_id"]]
                self.assertEqual(prepared.row.content, content)
        self.assertEqual(6, self.count("draw_revision"))
        self.assertEqual(12, self.count("candidate_observation"))
        self.assertEqual(6, self.count("raw_artifact"))

    def test_03_qualified_boundary_vectors_cover_all_twenty_rule_versions(self):
        vectors = json.loads(
            (ROOT / "tests/fixtures/historical_relational_v1.json").read_text(encoding="utf-8")
        )
        rules = set()
        count = 0
        for source in vectors["sources"]:
            body = (ROOT / source["source"]).read_bytes()
            self.assertEqual(source["raw_sha256"], sha256(body).hexdigest())
            for vector in source["vectors"]:
                content, evidence = vector["content"], vector["source_evidence"]
                row = PreparedRow(
                    f"data-record:{vector['data_record_ordinal']}",
                    content["identity"]["value"],
                    canonical_bytes(content),
                    canonical_bytes(evidence),
                )
                prepared = PreparedResult(
                    body,
                    evidence["source_key"],
                    source["normalizer_version"],
                    Path(source["source"]).name,
                    row,
                )
                result = self.persist(prepared)
                with psycopg.connect(**self.owner_args, row_factory=dict_row) as db:
                    self.assertEqual(
                        content, read_contents(db, [result["revision_id"]])[result["revision_id"]]
                    )
                rules.add((source["lottery"], content["rule_version"]))
                count += 1
        self.assertEqual(45, count)
        self.assertEqual(20, len(rules))

    def test_04_command_conflict_and_raw_mismatch_are_refused(self):
        key = str(uuid4())
        self.persist(self.prepared(), key)
        with self.assertRaises(PersistenceError) as error:
            self.persist(self.prepared(index=1), key)
        self.assertEqual("idempotency_conflict", error.exception.code)
        candidate, body = real_fixture("mega_sena")
        with self.assertRaises(PersistenceError):
            PreparedResult.from_candidate(candidate, body + b" ", "row", "test")
        self.assertEqual(1, self.count("draw_revision"))
        self.assertEqual(1, self.count("capture_receipt"))

    def test_05_conflict_is_quarantined_until_explicit_correction(self):
        original = self.persist()
        correction = self.simulated_correction()
        blocked = self.persist(correction)
        self.assertEqual("quarantined", blocked["outcome"])
        self.assertIsNone(blocked["revision_id"])
        self.assertEqual(1, self.count("draw_revision"))
        accepted = self.persist(correction, allow_correction=True)
        self.assertEqual("correction_candidate", accepted["outcome"])
        self.assertEqual(2, accepted["revision_no"])
        self.assertEqual(original["draw_id"], accepted["draw_id"])
        self.assertEqual([(None,)], self.query("SELECT published_revision_id FROM lb.draw"))

    def test_06_failure_rolls_back_whole_result(self):
        def fail(stage, db):
            if stage == "after_qualified_result":
                raise PersistenceError("forced_failure")

        with self.assertRaises(PersistenceError):
            self.persist(units=self.units(fail))
        for table in (
            "draw",
            "draw_revision",
            "capture_receipt",
            "processing_run",
            "ingestion_run",
            "raw_artifact",
        ):
            self.assertEqual(0, self.count(table), table)

    def test_07_concurrent_writes_share_one_revision_and_keep_two_receipts(self):
        prepared = self.prepared("mais_milionaria")
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.persist(prepared), range(2)))
        self.assertEqual(1, len({r["revision_id"] for r in results}))
        self.assertEqual({"new", "unchanged"}, {r["outcome"] for r in results})
        self.assertEqual(2, self.count("capture_receipt"))

    def test_08_six_approved_datasets_can_be_read_by_minimal_role(self):
        for slug in (
            "mega_sena",
            "lotofacil",
            "mais_milionaria",
            "powerball",
            "mega_millions",
            "euro_millions",
        ):
            prepared = self.prepared(slug)
            result = self.persist(prepared)
            with self.assertRaises(PersistenceError):
                self.reader().read(slug)
            dataset = self.approve(slug, [result])
            self.approver().activate(dataset, 0, "test-operator", str(uuid4()))
            page = self.reader().read(slug)
            self.assertEqual(dataset, page["dataset_id"])
            self.assertEqual(1, page["total"])
            self.assertEqual(prepared.row.content, page["items"][0]["content"])
            self.assertTrue(page["items"][0]["references"])

    def test_09_reader_and_ingestor_cannot_bypass_approval(self):
        result = self.persist()
        with self.assertRaises(PersistenceError):
            DatasetService(self.factory).policy(
                "mega_sena", "forbidden", [self.prepared().source_key], "ingestor"
            )
        for table in (
            "draw_revision",
            "candidate_observation",
            "capture_receipt",
            "raw_artifact",
            "dataset_member",
        ):
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                with psycopg.connect(**dict(self.owner_args, user="lb_stage6_reader")) as db:
                    db.execute(sql.SQL("SELECT * FROM lb.{}").format(sql.Identifier(table)))
        with psycopg.connect(**dict(self.owner_args, user="lb_stage6_reader")) as db:
            self.assertEqual(
                [],
                db.execute(
                    "SELECT id FROM lb.approved_draw_revision WHERE id=%s", (result["revision_id"],)
                ).fetchall(),
            )
        self.assertEqual(0, self.count("approved_dataset"))

    def test_10_approval_replay_conflicts_and_cross_lottery_are_rejected(self):
        first, second = self.persist(), self.persist(self.prepared("lotofacil"))
        service = self.approver()
        policy = service.policy(
            "mega_sena", "samples_v1", [self.prepared().source_key], "test-operator"
        )
        key = str(uuid4())
        dataset = service.approve(policy, [first["revision_id"]], "test-operator", key)
        self.assertEqual(
            dataset, service.approve(policy, [first["revision_id"]], "test-operator", key)
        )
        with self.assertRaises(PersistenceError):
            service.approve(policy, [second["revision_id"]], "test-operator", key)
        with self.assertRaises(PersistenceError):
            service.approve(policy, [second["revision_id"]], "test-operator", str(uuid4()))
        self.assertEqual(1, self.count("approved_dataset"))

    def test_11_sql_rejects_tampered_manifest_and_late_member_changes(self):
        result = self.persist()
        service = self.approver()
        policy = service.policy(
            "mega_sena", "samples_v1", [self.prepared().source_key], "test-operator"
        )
        with patch("app.infrastructure.postgres.datasets.manifest_hash", return_value="a" * 64):
            with self.assertRaises(PersistenceError):
                service.approve(policy, [result["revision_id"]], "test-operator", str(uuid4()))
        self.assertEqual(0, self.count("approved_dataset"))
        dataset = service.approve(policy, [result["revision_id"]], "test-operator", str(uuid4()))
        for statement in (
            "UPDATE lb.approved_dataset SET member_count=2 WHERE id=%s",
            "DELETE FROM lb.dataset_member WHERE dataset_id=%s",
            "UPDATE lb.dataset_member SET ordinal=2 WHERE dataset_id=%s",
        ):
            with self.assertRaises(psycopg.errors.CheckViolation):
                with psycopg.connect(**self.owner_args) as db:
                    db.execute(statement, (dataset,))

    def test_12_pagination_remains_on_selected_dataset_after_promotion(self):
        results = [self.persist(self.prepared(index=i)) for i in (0, 1)]
        older = self.approve("mega_sena", results)
        service = self.approver()
        service.activate(older, 0, "test-operator", str(uuid4()))
        first = self.reader().read("mega_sena", limit=1)
        corrected = self.persist(self.simulated_correction(), allow_correction=True)
        newer = self.approve("mega_sena", [corrected, results[1]])
        service.activate(newer, 1, "test-operator", str(uuid4()))
        second = self.reader().read("mega_sena", dataset_id=first["dataset_id"], offset=1, limit=1)
        self.assertEqual(older, second["dataset_id"])
        self.assertEqual(results[1]["revision_id"], second["items"][0]["revision_id"])
        self.assertEqual(newer, self.reader().read("mega_sena")["dataset_id"])
        self.assertEqual(older, self.reader().read("mega_sena", dataset_id=older)["dataset_id"])

    def test_13_activation_is_optimistic_audited_and_idempotent(self):
        result = self.persist()
        dataset = self.approve("mega_sena", [result])
        service = self.approver()
        key = str(uuid4())
        first = service.activate(dataset, 0, "test-operator", key)
        self.assertEqual(first, service.activate(dataset, 0, "test-operator", key))
        with self.assertRaises(PersistenceError) as error:
            service.activate(dataset, 0, "test-operator", str(uuid4()))
        self.assertEqual("dataset_activation_conflict", error.exception.code)
        self.assertEqual(2, self.count("dataset_decision"))

    def test_14_approval_failure_preserves_prior_active_dataset(self):
        result = self.persist()
        dataset = self.approve("mega_sena", [result])
        self.approver().activate(dataset, 0, "test-operator", str(uuid4()))

        def fail(stage, db):
            if stage == "after_dataset_activation":
                raise PersistenceError("forced_failure")

        with self.assertRaises(PersistenceError):
            self.approver(fail).activate(dataset, 1, "test-operator", str(uuid4()))
        self.assertEqual([(1,)], self.query("SELECT row_version FROM lb.active_dataset"))
        self.assertEqual(dataset, self.reader().read("mega_sena")["dataset_id"])

    def test_15_concurrent_activation_has_only_one_winner(self):
        result = self.persist()
        dataset = self.approve("mega_sena", [result])

        def activate(_):
            try:
                return self.approver().activate(dataset, 0, "test-operator", str(uuid4()))[
                    "active_version"
                ]
            except PersistenceError as error:
                return error.code

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(activate, range(2)))
        self.assertCountEqual([1, "dataset_activation_conflict"], results)
        self.assertEqual(2, self.count("dataset_decision"))

    def test_16_policy_is_immutable_and_unknown_profiles_fail_closed(self):
        service = self.approver()
        policy = service.policy(
            "mega_sena", "samples_v1", [self.prepared().source_key], "test-operator"
        )
        self.assertEqual(
            policy,
            service.policy(
                "mega_sena", "samples_v1", [self.prepared().source_key], "test-operator"
            ),
        )
        with self.assertRaises(PersistenceError):
            service.policy("mega_sena", "samples_v1", ["caixa_mega_sena_json"], "test-operator")
        with self.assertRaises(PersistenceError):
            service.policy("mega_sena", "other_v1", ["caixa_mega_sena_current"], "test-operator")
        with self.assertRaises(psycopg.errors.CheckViolation):
            with psycopg.connect(**self.owner_args) as db:
                db.execute(
                    "UPDATE lb.dataset_policy SET source_keys=ARRAY['other'] WHERE id=%s", (policy,)
                )

    def test_17_operational_bootstrap_detects_drift_without_overwriting(self):
        with psycopg.connect(**self.owner_args, row_factory=dict_row) as db:
            db.execute("""UPDATE lb.component_definition SET max_value=59 WHERE id IN (
                SELECT c.id FROM lb.component_definition c JOIN lb.series_definition s ON s.id=c.series_definition_id
                JOIN lb.rule_version r ON r.id=s.rule_version_id JOIN lb.lottery l ON l.id=r.lottery_id
                WHERE l.slug='mega_sena')""")
            with self.assertRaises(PersistenceError) as error:
                bootstrap_catalog(db)
            self.assertEqual("catalog_drift", error.exception.code)
            db.rollback()

    def test_18_local_sample_uses_existing_readers_for_each_lottery(self):
        for slug, extension in (
            ("mega_sena", "xlsx"),
            ("lotofacil", "xlsx"),
            ("mais_milionaria", "xlsx"),
            ("powerball", "html"),
            ("mega_millions", "html"),
            ("euro_millions", "json"),
        ):
            prepared = prepare_sample(
                slug, ROOT / f"data/raw/{slug}/{slug}_resultados.{extension}", 1
            )
            self.assertEqual(slug, prepared.row.content["lottery"])
            result = self.persist(prepared)
            self.assertEqual("new", result["outcome"])

    def test_19_catalog_role_can_bootstrap_a_fresh_database(self):
        from sqlalchemy.engine import URL
        from test_integrity import migrate

        name = "lottobrain_stage6_catalog_" + uuid4().hex
        with psycopg.connect(os.environ["LOTTOBRAIN_TEST_ADMIN_DSN"], autocommit=True) as admin:
            admin.execute(
                sql.SQL("CREATE DATABASE {} OWNER lb_migrator").format(sql.Identifier(name))
            )
        url = URL.create(
            "postgresql+psycopg",
            username="lb_migrator",
            password=self.owner["password"],
            host=self.owner["host"],
            port=self.owner["port"],
            database=name,
        ).render_as_string(hide_password=False)
        migrate(url)
        with psycopg.connect(**dict(self.owner, user="lb_admin"), dbname=name) as admin:
            admin.execute((ROOT / "scripts/database/roles.sql").read_text(encoding="utf-8"))
        with psycopg.connect(
            **dict(self.owner, user="lb_stage6_catalog"), dbname=name, row_factory=dict_row
        ) as db:
            self.assertEqual({"lotteries": 6, "rules": 20}, bootstrap_catalog(db))
            self.assertEqual({"lotteries": 6, "rules": 20}, bootstrap_catalog(db))

    def test_20_generic_historical_support_preserves_legacy_json_enrichment(self):
        receipt = self.capture()
        legacy = self.process(receipt)
        before = self.query(
            "SELECT content_hash FROM lb.draw_revision WHERE id=%s", (legacy.revision_id,)
        )[0][0]
        historical = self.persist(self.prepared(index=2))
        self.assertEqual("unchanged", historical["outcome"])
        self.assertEqual(legacy.revision_id, historical["revision_id"])
        self.assertEqual(
            [(before,)],
            self.query(
                "SELECT content_hash FROM lb.draw_revision WHERE id=%s", (legacy.revision_id,)
            ),
        )

    def test_21_operator_cli_runs_with_separate_roles_and_sanitized_inspection(self):
        from sqlalchemy.engine import URL

        def command(user, args):
            dsn = URL.create(
                "postgresql+psycopg",
                username=user,
                password=self.owner["password"],
                host=self.owner["host"],
                port=self.owner["port"],
                database=self.database,
            )
            output = StringIO()
            with patch.dict(
                os.environ, {"LOTTOBRAIN_DATABASE_URL": dsn.render_as_string(hide_password=False)}
            ):
                with redirect_stdout(output):
                    self.assertEqual(0, persistence_main(args))
            self.assertNotIn(self.owner["password"], output.getvalue())
            return json.loads(output.getvalue())

        inspected = command("lb_migrator", ["inspect"])
        self.assertEqual("0033_01", inspected["migration"])
        self.assertTrue(inspected["catalog_schema"])
        self.assertFalse(inspected["superuser"])
        self.assertEqual({"lotteries": 6, "rules": 20}, command("lb_stage6_catalog", ["bootstrap"]))
        sample = command(
            "lb_test_ingestor",
            [
                "sample",
                "--lottery",
                "mega_sena",
                "--file",
                str(ROOT / "data/raw/mega_sena/mega_sena_resultados.xlsx"),
                "--ordinal",
                "1",
                "--object-root",
                self.temporary.name,
                "--command-key",
                "cli-sample-1",
            ],
        )
        policy = command(
            "lb_stage6_approver",
            [
                "policy",
                "--lottery",
                "mega_sena",
                "--version",
                "cli_v1",
                "--source",
                "caixa_mega_sena_xlsx",
                "--actor",
                "cli-operator",
            ],
        )
        dataset = command(
            "lb_stage6_approver",
            [
                "approve",
                "--policy",
                policy["policy_id"],
                "--revision",
                sample["revision_id"],
                "--actor",
                "cli-operator",
                "--command-key",
                "cli-approve-1",
            ],
        )
        command(
            "lb_stage6_approver",
            [
                "activate",
                "--dataset",
                dataset["dataset_id"],
                "--expected-version",
                "0",
                "--actor",
                "cli-operator",
                "--command-key",
                "cli-activate-1",
            ],
        )
        page = command("lb_stage6_reader", ["read", "--lottery", "mega_sena", "--limit", "1"])
        self.assertEqual(sample["revision_id"], page["items"][0]["revision_id"])

    def test_22_identical_manifest_reuses_dataset_under_new_command(self):
        result = self.persist()
        service = self.approver()
        policy = service.policy("mega_sena", "reuse_v1", [self.prepared().source_key], "operator")
        first = service.approve(policy, [result["revision_id"]], "operator", "approval-one")
        second = service.approve(policy, [result["revision_id"]], "operator", "approval-two")
        self.assertEqual(first, second)
        self.assertEqual(
            second, service.approve(policy, [result["revision_id"]], "operator", "approval-two")
        )
        self.assertEqual(1, self.count("approved_dataset"))
        self.assertEqual(1, self.count("dataset_member"))
        self.assertEqual(
            [("approve",), ("reuse",)],
            self.query("SELECT action FROM lb.dataset_decision ORDER BY decided_at"),
        )

    def test_23_sql_requires_audit_witness_for_activation(self):
        result = self.persist()
        dataset = self.approve("mega_sena", [result])
        with self.assertRaises(psycopg.errors.CheckViolation):
            with closing(psycopg.connect(**self.owner_args)) as db:
                db.execute(
                    """INSERT INTO lb.active_dataset(lottery_id,dataset_id,row_version)
                    SELECT lottery_id,id,1 FROM lb.approved_dataset WHERE id=%s""",
                    (dataset,),
                )
                db.commit()
        self.assertTrue(db.closed)
        self.assertEqual(0, self.count("active_dataset"))
        self.assertEqual(1, self.count("dataset_decision"))

    def test_24_concurrent_approvals_share_one_manifest(self):
        result = self.persist()
        policy = self.approver().policy(
            "mega_sena", "concurrent_v1", [self.prepared().source_key], "operator"
        )

        def approve(_):
            return self.approver().approve(
                policy, [result["revision_id"]], "operator", str(uuid4())
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            datasets = list(pool.map(approve, range(2)))
        self.assertEqual(datasets[0], datasets[1])
        self.assertEqual(1, self.count("approved_dataset"))
        self.assertEqual(2, self.count("dataset_decision"))

    def test_25_catalog_change_requires_a_new_policy(self):
        result = self.persist()
        service = self.approver()
        policy = service.policy("mega_sena", "frozen_v1", [self.prepared().source_key], "operator")
        with patch(
            "app.infrastructure.postgres.datasets.policy_catalog_hash", return_value="a" * 64
        ):
            with self.assertRaises(PersistenceError) as error:
                service.approve(policy, [result["revision_id"]], "operator", str(uuid4()))
        self.assertEqual("dataset_policy_outdated", error.exception.code)
        self.assertEqual(0, self.count("approved_dataset"))
        self.assertIsNotNone(
            service.approve(policy, [result["revision_id"]], "operator", str(uuid4()))
        )
