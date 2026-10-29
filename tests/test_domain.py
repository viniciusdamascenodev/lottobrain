import unittest
from datetime import date, datetime, timezone
from decimal import Decimal

from app.domain import (
    ComponentDefinition,
    ComponentResult,
    DomainValidationError,
    DrawCandidate,
    DrawStatus,
    Lottery,
    LotteryRuleVersion,
    LotteryStatus,
    MonetaryAmount,
    OrderSemantics,
    RawProvenance,
    ResultAttribute,
    ResultSeries,
    ResultSeriesDefinition,
    SeriesRole,
    ValueStatus,
    ValueType,
    assert_valid_draw,
    validate_draw,
)


def integer_component(key, label, count, minimum, maximum, position=0):
    return ComponentDefinition(
        key=key,
        label=label,
        value_type=ValueType.INTEGER,
        min_count=count,
        max_count=count,
        min_value=minimum,
        max_value=maximum,
        unique_values=True,
        order_semantics=OrderSemantics.SORTED,
        position=position,
    )


def lottery(slug, name, components, additional_series=()):
    primary = ResultSeriesDefinition(
        key="primary",
        label="Resultado principal",
        role=SeriesRole.PRIMARY,
        components=tuple(components),
    )
    rule = LotteryRuleVersion(
        version_label="current",
        valid_from=date(1990, 1, 1),
        series=(primary, *additional_series),
    )
    return Lottery(
        slug=slug,
        display_name=name,
        jurisdiction_code="TEST",
        rules=(rule,),
        status=LotteryStatus.ACTIVE,
    )


def candidate(slug, components, attributes=(), extra_series=()):
    return DrawCandidate(
        lottery_slug=slug,
        draw_date=date(2025, 12, 1),
        rule_version_label="current",
        official_draw_number="1",
        series=(
            ResultSeries(
                key="primary",
                components=tuple(ComponentResult(key, tuple(values)) for key, values in components),
                attributes=tuple(attributes),
            ),
            *extra_series,
        ),
    )


class SixLotteryContractTests(unittest.TestCase):
    def test_representative_draws_for_all_six_lotteries(self):
        cases = [
            (
                lottery("mega_sena", "Mega-Sena", [integer_component("main", "Números", 6, 1, 60)]),
                candidate("mega_sena", [("main", (4, 5, 30, 33, 41, 52))]),
            ),
            (
                lottery("lotofacil", "Lotofácil", [integer_component("main", "Números", 15, 1, 25)]),
                candidate("lotofacil", [("main", tuple(range(1, 16)))]),
            ),
            (
                lottery(
                    "mais_milionaria",
                    "+Milionária",
                    [
                        integer_component("main", "Números", 6, 1, 50),
                        integer_component("trevos", "Trevos", 2, 1, 6, 1),
                    ],
                ),
                candidate("mais_milionaria", [("main", (1, 3, 7, 15, 23, 44)), ("trevos", (2, 4))]),
            ),
            (
                lottery(
                    "powerball",
                    "Powerball",
                    [
                        integer_component("main", "Números", 5, 1, 69),
                        integer_component("powerball", "Powerball", 1, 1, 26, 1),
                    ],
                ),
                candidate(
                    "powerball",
                    [("main", (4, 25, 31, 52, 59)), ("powerball", (19,))],
                    attributes=(ResultAttribute("power_play", 2),),
                ),
            ),
            (
                lottery(
                    "mega_millions",
                    "Mega Millions",
                    [
                        integer_component("main", "Números", 5, 1, 70),
                        integer_component("mega_ball", "Mega Ball", 1, 1, 25, 1),
                    ],
                ),
                candidate(
                    "mega_millions",
                    [("main", (15, 37, 38, 41, 64)), ("mega_ball", (21,))],
                ),
            ),
            (
                lottery(
                    "euro_millions",
                    "EuroMillions",
                    [
                        integer_component("main", "Números", 5, 1, 50),
                        integer_component("stars", "Estrelas", 2, 1, 12, 1),
                    ],
                ),
                candidate("euro_millions", [("main", (8, 26, 27, 29, 44)), ("stars", (11, 12))]),
            ),
        ]
        for definition, draw in cases:
            with self.subTest(lottery=definition.slug):
                self.assertEqual((), validate_draw(draw, definition))

    def test_double_play_is_a_separate_optional_series(self):
        double_play = ResultSeriesDefinition(
            key="double_play",
            label="Double Play",
            role=SeriesRole.ADDITIONAL,
            required=False,
            components=(
                integer_component("main", "Números", 5, 1, 69),
                integer_component("powerball", "Powerball", 1, 1, 26, 1),
            ),
        )
        definition = lottery(
            "powerball",
            "Powerball",
            [
                integer_component("main", "Números", 5, 1, 69),
                integer_component("powerball", "Powerball", 1, 1, 26, 1),
            ],
            (double_play,),
        )
        extra = ResultSeries(
            key="double_play",
            components=(
                ComponentResult("main", (3, 15, 19, 29, 35)),
                ComponentResult("powerball", (21,)),
            ),
        )
        draw = candidate(
            "powerball",
            [("main", (4, 25, 31, 52, 59)), ("powerball", (19,))],
            extra_series=(extra,),
        )
        self.assertEqual((), validate_draw(draw, definition))


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.mega_sena = lottery(
            "mega_sena",
            "Mega-Sena",
            [integer_component("main", "Números", 6, 1, 60)],
        )

    def test_invalid_count_range_duplicates_and_order_are_reported(self):
        draw = candidate("mega_sena", [("main", (61, 3, 3, 2, 1))])
        codes = {issue.code for issue in validate_draw(draw, self.mega_sena)}
        self.assertEqual(
            {
                "component.invalid_count",
                "component.out_of_range",
                "component.duplicate_values",
                "component.invalid_order",
            },
            codes,
        )

    def test_assert_valid_raises_structured_error(self):
        draw = candidate("mega_sena", [("main", (1, 2, 3, 4, 5))])
        with self.assertRaises(DomainValidationError) as context:
            assert_valid_draw(draw, self.mega_sena)
        self.assertEqual("component.invalid_count", context.exception.issues[0].code)

    def test_rule_version_is_selected_by_draw_date(self):
        old = LotteryRuleVersion(
            version_label="old",
            valid_from=date(1990, 1, 1),
            valid_to=date(2010, 1, 1),
            series=self.mega_sena.rules[0].series,
        )
        current = LotteryRuleVersion(
            version_label="current",
            valid_from=date(2010, 1, 1),
            series=self.mega_sena.rules[0].series,
        )
        versioned = Lottery("mega_sena", "Mega-Sena", "BR", (old, current))
        self.assertEqual("old", versioned.rule_for(date(2000, 1, 1)).version_label)
        self.assertEqual("current", versioned.rule_for(date(2025, 1, 1)).version_label)

    def test_overlapping_validated_rules_are_rejected(self):
        first = self.mega_sena.rules[0]
        overlapping = LotteryRuleVersion(
            version_label="overlap",
            valid_from=date(2020, 1, 1),
            series=first.series,
        )
        with self.assertRaisesRegex(ValueError, "sobrepor"):
            Lottery("mega_sena", "Mega-Sena", "BR", (first, overlapping))

    def test_active_lottery_requires_a_validated_rule_but_draft_can_be_empty(self):
        draft = Lottery("nova_loteria", "Nova Loteria", "BR", ())
        self.assertEqual(LotteryStatus.DRAFT, draft.status)
        with self.assertRaisesRegex(ValueError, "regra validada"):
            Lottery(
                "nova_loteria",
                "Nova Loteria",
                "BR",
                (),
                status=LotteryStatus.ACTIVE,
            )

    def test_published_draw_requires_raw_provenance(self):
        base = candidate("mega_sena", [("main", (1, 2, 3, 4, 5, 6))])
        published = DrawCandidate(
            lottery_slug=base.lottery_slug,
            draw_date=base.draw_date,
            rule_version_label=base.rule_version_label,
            series=base.series,
            status=DrawStatus.PUBLISHED,
        )
        self.assertEqual("draw.missing_provenance", validate_draw(published, self.mega_sena)[0].code)

        with_provenance = DrawCandidate(
            lottery_slug=base.lottery_slug,
            draw_date=base.draw_date,
            rule_version_label=base.rule_version_label,
            series=base.series,
            status=DrawStatus.PUBLISHED,
            provenance=RawProvenance(
                source_key="caixa",
                raw_sha256="0" * 64,
                captured_at=datetime(2025, 12, 1, tzinfo=timezone.utc),
                adapter_version="1",
            ),
        )
        self.assertEqual((), validate_draw(with_provenance, self.mega_sena))

    def test_zero_money_is_known_and_unknown_money_has_no_normalized_value(self):
        amount = MonetaryAmount(
            kind="paid_per_winner",
            status=ValueStatus.KNOWN,
            amount=Decimal("0"),
            currency="BRL",
        )
        self.assertEqual(Decimal("0"), amount.amount)
        with self.assertRaisesRegex(ValueError, "não conhecido"):
            MonetaryAmount(
                kind="jackpot",
                status=ValueStatus.UNKNOWN,
                amount=Decimal("10"),
                currency="EUR",
            )


if __name__ == "__main__":
    unittest.main()
