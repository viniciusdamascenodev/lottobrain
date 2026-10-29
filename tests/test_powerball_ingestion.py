import json
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from app.domain import RawProvenance, ValueStatus
from app.ingestion.powerball import RawPowerballRow, file_sha256, normalize_row, parse_html, read_html_rows

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/raw/powerball/powerball_resultados.html"
SHA = "12b1197b080bdf06cd8c944a66167732bb73850e8591b163faf985a3744b4238"


class PowerballContractTests(unittest.TestCase):
    def setUp(self):
        raw = json.loads((ROOT / "tests/fixtures/powerball_rows.json").read_text(encoding="utf-8"))
        self.rows = tuple(RawPowerballRow(**{k: tuple(v) if isinstance(v, list) else v for k, v in row.items()}) for row in raw)
        self.provenance = RawProvenance("usamega_powerball_html", SHA, datetime(2026, 9, 16, tzinfo=timezone.utc), "spec-0008")

    def test_three_real_shapes_keep_separate_semantics(self):
        current, multiplier_only, simple = (normalize_row(row, self.provenance) for row in self.rows)
        for result in (current, multiplier_only, simple):
            self.assertTrue(result.is_valid, result.issues)
            self.assertEqual((5, 1), tuple(len(c.values) for c in result.candidate.series[0].components))
        self.assertEqual("double_play", current.candidate.series[1].key)
        self.assertEqual(2, current.candidate.series[0].attributes[0].value)
        self.assertEqual(1, len(multiplier_only.candidate.series))
        self.assertEqual(2, multiplier_only.candidate.series[0].attributes[0].value)
        self.assertEqual((), simple.candidate.series[0].attributes)

    def test_identity_reference_and_jackpot(self):
        result = normalize_row(self.rows[0], self.provenance)
        self.assertEqual("powerball:drawing_date:2025-12-24", result.canonical_key)
        self.assertEqual(self.rows[0].drawing_href, result.candidate.external_references[0].value)
        jackpot = result.candidate.monetary_amounts[0]
        self.assertEqual((ValueStatus.KNOWN, Decimal("1816800000.0000"), "USD"), (jackpot.status, jackpot.amount, jackpot.currency))
        self.assertEqual(Decimal("6000000"), normalize_row(self.rows[-1], self.provenance).candidate.monetary_amounts[0].amount)

    def test_date_mismatch_and_invalid_dates(self):
        mismatch = normalize_row(replace(self.rows[0], visible_date="Tue, December, 23, 2025"), self.provenance)
        self.assertIn("source.date_mismatch", [i.code for i in mismatch.issues])
        missing = normalize_row(replace(self.rows[0], drawing_href="bad", visible_date="bad"), self.provenance)
        self.assertIsNone(missing.candidate)

    def test_invalid_multiplier_never_becomes_a_ball(self):
        for values in (("two",), ("2x", "3x")):
            result = normalize_row(replace(self.rows[1], multiplier_values=values), self.provenance)
            self.assertIn("source.invalid_multiplier", [i.code for i in result.issues])
            self.assertEqual(6, sum(len(c.values) for c in result.candidate.series[0].components))

    def test_incomplete_double_play_and_unknown_items_fail(self):
        incomplete = normalize_row(replace(self.rows[0], double_play_powerball=()), self.provenance)
        self.assertIn("component.invalid_count", [i.code for i in incomplete.issues])
        unknown = normalize_row(replace(self.rows[0], unknown_main_items=("99",)), self.provenance)
        self.assertIn("source.unknown_result_item", [i.code for i in unknown.issues])

    def test_invalid_numbers_duplicates_order_and_ranges(self):
        cases = (replace(self.rows[0], main_values=("4","4","31","52","59")),
                 replace(self.rows[0], main_values=("59","25","31","52","60")),
                 replace(self.rows[0], powerball_values=("46",)),
                 replace(self.rows[0], main_values=("x","25","31","52","59")))
        for row in cases:
            self.assertFalse(normalize_row(row, self.provenance).is_valid)

    def test_jackpot_missing_invalid_and_million_scale(self):
        missing = normalize_row(replace(self.rows[0], jackpot_text=None), self.provenance)
        self.assertTrue(missing.is_valid)
        self.assertEqual(ValueStatus.UNKNOWN, missing.candidate.monetary_amounts[0].status)
        self.assertFalse(normalize_row(replace(self.rows[0], jackpot_text="$10 Trillion"), self.provenance).is_valid)
        million = normalize_row(replace(self.rows[0], jackpot_text="$12.5 Million"), self.provenance)
        self.assertEqual(Decimal("12500000.0"), million.candidate.monetary_amounts[0].amount)

    def test_parser_uses_classes_not_flat_item_count(self):
        html = '<table><tbody><tr><td><section class="results"><a href="/powerball/drawing/2025/1/2">Thu, January, 2, 2025</a><ul><li>1</li><li>2</li><li>3</li><li>4</li><li>5</li><li class="mystery">6</li><li class="bonus">7</li></ul></section></td><td><a href="/powerball/jackpot/2025/1/2">$10 Million</a></td></tr></tbody></table>'
        row = parse_html(html)[0]
        self.assertEqual(("6",), row.unknown_main_items)
        self.assertFalse(normalize_row(row, self.provenance).is_valid)

    def test_full_file_extraction_contract_and_fixture_positions(self):
        before = file_sha256(SOURCE)
        rows = read_html_rows(SOURCE)
        self.assertEqual((SHA, before), (before, file_sha256(SOURCE)))
        self.assertEqual(3742, len(rows))
        shapes = {}
        for row in rows:
            shape = (len(row.multiplier_values), bool(row.double_play_main))
            shapes[shape] = shapes.get(shape, 0) + 1
        self.assertEqual({(1, True):680, (1, False):1926, (0, False):1136}, shapes)
        self.assertEqual((rows[0], rows[680], rows[-1]), self.rows)


if __name__ == "__main__":
    unittest.main()
