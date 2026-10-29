import json
import unittest
from dataclasses import replace
from datetime import date, datetime, timezone
from pathlib import Path

from app.domain import RawProvenance
from app.ingestion.mega_sena_history import report_json
from app.ingestion.powerball import POWERBALL, RawPowerballRow, normalize_row, read_html_rows
from app.ingestion.powerball_history import HistoryBaseline, audit_history, build_history_report


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/raw/powerball/powerball_resultados.html"
REPORT = ROOT / "docs/data/powerball-normalizacao-historica.json"
SHA = HistoryBaseline().source_sha256


class PowerballHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = read_html_rows(SOURCE)
        cls.by_date = {row.drawing_href.rsplit("/", 3)[-3:][0] + "-" + row.drawing_href.rsplit("/", 2)[-2].zfill(2) + "-" + row.drawing_href.rsplit("/", 1)[-1].zfill(2): row for row in cls.rows}
        cls.provenance = RawProvenance("usamega_powerball_html", SHA, datetime(2026, 10, 14, tzinfo=timezone.utc), "spec-0010")

    def normalize_date(self, value):
        return normalize_row(self.by_date[value], self.provenance)

    def test_seven_rule_boundaries_are_selected_by_draw_date(self):
        expected = {
            "1992-04-22": "pb_1992_45x45", "1997-11-01": "pb_1992_45x45",
            "1997-11-05": "pb_1997_49x42", "2002-10-05": "pb_1997_49x42",
            "2002-10-09": "pb_2002_53x42", "2005-08-27": "pb_2002_53x42",
            "2005-08-31": "pb_2005_55x42", "2009-01-03": "pb_2005_55x42",
            "2009-01-07": "pb_2009_59x39", "2012-01-14": "pb_2009_59x39",
            "2012-01-18": "pb_2012_59x35", "2015-10-03": "pb_2012_59x35",
            "2015-10-07": "pb_2015_69x26", "2025-12-24": "pb_2015_69x26",
        }
        for draw_date, version in expected.items():
            result = self.normalize_date(draw_date)
            self.assertTrue(result.is_valid, (draw_date, result.issues))
            self.assertEqual(version, result.candidate.rule_version_label)

    def test_rule_gaps_have_no_version(self):
        for value in (date(1997, 11, 3), date(2002, 10, 7), date(2015, 10, 5)):
            self.assertIsNone(POWERBALL.rule_for(value))

    def test_historical_range_is_not_validated_with_current_limits(self):
        old = self.normalize_date("1992-04-22")
        current = normalize_row(replace(self.by_date["2025-12-24"], powerball_values=("45",)), self.provenance)
        self.assertTrue(old.is_valid, old.issues)
        self.assertIn("component.out_of_range", [issue.code for issue in current.issues])

    def test_power_play_states_are_date_sensitive(self):
        cases = {
            "2001-03-03": ("not_applicable", False),
            "2001-03-07": ("observed", True),
            "2012-01-18": ("fixed_prize_no_multiplier", False),
            "2014-01-18": ("fixed_prize_no_multiplier", False),
            "2014-01-22": ("observed", True),
        }
        for draw_date, (state, has_value) in cases.items():
            result = self.normalize_date(draw_date)
            self.assertTrue(result.is_valid, (draw_date, result.issues))
            self.assertEqual(state, dict(result.candidate.metadata)["power_play_state"])
            self.assertEqual(has_value, bool(result.candidate.series[0].attributes))
        missing = normalize_row(replace(self.by_date["2014-01-22"], multiplier_values=()), self.provenance)
        self.assertIn("source.missing_multiplier", [issue.code for issue in missing.issues])
        unexpected = normalize_row(replace(self.by_date["2012-01-18"], multiplier_values=("2x",)), self.provenance)
        self.assertIn("source.unexpected_multiplier", [issue.code for issue in unexpected.issues])

    def test_double_play_launch_is_enforced(self):
        self.assertEqual(1, len(self.normalize_date("2021-08-21").candidate.series))
        self.assertEqual(2, len(self.normalize_date("2021-08-23").candidate.series))
        missing = normalize_row(replace(self.by_date["2021-08-23"], double_play_main=(), double_play_powerball=()), self.provenance)
        self.assertIn("source.missing_double_play", [issue.code for issue in missing.issues])

    def test_duplicate_empty_and_source_change_are_exposed(self):
        result = self.normalize_date("2025-12-24")
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
        self.assertEqual(3742, first["summary"]["valid_rows"])
        self.assertEqual({}, first["issue_counts"])
        self.assertEqual(680, first["special_components"]["double_play"]["rows"])
        self.assertEqual(210, first["power_play_state_counts"]["fixed_prize_no_multiplier"])


if __name__ == "__main__":
    unittest.main()
