"""Dobles de fonte usam mutações da amostra real apenas no diretório temporário."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from app.application.collect_mega_sena import CollectMegaSena, CollectionError, FetchResponse
from app.application.sync_mega_sena import SyncAnchor, SyncMegaSena, SyncPolicy
from app.infrastructure.caixa_http import ENDPOINT
from app.infrastructure.local_collection import LocalCollectionWorkspace
from app.infrastructure.mega_sena_baseline import verified_history_anchor

PROJECT = Path(__file__).resolve().parents[1]
FIXTURE = PROJECT / "tests/fixtures/mega_sena_api_2954.json"
NOW = datetime(2026, 10, 21, 1, 30, tzinfo=timezone.utc)
ANCHOR = SyncAnchor(2954, "0" * 64)


class ControlledSource:
    """Números de concursos alterados são cenários de teste, não novos fatos reais."""

    def __init__(self, latest=2960):
        self.latest = latest
        self.calls = []
        self.failures = {}
        self.winners = {}

    def fetch(self, contest):
        self.calls.append(contest)
        failure = self.failures.get(contest)
        if isinstance(failure, Exception):
            raise failure
        selected = self.latest if contest is None else contest
        payload = json.loads(FIXTURE.read_bytes())
        payload["numero"] = selected
        payload["numeroConcursoAnterior"] = selected - 1
        payload["numeroConcursoProximo"] = selected + 1
        if selected in self.winners:
            payload["listaRateioPremio"][1]["numeroDeGanhadores"] = self.winners[selected]
        suffix = "" if contest is None else f"/{contest}"
        return FetchResponse(
            json.dumps(payload).encode(), ENDPOINT + suffix,
            failure if isinstance(failure, int) else 200, "application/json", NOW,
        )


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = LocalCollectionWorkspace(Path(self.temp.name))
        self.source = ControlledSource()
        self.wait = Mock()
        self.collector = CollectMegaSena(self.source, self.workspace, self.workspace)
        self.service = SyncMegaSena(self.collector, self.workspace, wait=self.wait, clock=lambda: NOW)

    def run_sync(self, max_requests=4, window=0, anchor=None):
        with self.workspace.exclusive():
            return self.service.execute(SyncPolicy(max_requests, window), anchor=anchor)

    def test_initialization_is_explicit_and_baseline_is_verified(self):
        with self.assertRaisesRegex(CollectionError, "sync_not_initialized"):
            self.run_sync()
        self.assertEqual([], self.source.calls)
        official_anchor = verified_history_anchor(PROJECT / "data/raw/mega_sena/mega_sena_resultados.xlsx")
        self.assertEqual(2954, official_anchor.last_contest)
        with self.assertRaisesRegex(CollectionError, "historical_baseline_hash_mismatch"):
            verified_history_anchor(FIXTURE)

    def test_discovery_does_not_jump_gaps_and_budget_includes_it(self):
        report = self.run_sync(anchor=ANCHOR)
        self.assertEqual([None, 2955, 2956, 2957], self.source.calls)
        self.assertEqual(4, report["requests"])
        self.assertEqual(2957, report["cursor_after"])
        self.assertEqual(3, report["remaining"])
        self.assertTrue((self.workspace.root / "revisions/2960.json").exists())

    def test_discovery_is_reused_when_contiguous_cursor_reaches_latest(self):
        self.source.latest = 2958
        report = self.run_sync(anchor=ANCHOR)
        self.assertEqual([None, 2955, 2956, 2957], self.source.calls)
        self.assertEqual(2958, report["cursor_after"])
        self.assertEqual("caught_up", report["stop_reason"])
        self.assertTrue(report["operations"][-1]["reused_discovery"])

    def test_404_stops_cursor_and_following_run_resumes_missing_contest(self):
        self.source.failures[2956] = 404
        failed = self.run_sync(anchor=ANCHOR)
        self.assertEqual("collection_stopped", failed["stop_reason"])
        self.assertEqual(2955, failed["cursor_after"])
        self.assertEqual([None, 2955, 2956], self.source.calls)
        self.source.failures.clear()
        self.source.calls.clear()
        resumed = self.run_sync(max_requests=3)
        self.assertEqual([None, 2956, 2957], self.source.calls)
        self.assertEqual(2957, resumed["cursor_after"])

    def test_failed_checkpoint_is_retried_idempotently(self):
        original = self.workspace.save_sync_state

        def interrupted(state):
            if state.cursor == 2955:
                raise OSError("simulated crash")
            return original(state)

        with patch.object(self.workspace, "save_sync_state", side_effect=interrupted):
            with self.assertRaises(OSError):
                self.run_sync(anchor=ANCHOR)
        self.assertEqual(2954, self.workspace.load_sync_state().cursor)
        self.assertTrue((self.workspace.root / "revisions/2955.json").exists())
        self.source.calls.clear()
        report = self.run_sync(max_requests=2)
        self.assertEqual([None, 2955], self.source.calls)
        self.assertEqual(2955, report["cursor_after"])
        history = json.loads((self.workspace.root / "revisions/2955.json").read_bytes())
        self.assertEqual(1, len(history["revisions"]))

    def test_review_detects_correction_without_moving_forward_cursor_back(self):
        self.source.latest = 2957
        self.run_sync(anchor=ANCHOR)
        self.source.winners[2955] = 39
        self.source.calls.clear()
        report = self.run_sync(max_requests=2, window=3)
        self.assertEqual([None, 2955], self.source.calls)
        self.assertEqual(2957, report["cursor_after"])
        review = next(operation for operation in report["operations"] if operation["phase"] == "review")
        self.assertEqual("correction_candidate", review["outcome"])
        self.source.calls.clear()
        self.run_sync(max_requests=2, window=3)
        self.assertEqual([None, 2956], self.source.calls)

    def test_backlog_reserves_a_request_for_review(self):
        self.source.latest = 2956
        self.run_sync(anchor=ANCHOR)
        self.source.latest = 2960
        self.source.calls.clear()
        report = self.run_sync(max_requests=3, window=2)
        self.assertEqual([None, 2957, 2955], self.source.calls)
        self.assertEqual(2957, report["cursor_after"])
        self.assertEqual("budget_exhausted", report["stop_reason"])

    def test_rate_limit_cooldown_survives_next_invocation(self):
        self.source.failures[2955] = 429
        report = self.run_sync(anchor=ANCHOR)
        self.assertEqual(2954, report["cursor_after"])
        self.assertIsNotNone(report["cooldown_until"])
        self.source.calls.clear()
        self.assertEqual("cooldown", self.run_sync()["stop_reason"])
        self.assertEqual([], self.source.calls)
        self.service = SyncMegaSena(
            self.collector, self.workspace, wait=self.wait, clock=lambda: NOW + timedelta(minutes=16),
        )
        self.source.failures.clear()
        self.assertGreater(self.run_sync(max_requests=2)["cursor_after"], 2954)

    def test_quarantine_on_discovery_has_no_forward_attempt(self):
        self.source.failures[None] = 503
        report = self.run_sync(anchor=ANCHOR)
        self.assertEqual([None], self.source.calls)
        self.assertEqual(2954, report["cursor_after"])

    def test_transport_failure_stops_and_pacing_runs_before_every_request(self):
        self.source.failures[2956] = CollectionError("http.transport_failure")
        report = self.run_sync(anchor=ANCHOR)
        self.assertEqual(2955, report["cursor_after"])
        self.assertEqual(3, self.wait.call_count)
        self.assertTrue(all(call.args == (2,) for call in self.wait.call_args_list))

    def test_source_behind_cursor_never_regresses_checkpoint(self):
        self.source.latest = 2955
        self.run_sync(anchor=ANCHOR)
        self.source.latest = 2954
        report = self.run_sync()
        self.assertEqual("source_behind_cursor", report["stop_reason"])
        self.assertEqual(2955, report["cursor_after"])

    def test_single_request_can_only_discover_or_advance_to_adjacent_latest(self):
        first = self.run_sync(max_requests=1, anchor=ANCHOR)
        self.assertEqual(2954, first["cursor_after"])
        self.source.latest = 2955
        second = self.run_sync(max_requests=1)
        self.assertEqual(2955, second["cursor_after"])
        self.assertEqual(1, second["requests"])

    def test_corrupted_checkpoint_and_reset_are_rejected_before_network(self):
        self.run_sync(max_requests=1, anchor=ANCHOR)
        self.source.calls.clear()
        with self.assertRaisesRegex(CollectionError, "sync_baseline_mismatch"):
            self.run_sync(anchor=SyncAnchor(2953, "1" * 64))
        path = self.workspace.root / "sync-state.json"
        with path.open("w") as handle:
            handle.write('{"schema_version":99}')
        with self.assertRaisesRegex(CollectionError, "invalid_sync_checkpoint"):
            self.run_sync()
        self.assertEqual([], self.source.calls)

    def test_atomic_checkpoint_failure_keeps_previous_json(self):
        self.run_sync(max_requests=1, anchor=ANCHOR)
        before = (self.workspace.root / "sync-state.json").read_bytes()
        original = __import__("os").replace

        def interrupted(src, destination):
            if Path(destination).name == "sync-state.json":
                raise OSError("simulated checkpoint crash")
            return original(src, destination)

        with patch("app.infrastructure.local_collection.os.replace", side_effect=interrupted):
            with self.assertRaises(OSError):
                self.run_sync(max_requests=2)
        self.assertEqual(before, (self.workspace.root / "sync-state.json").read_bytes())

    def test_policy_rejects_invalid_budgets_before_execution(self):
        for kwargs in (
            {"max_requests": 0}, {"max_requests": 11}, {"max_requests": True},
            {"review_window": -1}, {"review_window": 21}, {"interval_seconds": 0},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                SyncPolicy(**kwargs)

    def test_review_failure_preserves_review_pointer_and_forward_progress(self):
        self.source.latest = 2956
        self.run_sync(anchor=ANCHOR)
        before_pointer = self.workspace.load_sync_state().review_next
        self.source.failures[2955] = 503
        report = self.run_sync(max_requests=3, window=2)
        self.assertEqual("collection_stopped", report["stop_reason"])
        self.assertEqual(2956, report["cursor_after"])
        self.assertEqual(before_pointer, report["review_next"])
        self.source.failures.clear()
        self.source.calls.clear()
        self.run_sync(max_requests=2, window=2)
        self.assertEqual([None, 2955], self.source.calls)

    def test_checkpoint_rejects_lost_cursor_evidence_before_querying(self):
        self.source.latest = 2955
        self.run_sync(anchor=ANCHOR)
        self.source.calls.clear()
        (self.workspace.root / "revisions/2955.json").unlink()
        with self.assertRaisesRegex(CollectionError, "sync_revision_missing"):
            self.run_sync()
        self.assertEqual([], self.source.calls)


if __name__ == "__main__":
    unittest.main()
