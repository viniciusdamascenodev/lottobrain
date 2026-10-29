import unittest
from datetime import date

from app.catalog import CATALOG, VERIFIED_AT
from app.domain import (
    CollectionReadiness,
    DataSourceDefinition,
    Lottery,
    LotteryCatalog,
    LotteryCatalogEntry,
    MarketDefinition,
    SourceAuthority,
)


class CatalogTests(unittest.TestCase):
    def test_catalog_contains_the_six_supported_lotteries_once(self):
        self.assertEqual(
            {
                "mega_sena",
                "lotofacil",
                "mais_milionaria",
                "powerball",
                "mega_millions",
                "euro_millions",
            },
            {entry.lottery.slug for entry in CATALOG.entries},
        )
        self.assertEqual(6, len(CATALOG.entries))

    def test_catalog_reuses_the_complete_historical_rule_contracts(self):
        expected_versions = {
            "mega_sena": 1,
            "lotofacil": 1,
            "mais_milionaria": 1,
            "powerball": 7,
            "mega_millions": 7,
            "euro_millions": 3,
        }
        self.assertEqual(
            expected_versions,
            {entry.lottery.slug: len(entry.lottery.rules) for entry in CATALOG.entries},
        )
        self.assertEqual(
            "mm_2025_70x24",
            CATALOG.get("mega_millions").lottery.rule_for(date(2026, 1, 1)).version_label,
        )

    def test_schedules_are_observations_and_do_not_invent_start_dates(self):
        for entry in CATALOG.entries:
            self.assertTrue(entry.schedules)
            for schedule in entry.schedules:
                self.assertEqual(VERIFIED_AT, schedule.observed_at)
                self.assertIsNone(schedule.valid_from)
                self.assertIn("/", schedule.timezone)

    def test_authority_and_collection_readiness_are_independent(self):
        powerball = CATALOG.get("powerball")
        official = next(source for source in powerball.sources if source.authority is SourceAuthority.OFFICIAL)
        historical = next(source for source in powerball.sources if "historical_results" in source.purposes)
        self.assertEqual(CollectionReadiness.RESEARCH_REQUIRED, official.readiness)
        self.assertEqual(SourceAuthority.SECONDARY, historical.authority)
        self.assertEqual(CollectionReadiness.CONTRACT_OBSERVED, historical.readiness)

    def test_cross_jurisdiction_extensions_are_not_result_components(self):
        powerball = CATALOG.get("powerball")
        self.assertEqual({"power_play", "double_play"}, {item.key for item in powerball.extensions})
        primary_keys = {
            component.key
            for component in powerball.lottery.rules[-1].series[0].components
        }
        self.assertEqual({"main", "powerball"}, primary_keys)

    def test_new_draft_lottery_can_be_registered_without_database(self):
        draft = Lottery("future_game", "Future Game", "BR", ())
        source = DataSourceDefinition(
            "manual_research",
            "Pesquisa manual",
            SourceAuthority.MANUAL,
            ("rules",),
            "html",
            "https://example.test/rules",
            CollectionReadiness.DISABLED,
        )
        entry = LotteryCatalogEntry(
            lottery=draft,
            markets=(MarketDefinition("BR", "BRL"),),
            sources=(source,),
        )
        expanded = CATALOG.register(entry)
        self.assertIsNone(CATALOG.get("future_game"))
        self.assertIs(entry, expanded.get("future_game"))

    def test_duplicate_registration_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "já cadastrada"):
            CATALOG.register(CATALOG.get("mega_sena"))
        with self.assertRaisesRegex(ValueError, "slugs duplicados"):
            LotteryCatalog((CATALOG.entries[0], CATALOG.entries[0]))


if __name__ == "__main__":
    unittest.main()
