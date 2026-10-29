import json
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from app.domain import RawProvenance, ValueStatus
from app.ingestion.euro_millions import RawEuroMillionsRow, file_sha256, normalize_row, parse_json, read_json_rows

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/raw/euro_millions/euro_millions_resultados.json"
SHA = "e4e7f97102c868569e33d54e34e258671cfca98f6872cf21fc0f86b171e57914"


class EuroMillionsContractTests(unittest.TestCase):
    def setUp(self):
        payload = json.loads((ROOT / "tests/fixtures/euro_millions_rows.json").read_text(encoding="utf-8"), parse_float=Decimal)
        self.rows = tuple(RawEuroMillionsRow(item["date"], item["draw_id"], item["has_winner"], item["id"], item["numbers"], item["prize"], item["stars"]) for item in payload)
        self.provenance = RawProvenance("pedromealha_euromillions_api_json", SHA, datetime(2026, 10, 14, tzinfo=timezone.utc), "spec-0016")

    def test_real_rows_keep_main_stars_and_winner_flag_separate(self):
        for row in self.rows:
            result = normalize_row(row, self.provenance)
            self.assertTrue(result.is_valid, result.issues)
            self.assertEqual((5, 2), tuple(len(component.values) for component in result.candidate.series[0].components))
            self.assertIs(row.has_winner, result.candidate.series[0].attributes[0].value)

    def test_identity_references_are_preserved_without_certifying_them(self):
        result = normalize_row(self.rows[1], self.provenance)
        self.assertEqual("euro_millions:drawing_date:2024-11-19", result.canonical_key)
        refs = {(reference.namespace, reference.value) for reference in result.candidate.external_references}
        self.assertEqual({("source_id", "3943"), ("draw_id", "932024")}, refs)
        self.assertIsNone(result.candidate.official_draw_number)

    def test_prize_uses_researched_semantics_and_provenance(self):
        amount = normalize_row(self.rows[0], self.provenance).candidate.monetary_amounts[0]
        self.assertEqual(ValueStatus.KNOWN, amount.status)
        self.assertEqual(Decimal("15000000.0"), amount.amount)
        self.assertEqual("EUR", amount.currency)
        self.assertEqual("top_tier_prize_per_winner", amount.kind)
        self.assertEqual("15000000.0", amount.source_text)
        metadata = dict(normalize_row(self.rows[0], self.provenance).candidate.metadata)
        self.assertEqual("top_tier_5_plus_2_per_winner", metadata["prize_scope"])
        self.assertEqual("PT_or_ES", metadata["prize_source_jurisdiction"])

    def test_zero_prize_is_unknown_not_known_zero(self):
        amount = normalize_row(replace(self.rows[0], prize=Decimal("0.0")), self.provenance).candidate.monetary_amounts[0]
        self.assertEqual(ValueStatus.UNKNOWN, amount.status)
        self.assertIsNone(amount.amount)
        self.assertEqual("0.0", amount.source_text)

    def test_invalid_date_identifiers_boolean_and_money(self):
        self.assertIsNone(normalize_row(replace(self.rows[0], date_value="bad"), self.provenance).candidate)
        for changes, code in (({"source_id": 0}, "source.invalid_identifier"), ({"draw_id": True}, "source.invalid_identifier"), ({"has_winner": "yes"}, "source.invalid_boolean"), ({"prize": Decimal("NaN")}, "source.invalid_money"), ({"prize": -1}, "source.invalid_money")):
            result = normalize_row(replace(self.rows[0], **changes), self.provenance)
            self.assertIn(code, [issue.code for issue in result.issues])

    def test_invalid_components_and_structure_fail_closed(self):
        for changes in ({"numbers": ["16", "16", "32", "36", "41"]}, {"numbers": ["16", "29", "32", "36", "51"]}, {"stars": ["7", "13"]}, {"stars": "7,9"}, {"numbers": [16, "29", "32", "36", "41"]}):
            self.assertFalse(normalize_row(replace(self.rows[0], **changes), self.provenance).is_valid)
        self.assertIn("source.invalid_structure", [issue.code for issue in normalize_row(replace(self.rows[0], extra_fields=("new",)), self.provenance).issues])

    def test_parser_rejects_non_list_and_non_object(self):
        with self.assertRaises(ValueError):
            parse_json("{}")
        with self.assertRaises(ValueError):
            parse_json("[1]")

    def test_full_file_contract_and_fixture_reconciliation(self):
        before = file_sha256(SOURCE)
        rows = read_json_rows(SOURCE)
        self.assertEqual((SHA, before), (before, file_sha256(SOURCE)))
        self.assertEqual(1906, len(rows))
        self.assertEqual(1906, len({row.draw_id for row in rows}))
        self.assertEqual(1906, len({row.source_id for row in rows}))
        by_source_id = {row.source_id: row for row in rows}
        self.assertEqual(self.rows, tuple(by_source_id[row.source_id] for row in self.rows))


if __name__ == "__main__":
    unittest.main()
