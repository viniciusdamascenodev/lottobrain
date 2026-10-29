import json
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from app.domain import RawProvenance, ValueStatus
from app.ingestion.lotofacil import iter_xlsx_rows, normalize_row
from app.ingestion.lotofacil_history import HistoryBaseline, audit_history, build_history_report, report_json

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/raw/lotofacil/lotofacil_resultados.xlsx"
SHA = HistoryBaseline().source_sha256


class LotofacilTests(unittest.TestCase):
    def setUp(self):
        self.rows = json.loads((ROOT / "tests/fixtures/lotofacil_rows.json").read_text(encoding="utf-8"))
        self.provenance = RawProvenance("caixa_lotofacil_xlsx", SHA, datetime(2026, 9, 15, tzinfo=timezone.utc), "spec-0006")

    def normalize(self, **changes):
        return normalize_row(dict(self.rows[0], **changes), self.provenance)

    def report(self, results):
        return build_history_report(results, source_sha256_before=SHA, source_sha256_after=SHA)

    def test_real_fixtures_and_five_tiers(self):
        for row in self.rows:
            result = normalize_row(row, self.provenance)
            self.assertTrue(result.is_valid, result.issues)
            self.assertEqual(15, len(result.candidate.series[0].components[0].values))
            self.assertEqual({f"hits_{n}" for n in range(11, 16)}, {tier.tier_key for tier in result.candidate.prize_tiers})
            self.assertEqual("BRL", result.candidate.monetary_amounts[0].currency)
        self.assertEqual(Decimal("2"), self.normalize().candidate.prize_tiers[-1].prize_per_winner.amount)
        self.assertEqual(Decimal("7"), normalize_row(self.rows[-1], self.provenance).candidate.prize_tiers[-1].prize_per_winner.amount)

    def test_bad_balls_are_diagnosed(self):
        for change in ({"Bola15": 26}, {"Bola15": 2}, {"Bola15": None}, {"Bola1": 25}):
            result = self.normalize(**change)
            self.assertFalse(result.is_valid)
            self.assertTrue(any("components.main" in issue.path for issue in result.issues))

    def test_bad_identity_and_date(self):
        for change in ({"Concurso": None}, {"Data Sorteio": "31/02/2020"}):
            result = self.normalize(**change)
            self.assertIsNone(result.candidate)
            self.assertEqual(1, self.report((result,))["summary"]["invalid_rows"])

    def test_zero_missing_invalid_and_numeric_money(self):
        for value, expected in (("R$0,00", Decimal("0")), (12.5, Decimal("12.5"))):
            result = self.normalize(**{"Arrecadacao Total": value})
            self.assertTrue(result.is_valid)
            self.assertEqual(expected, result.candidate.monetary_amounts[1].amount)
        missing = self.normalize(**{"Arrecadacao Total": None})
        self.assertEqual(ValueStatus.UNKNOWN, missing.candidate.monetary_amounts[1].status)
        for value in ("não disponível", "NaN", True):
            result = self.normalize(**{"Arrecadacao Total": value})
            self.assertFalse(result.is_valid)
            self.assertIn("source.invalid_money", [issue.code for issue in result.issues])

    def test_canonical_key_and_duplicate_history(self):
        result = self.normalize()
        self.assertEqual("lotofacil:official_draw_number:1", result.canonical_key)
        report = self.report((result, result))
        self.assertEqual(0, report["summary"]["valid_rows"])
        self.assertEqual(2, report["summary"]["invalid_rows"])

    def test_gaps_empty_and_changed_source(self):
        self.assertEqual([2], self.report((self.normalize(), self.normalize(Concurso=3)))["summary"]["missing_contests"])
        self.assertFalse(self.report(())["baseline_matches"])
        self.assertFalse(build_history_report((), source_sha256_before=SHA, source_sha256_after="1" * 64)["source_unchanged"])

    def test_header_collisions_rejected(self):
        result = self.normalize(**{"Con curso": 2})
        self.assertEqual("source.duplicate_header", result.issues[0].code)

    def test_xlsx_structure_contract_rejects_missing_duplicate_and_extra_cells(self):
        headers = tuple(self.rows[0])
        values = tuple(self.rows[0].values())
        class Worksheet:
            def reset_dimensions(self):
                pass
            def iter_rows(self, values_only):
                return iter(self.rows)
        class Workbook:
            def __init__(self, rows):
                sheet = Worksheet()
                sheet.rows = rows
                self.worksheets = [sheet]
                self.closed = False
            def close(self):
                self.closed = True
        for rows in ((headers[:-1] + ("Bola1",),), (headers[1:],), (headers, values + (99,))):
            workbook = Workbook(rows)
            with patch("openpyxl.load_workbook", return_value=workbook):
                with self.assertRaises(ValueError):
                    list(iter_xlsx_rows(SOURCE))
            self.assertTrue(workbook.closed)

    def test_full_history_repeatability_and_saved_diagnostic(self):
        first = audit_history(SOURCE, observed_at=self.provenance.captured_at)
        second = audit_history(SOURCE, observed_at=datetime(2026, 9, 16, tzinfo=timezone.utc))
        self.assertEqual(report_json(first), report_json(second))
        self.assertEqual(json.loads((ROOT / "docs/data/lotofacil-normalizacao-historica.json").read_text(encoding="utf-8")), first)
        self.assertTrue(first["baseline_matches"])
        self.assertTrue(first["source_unchanged"])
        self.assertEqual(3571, first["summary"]["valid_rows"])
        self.assertEqual(53565, first["summary"]["main_values_count"])
        self.assertEqual({}, first["issue_counts"])
        rows = list(iter_xlsx_rows(SOURCE))
        self.assertEqual([rows[0], rows[1785], rows[-1]], self.rows)


if __name__ == "__main__":
    unittest.main()
