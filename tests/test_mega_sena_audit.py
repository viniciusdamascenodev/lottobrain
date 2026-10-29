"""Falhas simuladas só afetam workspaces temporários; nenhuma consulta de rede."""
import hashlib
import io
import json
import tempfile
import unittest
from dataclasses import replace
from contextlib import redirect_stderr
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

from app.application.audit_mega_sena import AuditFile, AuditMegaSena, audit_snapshot, finalize_report, missing_ranges
from app.application.collect_mega_sena import CollectMegaSena, FetchResponse, canonical_json, content_hash
from app.application.sync_mega_sena import SyncMegaSena, SyncPolicy
from app.infrastructure.local_audit import LocalAuditReader
from app.infrastructure.local_collection import LocalCollectionWorkspace
from app.infrastructure.mega_sena_baseline import verified_history_anchor
from app.interfaces.audit_mega_sena import main

PROJECT = Path(__file__).resolve().parents[1]
BASELINE = PROJECT / "data/raw/mega_sena/mega_sena_resultados.xlsx"
FIXTURE = PROJECT / "tests/fixtures/mega_sena_api_2954.json"
NOW = datetime(2026, 10, 21, 1, 30, tzinfo=timezone.utc)
API = "https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena"


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "workspace"
        workspace = LocalCollectionWorkspace(self.root)
        source = Mock()

        def fetched(contest):
            # Identificadores alterados são apenas cenários de teste.
            selected = 2957 if contest is None else contest
            payload = json.loads(FIXTURE.read_bytes())
            payload["numero"] = selected
            return FetchResponse(
                json.dumps(payload).encode(), API if contest is None else f"{API}/{contest}",
                200, "application/json", NOW,
            )

        source.fetch.side_effect = fetched
        with workspace.exclusive():
            collector = CollectMegaSena(source, workspace, workspace)
            SyncMegaSena(collector, workspace, wait=lambda seconds: None, clock=lambda: NOW).execute(
                SyncPolicy(4, 0), anchor=verified_history_anchor(BASELINE),
            )
        self.reader = LocalAuditReader(self.root, BASELINE)

    def audit(self):
        return AuditMegaSena(self.reader).execute()

    def codes(self, report):
        return {item["code"] for item in report["issues"]}

    def rewrite(self, path, transform):
        target = self.root / path
        payload = json.loads(target.read_bytes())
        transform(payload)
        with target.open("w", encoding="utf-8") as handle:
            handle.write(canonical_json(payload))

    def receipt(self, contest):
        payload = json.loads((self.root / f"revisions/{contest}.json").read_bytes())
        return payload["revisions"][0]["receipt_id"]

    def test_healthy_workspace_is_deterministic_read_only_and_portable(self):
        before = self.reader.capture().manifest()
        report = self.audit()
        self.assertEqual("healthy", report["status"])
        self.assertEqual(2957, report["coverage"]["cursor_verified_through"])
        self.assertEqual([], report["issues"])
        self.assertEqual(before, self.reader.capture().manifest())
        self.assertEqual(canonical_json(report), canonical_json(self.audit()))
        self.assertNotIn(str(self.root), canonical_json(report))
        self.assertFalse((self.root / ".collection.lock").exists())

    def test_missing_middle_revision_invalidates_continuity(self):
        (self.root / "revisions/2956.json").unlink()
        report = self.audit()
        self.assertEqual(2957, report["coverage"]["cursor_claimed"])
        self.assertEqual(2955, report["coverage"]["cursor_verified_through"])
        self.assertIn("cursor.coverage_gap", self.codes(report))
        self.assertEqual([{"first": 2956, "last": 2956, "count": 1}], report["coverage"]["unverified_within_cursor"])
        self.assertEqual("failed", report["status"])

    def test_raw_tampering_breaks_receipt_and_revision_chain(self):
        receipt = self.receipt(2956)
        metadata = json.loads((self.root / f"receipts/{receipt}.json").read_bytes())
        artifact = self.root / f"artifacts/{metadata['sha256']}.json"
        with artifact.open("wb") as handle:
            handle.write(b"tampered")
        report = self.audit()
        self.assertTrue({"artifact.hash_mismatch", "receipt.artifact_unavailable", "revision.receipt_unavailable"} <= self.codes(report))

    def test_recomputed_revision_hash_still_requires_raw_reproduction(self):
        def forge(payload):
            record = payload["revisions"][0]
            record["payload"]["metadata"].append(["forged", "value"])
            record["content_sha256"] = content_hash(record["payload"])
        self.rewrite("revisions/2955.json", forge)
        self.assertIn("revision.not_reproducible", self.codes(self.audit()))

    def test_missing_receipt_and_missing_outcome_are_distinct(self):
        first = self.receipt(2955)
        second = self.receipt(2956)
        (self.root / f"receipts/{first}.json").unlink()
        for path in (self.root / "outcomes").glob(f"{second}-*.json"):
            path.unlink()
        codes = self.codes(self.audit())
        self.assertTrue({"revision.receipt_unavailable", "receipt.outcome_missing", "revision.outcome_missing"} <= codes)

    def test_orphan_raw_is_reported_without_deleting_it(self):
        body = b"orphaned original bytes"
        path = self.root / f"artifacts/{hashlib.sha256(body).hexdigest()}.json"
        with path.open("wb") as handle:
            handle.write(body)
        report = self.audit()
        self.assertIn("artifact.orphan", self.codes(report))
        self.assertEqual("attention", report["status"])
        self.assertEqual(body, path.read_bytes())
        self.assertTrue(all(action["automatic"] is False for action in report["recovery_plan"]))

    def test_unfinished_receipt_proposes_replay_without_advancing_cursor(self):
        workspace = LocalCollectionWorkspace(self.root)
        with workspace.exclusive():
            archived = workspace.save(FetchResponse(FIXTURE.read_bytes(), API + "/2954", 200, "application/json", NOW))
        report = self.audit()
        self.assertIn("receipt.outcome_missing", self.codes(report))
        self.assertTrue(any(action["action"] == "replay_receipt" for action in report["recovery_plan"]))
        self.assertTrue((self.root / f"receipts/{archived.receipt_id}.json").exists())
        self.assertEqual(2957, report["coverage"]["cursor_claimed"])

    def test_invalid_json_duplicate_keys_and_wrong_shapes_accumulate(self):
        paths = sorted((self.root / "receipts").glob("*.json"))
        for path, body in zip(paths, (b"{broken", b'{"x":1,"x":2}', b'[]')):
            with path.open("wb") as handle:
                handle.write(body)
        report = self.audit()
        self.assertEqual(3, sum(item["code"] == "file.invalid_json" for item in report["issues"]))
        self.assertIn("cursor.coverage_gap", self.codes(report))

    def test_malformed_values_do_not_abort_other_checks(self):
        receipt = self.receipt(2955)
        self.rewrite(f"receipts/{receipt}.json", lambda payload: payload.update(sha256=[]))
        self.rewrite("revisions/2956.json", lambda payload: payload.update(revisions=[[]]))
        self.rewrite("sync-state.json", lambda payload: payload.update(anchor=[]))
        codes = self.codes(self.audit())
        self.assertTrue({"receipt.invalid_metadata", "revision.invalid_structure", "cursor.invalid_checkpoint"} <= codes)

    def test_baseline_mismatch_cannot_certify_cursor(self):
        snapshot = self.reader.capture()
        changed = replace(snapshot, baseline=replace(snapshot.baseline, observed_sha256="f" * 64))
        reader = Mock()
        reader.capture.return_value = changed
        report = AuditMegaSena(reader).execute()
        self.assertIn("baseline.hash_mismatch", self.codes(report))
        self.assertIsNone(report["coverage"]["cursor_verified_through"])

    def test_snapshot_change_invalidates_otherwise_healthy_report(self):
        before = self.reader.capture()
        after = replace(before, files=before.files[:-1])
        reader = Mock()
        reader.capture.side_effect = [before, after]
        report = AuditMegaSena(reader).execute()
        self.assertIn("workspace.changed_during_audit", self.codes(report))
        self.assertEqual("failed", report["status"])

    def test_lock_pending_file_and_unsafe_link_have_explicit_diagnostics(self):
        snapshot = self.reader.capture()
        snapshot = replace(snapshot, files=(*snapshot.files,
            AuditFile(".collection.lock", b"123", 3),
            AuditFile("revisions/.pending-test", b"partial", 7),
            AuditFile("artifacts/link.json", None, None, "unsafe_link"),
        ))
        report = finalize_report(audit_snapshot(snapshot))
        self.assertTrue({"workspace.lock_present", "file.pending_write", "file.unsafe_link"} <= self.codes(report))

    def test_wrong_sequence_and_false_publication_are_rejected(self):
        self.rewrite("revisions/2955.json", lambda p: p["revisions"][0].update(revision=2, state="published"))
        self.assertIn("revision.invalid_sequence_or_state", self.codes(self.audit()))

    def test_outcome_revision_reference_is_checked(self):
        receipt = self.receipt(2956)
        path = next((self.root / "outcomes").glob(f"{receipt}-*.json"))
        self.rewrite(path.relative_to(self.root), lambda p: p.update(revision=88))
        self.assertIn("outcome.revision_mismatch", self.codes(self.audit()))

    def test_run_request_count_and_reference_are_checked(self):
        path = next((self.root / "sync-runs").glob("*.json"))
        self.rewrite(path.relative_to(self.root), lambda p: p.update(requests=10))
        self.assertIn("run.request_count_mismatch", self.codes(self.audit()))

    def test_missing_workspace_is_diagnosed_without_creating_it(self):
        path = Path(self.temp.name) / "does-not-exist"
        report = AuditMegaSena(LocalAuditReader(path, BASELINE)).execute()
        self.assertIn("workspace.missing", self.codes(report))
        self.assertFalse(path.exists())

    def test_cli_refuses_to_write_inside_workspace_or_replace_report(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            main(["--workspace", str(self.root), "--output", str(self.root / "report.json")])
        output = Path(self.temp.name) / "existing.json"
        with output.open("w") as handle:
            handle.write("preserved")
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            main(["--workspace", str(self.root), "--output", str(output)])
        self.assertEqual("preserved", output.read_text())

    def test_huge_gap_is_compact(self):
        self.assertEqual(
            [{"first": 2, "last": 10**15 - 1, "count": 10**15 - 2}],
            missing_ranges(1, 10**15, {1, 10**15}),
        )

    def test_false_run_latest_and_remaining_are_detected(self):
        path = next((self.root / "sync-runs").glob("*.json"))
        self.rewrite(path.relative_to(self.root), lambda p: p.update(latest_observed=9999, remaining=0))
        codes = self.codes(self.audit())
        self.assertTrue({"run.latest_mismatch", "run.remaining_mismatch", "run.false_caught_up"} <= codes)

    def test_quarantine_remains_a_pending_action_without_candidate_publication(self):
        workspace = LocalCollectionWorkspace(self.root)
        source = Mock()
        source.fetch.return_value = FetchResponse(b"not found", API + "/2958", 404, "text/plain", NOW)
        with workspace.exclusive():
            CollectMegaSena(source, workspace, workspace).execute(2958)
        report = self.audit()
        self.assertIn("capture.quarantined", self.codes(report))
        self.assertEqual("attention", report["status"])
        self.assertNotIn(2958, report["coverage"]["verified_candidate_contests"])


if __name__ == "__main__":
    unittest.main()
