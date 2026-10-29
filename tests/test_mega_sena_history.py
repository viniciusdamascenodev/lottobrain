import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from app.domain import RawProvenance
from app.ingestion.mega_sena import normalize_row
from app.ingestion.mega_sena_history import HistoryBaseline, audit_history, build_history_report, report_json


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/raw/mega_sena/mega_sena_resultados.xlsx"
SHA256 = HistoryBaseline().source_sha256


class HistoryReportTests(unittest.TestCase):
    def setUp(self):
        self.row = json.loads((ROOT / "tests/fixtures/mega_sena_rows.json").read_text(encoding="utf-8"))[0]
        self.provenance = RawProvenance("caixa_mega_sena_xlsx", SHA256, datetime(2026, 9, 15, tzinfo=timezone.utc), "spec-0004")

    def report(self, results):
        return build_history_report(results, source_sha256_before=SHA256, source_sha256_after=SHA256)

    def test_duplicate_keys_are_not_dropped_or_counted_as_valid(self):
        result = normalize_row(self.row, self.provenance)
        report = self.report((result, result))
        self.assertEqual(2, report["summary"]["total_rows"])
        self.assertEqual(0, report["summary"]["valid_rows"])
        self.assertEqual(2, report["summary"]["invalid_rows"])
        self.assertEqual(2, report["summary"]["duplicate_key_rows"])
        self.assertEqual({"history.duplicate_key": 2}, report["issue_counts"])

    def test_missing_identity_is_counted_and_reported(self):
        row = dict(self.row, Concurso=None)
        report = self.report((normalize_row(row, self.provenance),))
        self.assertEqual(1, report["summary"]["missing_identity_rows"])
        self.assertEqual(1, report["summary"]["invalid_rows"])
        self.assertEqual(0, report["summary"]["candidate_rows"])
        self.assertFalse(report["baseline_matches"])

    def test_empty_input_does_not_match_baseline(self):
        report = self.report(())
        self.assertEqual(0, report["summary"]["total_rows"])
        self.assertIsNone(report["summary"]["first_date"])
        self.assertFalse(report["baseline_matches"])

    def test_content_hash_ignores_local_snapshot_time(self):
        first = normalize_row(self.row, self.provenance)
        later = RawProvenance(self.provenance.source_key, SHA256, datetime(2026, 9, 16, tzinfo=timezone.utc), "spec-0004")
        self.assertEqual(report_json(self.report((first,))), report_json(self.report((normalize_row(self.row, later),))))

    def test_changed_source_is_exposed(self):
        report = build_history_report((), source_sha256_before=SHA256, source_sha256_after="1" * 64)
        self.assertFalse(report["source_unchanged"])

    def test_gaps_between_observed_contests_are_reported(self):
        third_row = dict(self.row, Concurso=3)
        report = self.report((normalize_row(self.row, self.provenance), normalize_row(third_row, self.provenance)))
        self.assertEqual([2], report["summary"]["missing_contests"])

    def test_invalid_candidate_keeps_its_row_and_field_diagnostic(self):
        row = dict(self.row, Bola6=61)
        report = self.report((normalize_row(row, self.provenance),))
        self.assertEqual(1, report["summary"]["invalid_rows"])
        self.assertEqual(0, report["summary"]["valid_rows"])
        self.assertEqual("component.out_of_range", report["issues"][0]["code"])
        self.assertEqual(1, report["issues"][0]["row_position"])
        self.assertEqual("draw.series.primary.components.main", report["issues"][0]["path"])


class FullHistoryContractTests(unittest.TestCase):
    def test_full_snapshot_matches_baseline_and_is_reproducible(self):
        first = audit_history(SOURCE, observed_at=datetime(2026, 9, 15, tzinfo=timezone.utc))
        second = audit_history(SOURCE, observed_at=datetime(2026, 9, 16, tzinfo=timezone.utc))
        self.assertEqual(report_json(first), report_json(second))
        self.assertTrue(first["source_unchanged"])
        self.assertTrue(first["baseline_matches"])
        self.assertEqual(2954, first["summary"]["valid_rows"])
        self.assertEqual(2954, first["summary"]["unique_keys"])
        self.assertEqual([], first["summary"]["missing_contests"])
        self.assertEqual({}, first["issue_counts"])
        self.assertEqual(17724, first["summary"]["main_values_count"])
        for counts in first["money_counts"].values():
            self.assertEqual(2954, counts["known"])


if __name__ == "__main__":
    unittest.main()
