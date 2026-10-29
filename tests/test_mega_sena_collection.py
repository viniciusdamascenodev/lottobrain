import copy
import hashlib
import io
import json
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from app.application.collect_mega_sena import (
    CollectMegaSena, CollectionError, FetchResponse, MAX_RESPONSE_BYTES,
)
from app.domain import RawProvenance
from app.infrastructure.caixa_http import CaixaMegaSenaHttp, ENDPOINT
from app.infrastructure.local_collection import LocalCollectionWorkspace
from app.ingestion.mega_sena import normalize_row
from app.ingestion.mega_sena_api import ADAPTER_VERSION, SOURCE_KEY, normalize_response

FIXTURE = Path(__file__).parent / "fixtures" / "mega_sena_api_2954.json"
CAPTURED = datetime(2026, 10, 21, 1, 0, 2, tzinfo=timezone.utc)


def response(payload=None, **changes):
    body = FIXTURE.read_bytes() if payload is None else json.dumps(payload).encode()
    base = FetchResponse(body, f"{ENDPOINT}/2954", 200, "application/json", CAPTURED)
    return replace(base, **changes)


def normalized(payload=None, expected=2954):
    fetched = response(payload)
    provenance = RawProvenance(SOURCE_KEY, hashlib.sha256(fetched.body).hexdigest(), CAPTURED, ADAPTER_VERSION)
    return normalize_response(fetched.body, provenance, expected_contest=expected)


class JsonContractTests(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads(FIXTURE.read_bytes())

    def test_real_official_sample_matches_historical_snapshot(self):
        actual = normalized()
        self.assertTrue(actual.is_valid, actual.issues)
        rows = json.loads((FIXTURE.parent / "mega_sena_rows.json").read_bytes())
        historic = normalize_row(rows[-1], actual.candidate.provenance).candidate
        self.assertEqual(historic.series, actual.candidate.series)
        self.assertEqual(historic.draw_date, actual.candidate.draw_date)
        self.assertEqual(historic.official_draw_number, actual.candidate.official_draw_number)
        def prizes(candidate):
            return {tier.tier_key: (tier.winners, tier.prize_per_winner.amount, tier.prize_per_winner.currency)
                    for tier in candidate.prize_tiers}
        self.assertEqual(prizes(historic), prizes(actual.candidate))

    def test_wrong_contest_date_and_game_are_quarantined(self):
        for field, value, code in (
            ("numero", True, "source.invalid_identity"),
            ("numero", 2955, "source.identity_mismatch"),
            ("dataApuracao", "31/02/2025", "source.invalid_date"),
            ("dataApuracao", "22/10/2026", "source.future_result"),
            ("tipoJogo", "QUINA", "source.wrong_game"),
            ("tipoPublicacao", 1, "source.unverified_publication"),
            ("premiacaoContingencia", {}, "source.unverified_contingency"),
        ):
            with self.subTest(field=field, value=value):
                payload = copy.deepcopy(self.payload)
                payload[field] = value
                result = normalized(payload)
                self.assertFalse(result.is_valid)
                self.assertIn(code, {issue.code for issue in result.issues})

    def test_schema_changes_and_invalid_balls_fail_closed(self):
        for field, value in (
            ("newField", 1), ("listaDezenas", ["01"]),
            ("listaDezenas", ["01", "09", "37", "39", "42", "61"]),
            ("listaDezenas", ["01", "09", "37", "39", "42", "42"]),
            ("dezenasSorteadasOrdemSorteio", ["01", "09", "37", "39", "42", "43"]),
            ("listaDezenasSegundoSorteio", ["01"]),
        ):
            payload = copy.deepcopy(self.payload)
            payload[field] = value
            self.assertFalse(normalized(payload).is_valid, field)

    def test_missing_duplicate_and_negative_tiers_fail_closed(self):
        for modify in (
            lambda p: p.update(listaRateioPremio=[]),
            lambda p: p["listaRateioPremio"].append(p["listaRateioPremio"][0]),
            lambda p: p["listaRateioPremio"][0].update(numeroDeGanhadores=-1),
            lambda p: p["listaRateioPremio"][0].update(valorPremio=-1),
            lambda p: p["listaRateioPremio"][0].update(valorPremio=None),
            lambda p: p.update(valorArrecadado=True),
            lambda p: p.update(valorArrecadado=10 ** 30),
        ):
            payload = copy.deepcopy(self.payload)
            modify(payload)
            self.assertFalse(normalized(payload).is_valid)

    def test_invalid_json_and_duplicate_keys_return_diagnostics(self):
        provenance = RawProvenance(SOURCE_KEY, "0" * 64, CAPTURED, ADAPTER_VERSION)
        for body in (b"<html>blocked</html>", b'{"numero":1,"numero":2}', b'{"x":NaN}', b'[]'):
            result = normalize_response(body, provenance)
            self.assertFalse(result.is_valid)
            self.assertTrue(result.issues)


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = LocalCollectionWorkspace(Path(self.temp.name))
        self.source = Mock()
        self.source.fetch.return_value = response()
        self.service = CollectMegaSena(self.source, self.workspace, self.workspace)

    def run_collection(self):
        with self.workspace.exclusive():
            return self.service.execute(2954)

    def test_repeat_capture_has_one_raw_one_revision_and_two_receipts(self):
        first = self.run_collection()
        self.source.fetch.return_value = replace(response(), captured_at=CAPTURED.replace(hour=2))
        second = self.run_collection()
        self.assertEqual("new", first["outcome"])
        self.assertEqual("unchanged", second["outcome"])
        self.assertEqual(1, len(list((self.workspace.root / "artifacts").glob("*.json"))))
        self.assertEqual(2, len(list((self.workspace.root / "receipts").glob("*.json"))))
        self.assertEqual(1, len(self.history()))

    def history(self):
        return json.loads((self.workspace.root / "revisions" / "2954.json").read_bytes())["revisions"]

    def test_correction_is_candidate_and_replay_old_receipt_does_not_roll_back(self):
        first = self.run_collection()
        payload = json.loads(FIXTURE.read_bytes())
        payload["listaRateioPremio"][1]["numeroDeGanhadores"] = 39
        self.source.fetch.return_value = response(payload)
        correction = self.run_collection()
        self.assertEqual("correction_candidate", correction["outcome"])
        self.assertEqual(2, len(self.history()))
        self.assertTrue(all(item["state"] == "candidate" for item in self.history()))
        with self.workspace.exclusive():
            replayed = self.service.replay(self.workspace.load(first["receipt_id"]), expected_contest=2954)
        self.assertEqual("replayed", replayed["outcome"])
        self.assertEqual(2, len(self.history()))

    def test_navigation_flags_and_json_format_are_not_content_changes(self):
        self.run_collection()
        payload = json.loads(FIXTURE.read_bytes())
        payload.update(ultimoConcurso=False, dataProximoConcurso="02/01/2026")
        self.source.fetch.return_value = response(payload)
        self.assertEqual("unchanged", self.run_collection()["outcome"])

    def test_http_failure_and_invalid_payload_are_archived_before_quarantine(self):
        for fetched in (
            response(status=429), response(content_type="text/html"),
            response(body=b"{broken"),
        ):
            self.source.fetch.return_value = fetched
            result = self.run_collection()
            self.assertEqual("quarantined", result["outcome"])
            archived = self.workspace.load(result["receipt_id"])
            self.assertEqual(fetched.body, archived.response.body)
        self.assertFalse((self.workspace.root / "revisions").exists())

    def test_truncated_and_tampered_artifact_cannot_be_replayed(self):
        result = self.run_collection()
        artifact = self.workspace.root / "artifacts" / f"{result['raw_sha256']}.json"
        with artifact.open("wb") as handle:
            handle.write(b"bad")
        with self.assertRaisesRegex(CollectionError, "artifact_size_mismatch"):
            self.workspace.load(result["receipt_id"])

    def test_atomic_failure_preserves_previous_revision_and_allows_retry(self):
        self.run_collection()
        before = self.history()
        payload = json.loads(FIXTURE.read_bytes())
        payload["listaRateioPremio"][1]["numeroDeGanhadores"] = 39
        self.source.fetch.return_value = response(payload)
        with patch("app.infrastructure.local_collection.os.replace", side_effect=OSError("interrupted")):
            with self.assertRaises(OSError):
                self.run_collection()
        self.assertEqual(before, self.history())
        self.assertEqual("correction_candidate", self.run_collection()["outcome"])

    def test_concurrent_cli_execution_and_path_traversal_are_rejected(self):
        with self.workspace.exclusive():
            with self.assertRaisesRegex(CollectionError, "workspace_locked"):
                with self.workspace.exclusive():
                    self.fail("lock should prevent another run")
        with self.assertRaisesRegex(CollectionError, "invalid_receipt_reference"):
            self.workspace.load("../secret")


class HttpTransportTests(unittest.TestCase):
    def test_fixed_endpoint_timeout_and_response_limit(self):
        source = CaixaMegaSenaHttp(timeout=2)
        received = io.BytesIO(FIXTURE.read_bytes())
        received.headers = {"Content-Type": "application/json"}
        received.code = 200
        received.geturl = lambda: f"{ENDPOINT}/2954"
        source._opener = Mock()
        source._opener.open.return_value = received
        result = source.fetch(2954)
        self.assertEqual(FIXTURE.read_bytes(), result.body)
        request = source._opener.open.call_args.args[0]
        self.assertEqual(f"{ENDPOINT}/2954", request.full_url)
        self.assertEqual(2, source._opener.open.call_args.kwargs["timeout"])
        received = io.BytesIO(b"x" * (MAX_RESPONSE_BYTES + 1))
        received.headers = {}
        received.geturl = lambda: ENDPOINT
        source._opener.open.return_value = received
        with self.assertRaisesRegex(CollectionError, "response_too_large"):
            source.fetch(None)
        self.assertTrue(received.closed)

    def test_transport_failure_and_redirect_fail_safely(self):
        import urllib.error
        source = CaixaMegaSenaHttp()
        source._opener = Mock()
        source._opener.open.side_effect = urllib.error.URLError("unavailable")
        with self.assertRaisesRegex(CollectionError, "http.transport_failure"):
            source.fetch(None)
        from app.infrastructure.caixa_http import _NoRedirect
        self.assertIsNone(_NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.test"))

    def test_declared_oversize_and_truncation_are_rejected(self):
        source = CaixaMegaSenaHttp()
        source._opener = Mock()
        for size, expected in ((MAX_RESPONSE_BYTES + 1, "response_too_large"), (20, "truncated_response")):
            received = io.BytesIO(b"x")
            received.headers = {"Content-Length": str(size)}
            received.geturl = lambda: ENDPOINT
            source._opener.open.return_value = received
            with self.assertRaisesRegex(CollectionError, expected):
                source.fetch(None)
            self.assertTrue(received.closed)


if __name__ == "__main__":
    unittest.main()
