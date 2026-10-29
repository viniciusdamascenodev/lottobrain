import json
import unittest
from dataclasses import replace
from datetime import date, datetime, timezone
from pathlib import Path

from app.domain import RawProvenance
from app.ingestion.mega_millions import MEGA_MILLIONS, normalize_row, read_html_rows
from app.ingestion.mega_millions_history import HistoryBaseline, audit_history, build_history_report
from app.ingestion.mega_sena_history import report_json


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/raw/mega_millions/mega_millions_resultados.html"
REPORT = ROOT / "docs/data/mega-millions-normalizacao-historica.json"
SHA = HistoryBaseline().source_sha256


class MegaMillionsHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = read_html_rows(SOURCE)
        cls.by_date = {}
        for row in cls.rows:
            parts = row.drawing_href.rsplit("/", 3)[-3:]
            cls.by_date[f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"] = row
        cls.provenance = RawProvenance("usamega_mega_millions_html", SHA, datetime(2026, 10, 14, tzinfo=timezone.utc), "spec-0013")

    def normalize_date(self, value):
        return normalize_row(self.by_date[value], self.provenance)

    def test_seven_rule_boundaries(self):
        expected = {
            "1996-09-06": "mm_1996_50x25", "1999-01-12": "mm_1996_50x25",
            "1999-01-15": "mm_1999_50x36", "2002-05-14": "mm_1999_50x36",
            "2002-05-17": "mm_2002_52x52", "2005-06-21": "mm_2002_52x52",
            "2005-06-24": "mm_2005_56x46", "2013-10-18": "mm_2005_56x46",
            "2013-10-22": "mm_2013_75x15", "2017-10-27": "mm_2013_75x15",
            "2017-10-31": "mm_2017_70x25", "2025-04-04": "mm_2017_70x25",
            "2025-04-08": "mm_2025_70x24", "2025-12-23": "mm_2025_70x24",
        }
        for draw_date, version in expected.items():
            result = self.normalize_date(draw_date)
            self.assertTrue(result.is_valid, (draw_date, result.issues))
            self.assertEqual(version, result.candidate.rule_version_label)

    def test_rule_gaps_have_no_version(self):
        for value in (date(1999, 1, 13), date(2002, 5, 16), date(2025, 4, 6)):
            self.assertIsNone(MEGA_MILLIONS.rule_for(value))

    def test_historical_limits_are_strict_by_version(self):
        old = self.normalize_date("2002-05-17")
        current = normalize_row(replace(self.by_date["2025-12-23"], mega_ball_values=("25",)), self.provenance)
        self.assertTrue(old.is_valid, old.issues)
        self.assertIn("component.out_of_range", [issue.code for issue in current.issues])

    def test_multiplier_states_are_distinct(self):
        cases = {
            "2003-12-02": ("not_applicable", False),
            "2003-12-05": ("drawn_optional_megaplier", True),
            "2025-04-04": ("drawn_optional_megaplier", True),
            "2025-04-08": ("ticket_assigned_multiplier", False),
        }
        for draw_date, (state, has_value) in cases.items():
            result = self.normalize_date(draw_date)
            self.assertTrue(result.is_valid, (draw_date, result.issues))
            self.assertEqual(state, dict(result.candidate.metadata)["multiplier_state"])
            self.assertEqual(has_value, bool(result.candidate.series[0].attributes))
        missing = normalize_row(replace(self.by_date["2025-04-04"], multiplier_values=()), self.provenance)
        self.assertIn("source.missing_multiplier", [issue.code for issue in missing.issues])
        unexpected = normalize_row(replace(self.by_date["2025-04-08"], multiplier_values=("2x",)), self.provenance)
        self.assertIn("source.unexpected_multiplier", [issue.code for issue in unexpected.issues])

    def test_duplicate_empty_and_source_change(self):
        result = self.normalize_date("2025-12-23")
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
        self.assertEqual(2984, first["summary"]["valid_rows"])
        self.assertEqual({}, first["issue_counts"])
        self.assertEqual(682, first["multiplier_state_counts"]["not_applicable"])
        self.assertEqual(2227, first["multiplier_state_counts"]["drawn_optional_megaplier"])
        self.assertEqual(75, first["multiplier_state_counts"]["ticket_assigned_multiplier"])


if __name__ == "__main__":
    unittest.main()
