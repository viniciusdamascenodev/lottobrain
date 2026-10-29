import json
import unittest
from dataclasses import replace
from datetime import date, datetime, timezone
from pathlib import Path

from app.domain import RawProvenance
from app.ingestion.euro_millions import EURO_MILLIONS, normalize_row, read_json_rows
from app.ingestion.euro_millions_history import HistoryBaseline, audit_history, build_history_report
from app.ingestion.mega_sena_history import report_json


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/raw/euro_millions/euro_millions_resultados.json"
REPORT = ROOT / "docs/data/euro-millions-normalizacao-historica.json"
SHA = HistoryBaseline().source_sha256


class EuroMillionsHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = read_json_rows(SOURCE)
        cls.by_date = {}
        for row in cls.rows:
            parsed = datetime.strptime(row.date_value, "%a, %d %b %Y %H:%M:%S GMT")
            cls.by_date[parsed.date().isoformat()] = row
        cls.provenance = RawProvenance(
            "pedromealha_euromillions_api_json", SHA,
            datetime(2026, 10, 14, tzinfo=timezone.utc), "spec-0016",
        )

    def normalize_date(self, value):
        return normalize_row(self.by_date[value], self.provenance)

    def test_three_rule_boundaries(self):
        expected = {
            "2004-02-13": "em_2004_50x9", "2011-05-06": "em_2004_50x9",
            "2011-05-10": "em_2011_50x11", "2016-09-23": "em_2011_50x11",
            "2016-09-27": "em_2016_50x12", "2025-12-26": "em_2016_50x12",
        }
        for draw_date, version in expected.items():
            result = self.normalize_date(draw_date)
            self.assertTrue(result.is_valid, (draw_date, result.issues))
            self.assertEqual(version, result.candidate.rule_version_label)

    def test_rule_gaps_have_no_version(self):
        for value in (date(2011, 5, 7), date(2011, 5, 9), date(2016, 9, 24), date(2016, 9, 26)):
            self.assertIsNone(EURO_MILLIONS.rule_for(value))

    def test_historical_star_limits_are_strict(self):
        old = normalize_row(replace(self.by_date["2004-02-13"], stars=["7", "10"]), self.provenance)
        middle = normalize_row(replace(self.by_date["2011-05-10"], stars=["5", "12"]), self.provenance)
        current = self.normalize_date("2016-09-27")
        self.assertIn("component.out_of_range", [issue.code for issue in old.issues])
        self.assertIn("component.out_of_range", [issue.code for issue in middle.issues])
        self.assertTrue(current.is_valid, current.issues)

    def test_winner_semantics_and_zero_money(self):
        winner = self.normalize_date("2004-02-13").candidate
        self.assertEqual("has_jackpot_winner", winner.series[0].attributes[0].key)
        zero_row = next(row for row in self.rows if row.prize == 0)
        amount = normalize_row(zero_row, self.provenance).candidate.monetary_amounts[0]
        self.assertEqual("unknown", amount.status.value)
        self.assertIsNone(amount.amount)

    def test_duplicate_empty_and_source_change(self):
        result = self.normalize_date("2025-12-26")
        duplicate = build_history_report((result, result), source_sha256_before=SHA, source_sha256_after=SHA)
        self.assertEqual(0, duplicate["summary"]["valid_rows"])
        self.assertFalse(build_history_report((), source_sha256_before=SHA, source_sha256_after=SHA)["baseline_matches"])
        self.assertFalse(build_history_report((), source_sha256_before=SHA, source_sha256_after="1" * 64)["source_unchanged"])

    def test_full_history_and_saved_report_are_reproducible(self):
        first = audit_history(SOURCE, observed_at=self.provenance.captured_at)
        second = audit_history(SOURCE, observed_at=datetime(2026, 10, 15, tzinfo=timezone.utc))
        self.assertEqual(report_json(first), report_json(second))
        self.assertEqual(first, json.loads(REPORT.read_text(encoding="utf-8")))
        self.assertTrue(first["source_unchanged"])
        self.assertTrue(first["baseline_matches"])
        self.assertEqual(1906, first["summary"]["valid_rows"])
        self.assertEqual({}, first["issue_counts"])
        self.assertEqual({"em_2004_50x9": 378, "em_2011_50x11": 562, "em_2016_50x12": 966}, first["rule_version_counts"])
        self.assertEqual({"false": 1466, "true": 440}, first["jackpot_winner_flag_counts"])
        self.assertEqual(9, first["unknown_zero_top_tier_prize_rows"])


if __name__ == "__main__":
    unittest.main()
