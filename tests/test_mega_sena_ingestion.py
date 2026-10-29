import json
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from app.domain import RawProvenance, ValueStatus
from app.ingestion.mega_sena import normalize_row


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "mega_sena_rows.json"


def fixture_rows():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def provenance():
    return RawProvenance(
        source_key="caixa_mega_sena_xlsx",
        raw_sha256="0e1936e3ac94a35a89c13ef31d705d3fb363239779ad6224b5e41171a3238686",
        captured_at=datetime(2025, 12, 20, 12, tzinfo=timezone.utc),
        adapter_version="spec-0004",
    )


class MegaSenaNormalizerTests(unittest.TestCase):
    def test_three_real_rows_normalize_without_issues(self):
        results = [normalize_row(row, provenance()) for row in fixture_rows()]
        self.assertEqual(3, len(results))
        self.assertTrue(all(result.is_valid for result in results))
        self.assertEqual(
            [
                "mega_sena:official_draw_number:1",
                "mega_sena:official_draw_number:2",
                "mega_sena:official_draw_number:2954",
            ],
            [result.canonical_key for result in results],
        )

    def test_zero_and_missing_are_not_confused(self):
        result = normalize_row(fixture_rows()[0], provenance())
        candidate = result.candidate
        self.assertIsNotNone(candidate)
        sena = next(tier for tier in candidate.prize_tiers if tier.tier_key == "sena")
        self.assertEqual(0, sena.winners)
        self.assertEqual(Decimal("0.00"), sena.prize_per_winner.amount)
        self.assertEqual(ValueStatus.KNOWN, sena.prize_per_winner.status)
        self.assertEqual((), candidate.metadata)

    def test_normalization_is_idempotent_for_the_same_row(self):
        row = fixture_rows()[1]
        first = normalize_row(row, provenance())
        second = normalize_row(row, provenance())
        self.assertEqual(first, second)
        self.assertEqual(first.canonical_key, second.canonical_key)

    def test_invalid_ball_is_preserved_as_an_issue(self):
        row = dict(fixture_rows()[0])
        row["Bola6"] = 61
        result = normalize_row(row, provenance())
        self.assertIsNotNone(result.candidate)
        self.assertIn("component.out_of_range", {issue.code for issue in result.issues})

    def test_missing_identity_prevents_candidate(self):
        row = dict(fixture_rows()[0])
        row["Concurso"] = None
        result = normalize_row(row, provenance())
        self.assertIsNone(result.candidate)
        self.assertIsNone(result.canonical_key)
        self.assertIn("source.missing_value", {issue.code for issue in result.issues})

    def test_invalid_money_becomes_unknown_and_reports_issue(self):
        row = dict(fixture_rows()[0])
        row["Arrecadação Total"] = "valor indisponível"
        result = normalize_row(row, provenance())
        sales = next(item for item in result.candidate.monetary_amounts if item.kind == "sales_total")
        self.assertEqual(ValueStatus.UNKNOWN, sales.status)
        self.assertEqual("valor indisponível", sales.source_text)
        self.assertIn("source.invalid_money", {issue.code for issue in result.issues})


if __name__ == "__main__":
    unittest.main()

