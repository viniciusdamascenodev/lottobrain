import json
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from app.domain import RawProvenance, ValueStatus
from app.ingestion.mais_milionaria import TIERS, iter_xlsx_rows, normalize_row
from app.ingestion.mais_milionaria_history import HistoryBaseline, audit_history, build_history_report, report_json

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/raw/mais_milionaria/mais_milionaria_resultados.xlsx"
SHA = HistoryBaseline().source_sha256


class MaisMilionariaTests(unittest.TestCase):
    def setUp(self):
        self.rows = json.loads((ROOT / "tests/fixtures/mais_milionaria_rows.json").read_text(encoding="utf-8"))
        self.provenance = RawProvenance("caixa_mais_milionaria_xlsx", SHA, datetime(2026, 9, 15, tzinfo=timezone.utc), "spec-0007")

    def normalize(self, **changes):
        return normalize_row(dict(self.rows[0], **changes), self.provenance)

    def report(self, results):
        return build_history_report(results, source_sha256_before=SHA, source_sha256_after=SHA)

    def test_real_fixtures_keep_groups_and_ten_tiers(self):
        for row in self.rows:
            result = normalize_row(row, self.provenance)
            self.assertTrue(result.is_valid, result.issues)
            components = {c.key: c.values for c in result.candidate.series[0].components}
            self.assertEqual(tuple(row[f"Bola{i}"] for i in range(1, 7)), components["main"])
            self.assertEqual((row["Trevo1"], row["Trevo2"]), components["clovers"])
            self.assertEqual({t[0] for t in TIERS}, {t.tier_key for t in result.candidate.prize_tiers})
            self.assertEqual("BRL", result.candidate.monetary_amounts[0].currency)
        self.assertEqual("mais_milionaria:official_draw_number:1", self.normalize().canonical_key)

    def test_invalid_main_numbers(self):
        for change in ({"Bola6": 51}, {"Bola6": 1}, {"Bola6": None}, {"Bola1": 50}):
            result = self.normalize(**change)
            self.assertFalse(result.is_valid)
            self.assertTrue(any("components.main" in i.path for i in result.issues))

    def test_clovers_validated_independently_and_order_preserved(self):
        for change in ({"Trevo2": 7}, {"Trevo2": 2}, {"Trevo1": None}, {"Trevo1": True}):
            result = self.normalize(**change)
            self.assertFalse(result.is_valid)
            self.assertTrue(any("components.clovers" in i.path for i in result.issues))
        reversed_result = self.normalize(Trevo1=4, Trevo2=2)
        self.assertTrue(reversed_result.is_valid)
        self.assertEqual((4, 2), reversed_result.candidate.series[0].components[1].values)
        # Sobreposição de valores entre grupos é legítima.
        self.assertTrue(self.normalize(Trevo1=1, Trevo2=3).is_valid)

    def test_extra_number_fields_are_not_silently_discarded(self):
        for key in ("Bola7", "Trevo3"):
            self.assertFalse(self.normalize(**{key: 1}).is_valid)

    def test_bad_identity_dates_and_negative_winners(self):
        for change in ({"Concurso": None}, {"Concurso": 0}, {"Data Sorteio": "31/02/2022"}):
            self.assertIsNone(self.normalize(**change).candidate)
        result = self.normalize(**{"Ganhadores 6 Números + 2 Trevos": -1})
        self.assertFalse(result.is_valid)
        self.assertIsNone(result.candidate.prize_tiers[0].winners)

    def test_money_zero_unknown_invalid_and_numeric(self):
        for raw, amount in (("R$0,00", Decimal("0")), (12.5, Decimal("12.5"))):
            result = self.normalize(**{"Arrecadacao Total": raw})
            self.assertTrue(result.is_valid)
            self.assertEqual(amount, result.candidate.monetary_amounts[0].amount)
        missing = self.normalize(**{"Arrecadacao Total": None})
        self.assertEqual(ValueStatus.UNKNOWN, missing.candidate.monetary_amounts[0].status)
        for raw in ("inválido", "NaN", "R$-1,00", True):
            result = self.normalize(**{"Arrecadacao Total": raw})
            self.assertFalse(result.is_valid)
            self.assertIn("source.invalid_money", [i.code for i in result.issues])

    def test_rollover_category_is_not_money_and_absence_is_not_no(self):
        field = "Acumulado 6 acertos + 2 Trevos"
        for raw, expected in (("Sim", True), ("Não", False)):
            result = self.normalize(**{field: raw})
            self.assertTrue(result.is_valid)
            self.assertEqual(expected, result.candidate.series[0].attributes[0].value)
            self.assertEqual(raw, dict(result.candidate.metadata)["rollover_flag_source_text"])
            self.assertNotIn("rollover_amount", [m.kind for m in result.candidate.monetary_amounts])
        missing = self.normalize(**{field: None})
        self.assertEqual((), missing.candidate.series[0].attributes)
        self.assertEqual({"unknown": 1}, self.report((missing,))["rollover_flag_counts"])
        invalid = self.normalize(**{field: "Talvez"})
        self.assertFalse(invalid.is_valid)
        self.assertEqual("Talvez", dict(invalid.candidate.metadata)["rollover_flag_source_text"])

    def test_duplicate_gap_empty_and_source_change(self):
        result = self.normalize()
        report = self.report((result, result))
        self.assertEqual(0, report["summary"]["valid_rows"])
        self.assertEqual(2, report["summary"]["invalid_rows"])
        self.assertEqual([2], self.report((result, self.normalize(Concurso=3)))["summary"]["missing_contests"])
        self.assertFalse(self.report(())["baseline_matches"])
        self.assertFalse(build_history_report((), source_sha256_before=SHA, source_sha256_after="1" * 64)["source_unchanged"])

    def test_header_collision_and_structure_failures_close_workbook(self):
        self.assertEqual("source.duplicate_header", self.normalize(**{"Con curso": 2}).issues[0].code)
        headers = tuple(self.rows[0])
        values = tuple(self.rows[0].values())
        class Sheet:
            def reset_dimensions(self):
                pass
            def iter_rows(self, values_only):
                return iter(self.rows)
        class Workbook:
            def __init__(self, rows):
                sheet = Sheet()
                sheet.rows = rows
                self.worksheets = [sheet]
                self.closed = False
            def close(self):
                self.closed = True
        for rows in ((headers[1:],), (headers[:-1] + ("Bola1",),), (headers, values + (99,))):
            workbook = Workbook(rows)
            with patch("openpyxl.load_workbook", return_value=workbook):
                with self.assertRaises(ValueError):
                    list(iter_xlsx_rows(SOURCE))
            self.assertTrue(workbook.closed)

    def test_full_history_and_saved_report_are_reproducible(self):
        first = audit_history(SOURCE, observed_at=self.provenance.captured_at)
        second = audit_history(SOURCE, observed_at=datetime(2026, 9, 16, tzinfo=timezone.utc))
        self.assertEqual(report_json(first), report_json(second))
        self.assertEqual(first, json.loads((ROOT / "docs/data/mais-milionaria-normalizacao-historica.json").read_text(encoding="utf-8")))
        self.assertTrue(first["baseline_matches"])
        self.assertTrue(first["source_unchanged"])
        self.assertEqual(314, first["summary"]["valid_rows"])
        self.assertEqual(1884, first["summary"]["main_values_count"])
        self.assertEqual({"values_count": 628, "min": 1, "max": 6}, first["special_components"]["clovers"])
        self.assertEqual({"yes": 312, "no": 2}, first["rollover_flag_counts"])
        self.assertEqual({}, first["issue_counts"])
        rows = list(iter_xlsx_rows(SOURCE))
        self.assertEqual([rows[0], rows[157], rows[-1]], self.rows)


if __name__ == "__main__":
    unittest.main()
