import json
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from app.domain import RawProvenance, ValueStatus
from app.ingestion.mega_millions import RawMegaMillionsRow, file_sha256, normalize_row, parse_html, read_html_rows

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/raw/mega_millions/mega_millions_resultados.html"
SHA = "c154cb21ae6381efe53f9735b5704d148156ba9737266de54e8badbf1d92c35c"


class MegaMillionsContractTests(unittest.TestCase):
    def setUp(self):
        raw = json.loads((ROOT / "tests/fixtures/mega_millions_rows.json").read_text(encoding="utf-8"))
        self.rows = tuple(RawMegaMillionsRow(**{key: tuple(value) if isinstance(value, list) else value for key, value in row.items()}) for row in raw)
        self.provenance = RawProvenance("usamega_mega_millions_html", SHA, datetime(2026, 10, 14, tzinfo=timezone.utc), "spec-0011")

    def test_real_shapes_keep_mega_ball_and_megaplier_separate(self):
        current, multiplier, early = (normalize_row(row, self.provenance) for row in self.rows)
        for result in (current, multiplier, early):
            self.assertTrue(result.is_valid, result.issues)
            self.assertEqual((5, 1), tuple(len(component.values) for component in result.candidate.series[0].components))
        self.assertEqual((), current.candidate.series[0].attributes)
        self.assertEqual(2, multiplier.candidate.series[0].attributes[0].value)
        self.assertEqual((), early.candidate.series[0].attributes)

    def test_identity_reference_and_jackpot(self):
        result = normalize_row(self.rows[0], self.provenance)
        self.assertEqual("mega_millions:drawing_date:2025-12-23", result.canonical_key)
        self.assertEqual(self.rows[0].drawing_href, result.candidate.external_references[0].value)
        self.assertEqual((ValueStatus.KNOWN, Decimal("100000000"), "USD"), (result.candidate.monetary_amounts[0].status, result.candidate.monetary_amounts[0].amount, result.candidate.monetary_amounts[0].currency))

    def test_bad_dates_and_mismatch(self):
        mismatch = normalize_row(replace(self.rows[0], visible_date="Mon, December, 22, 2025"), self.provenance)
        self.assertIn("source.date_mismatch", [issue.code for issue in mismatch.issues])
        missing = normalize_row(replace(self.rows[0], drawing_href="bad", visible_date="bad"), self.provenance)
        self.assertIsNone(missing.candidate)

    def test_invalid_multiplier_never_becomes_a_ball(self):
        for values in (("two",), ("2x", "3x")):
            result = normalize_row(replace(self.rows[1], multiplier_values=values), self.provenance)
            self.assertIn("source.invalid_multiplier", [issue.code for issue in result.issues])
            self.assertEqual(6, sum(len(component.values) for component in result.candidate.series[0].components))

    def test_unknown_classes_and_blocks_fail_closed(self):
        html = '<table><tbody><tr><td><section class="results"><a href="/mega-millions/drawing/2025/1/3">Fri, January, 3, 2025</a><ul><li>1</li><li>2</li><li>3</li><li>4</li><li>5</li><li class="mystery">6</li><li class="bonus">7</li></ul><ul><li>8</li></ul></section></td><td><a href="/mega-millions/jackpot/2025/1/3">$10 Million</a></td></tr></tbody></table>'
        row = parse_html(html)[0]
        self.assertEqual(1, row.unknown_result_blocks)
        self.assertFalse(normalize_row(row, self.provenance).is_valid)

    def test_invalid_numbers_and_money(self):
        for row in (replace(self.rows[0], main_values=("15", "15", "38", "41", "64")), replace(self.rows[0], main_values=("15", "37", "38", "41", "76")), replace(self.rows[0], mega_ball_values=("53",)), replace(self.rows[0], main_values=("x", "37", "38", "41", "64"))):
            self.assertFalse(normalize_row(row, self.provenance).is_valid)
        self.assertFalse(normalize_row(replace(self.rows[0], jackpot_text="$10 Trillion"), self.provenance).is_valid)
        missing = normalize_row(replace(self.rows[0], jackpot_text=None), self.provenance)
        self.assertEqual(ValueStatus.UNKNOWN, missing.candidate.monetary_amounts[0].status)

    def test_full_file_contract_and_fixture_positions(self):
        before = file_sha256(SOURCE)
        rows = read_html_rows(SOURCE)
        self.assertEqual((SHA, before), (before, file_sha256(SOURCE)))
        self.assertEqual(2984, len(rows))
        shapes = {}
        for row in rows:
            shape = len(row.multiplier_values)
            shapes[shape] = shapes.get(shape, 0) + 1
        self.assertEqual({0: 757, 1: 2227}, shapes)
        by_path = {row.drawing_href: row for row in rows}
        self.assertEqual(self.rows, tuple(by_path[row.drawing_href] for row in self.rows))


if __name__ == "__main__":
    unittest.main()
