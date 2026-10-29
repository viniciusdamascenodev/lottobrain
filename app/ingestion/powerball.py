"""Contrato conservador para o HTML histórico da Powerball."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable

from app.domain import (
    ComponentDefinition, ComponentResult, DrawCandidate, DrawStatus, ExternalReference,
    Lottery, LotteryRuleVersion, LotteryStatus, MonetaryAmount, OrderSemantics,
    RawProvenance, ResultAttribute, ResultSeries, ResultSeriesDefinition, SeriesRole,
    ValidationIssue, ValueStatus, ValueType, validate_draw,
)
from app.ingestion.lotofacil import NormalizationResult

SOURCE_KEY = "usamega_powerball_html"
NORMALIZER_VERSION = "spec-0010"


def _series(main_max: int, powerball_max: int):
    components = (
        ComponentDefinition("main", "Números", ValueType.INTEGER, 5, 5, 1, main_max, True, OrderSemantics.SORTED),
        ComponentDefinition("powerball", "Powerball", ValueType.INTEGER, 1, 1, 1, powerball_max, True, OrderSemantics.NONE, 1),
    )
    return (
        ResultSeriesDefinition("primary", "Resultado principal", SeriesRole.PRIMARY, components),
        ResultSeriesDefinition("double_play", "Double Play", SeriesRole.ADDITIONAL, components, required=False),
    )


RULES = (
    LotteryRuleVersion("pb_1992_45x45", date(1992, 4, 22), _series(45, 45), date(1997, 11, 2), source_reference="SPEC-0009"),
    LotteryRuleVersion("pb_1997_49x42", date(1997, 11, 5), _series(49, 42), date(2002, 10, 6), source_reference="SPEC-0009"),
    LotteryRuleVersion("pb_2002_53x42", date(2002, 10, 9), _series(53, 42), date(2005, 8, 28), source_reference="SPEC-0009"),
    LotteryRuleVersion("pb_2005_55x42", date(2005, 8, 31), _series(55, 42), date(2009, 1, 4), source_reference="SPEC-0009"),
    LotteryRuleVersion("pb_2009_59x39", date(2009, 1, 7), _series(59, 39), date(2012, 1, 15), source_reference="SPEC-0009"),
    LotteryRuleVersion("pb_2012_59x35", date(2012, 1, 18), _series(59, 35), date(2015, 10, 4), source_reference="SPEC-0009"),
    LotteryRuleVersion("pb_2015_69x26", date(2015, 10, 7), _series(69, 26), source_reference="SPEC-0009"),
)
POWERBALL = Lottery(
    slug="powerball", display_name="Powerball", jurisdiction_code="US",
    default_timezone="America/New_York", default_currency="USD", status=LotteryStatus.ACTIVE,
    rules=RULES,
)


def _power_play_state(draw_date: date) -> str:
    if draw_date < date(2001, 3, 7):
        return "not_applicable"
    if date(2012, 1, 18) <= draw_date <= date(2014, 1, 18):
        return "fixed_prize_no_multiplier"
    return "observed"


@dataclass(frozen=True, slots=True)
class RawPowerballRow:
    drawing_href: str | None
    visible_date: str | None
    main_values: tuple[str, ...]
    powerball_values: tuple[str, ...]
    multiplier_values: tuple[str, ...]
    double_play_main: tuple[str, ...]
    double_play_powerball: tuple[str, ...]
    jackpot_text: str | None
    unknown_main_items: tuple[str, ...] = ()


class _PowerballHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self._row = None
        self._section_depth = 0
        self._ul = None
        self._li_classes = ()
        self._capture = None
        self._text = []

    @staticmethod
    def _attrs(attrs):
        return dict(attrs)

    def handle_starttag(self, tag, attrs):
        attrs = self._attrs(attrs)
        classes = set(attrs.get("class", "").split())
        if tag == "tr":
            self._row = {"href": None, "date": None, "main": [], "bonus": [], "mult": [], "dp": [], "dp_bonus": [], "jackpot": None, "unknown": [], "main_ul_seen": False}
        if self._row is None:
            return
        if tag == "section" and "results" in classes:
            self._section_depth += 1
        elif tag == "ul" and self._section_depth:
            if "extradraw" in classes:
                self._ul = "double"
            elif self._row["main_ul_seen"]:
                self._ul = "unknown"
            else:
                self._ul = "main"
                self._row["main_ul_seen"] = True
        elif tag == "li" and self._ul:
            self._li_classes = tuple(classes)
            self._capture, self._text = "li", []
        elif tag == "a":
            href = attrs.get("href", "")
            if "/powerball/drawing/" in href:
                self._row["href"] = href
                self._capture, self._text = "date", []
            elif "/powerball/jackpot/" in href:
                self._capture, self._text = "jackpot", []

    def handle_data(self, data):
        if self._capture:
            self._text.append(data)

    def handle_endtag(self, tag):
        if self._row is None:
            return
        if tag in ("li", "a") and self._capture:
            value = " ".join("".join(self._text).split())
            if self._capture == "date": self._row["date"] = value
            elif self._capture == "jackpot": self._row["jackpot"] = value
            elif self._capture == "li":
                if self._ul == "unknown":
                    target = "unknown"
                elif self._ul == "double":
                    target = "dp_bonus" if "bonus" in self._li_classes else "dp"
                elif "bonus" in self._li_classes: target = "bonus"
                elif "multiplier" in self._li_classes: target = "mult"
                elif self._li_classes: target = "unknown"
                else: target = "main"
                self._row[target].append(value)
            self._capture, self._text = None, []
        if tag == "ul": self._ul = None
        elif tag == "section" and self._section_depth: self._section_depth -= 1
        elif tag == "tr":
            r = self._row
            if r["href"] or r["date"]:
                self.rows.append(RawPowerballRow(r["href"], r["date"], tuple(r["main"]), tuple(r["bonus"]), tuple(r["mult"]), tuple(r["dp"]), tuple(r["dp_bonus"]), r["jackpot"], tuple(r["unknown"])))
            self._row = None


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_html(text: str) -> tuple[RawPowerballRow, ...]:
    parser = _PowerballHTMLParser()
    parser.feed(text)
    parser.close()
    return tuple(parser.rows)


def read_html_rows(path: Path) -> tuple[RawPowerballRow, ...]:
    return parse_html(path.read_text(encoding="utf-8"))


def _integers(values, path, issues):
    parsed = []
    for index, value in enumerate(values):
        if re.fullmatch(r"\d+", value): parsed.append(int(value))
        else: issues.append(ValidationIssue("source.invalid_integer", f"{path}[{index}]", "valor não inteiro", value, "integer"))
    return tuple(parsed)


def _jackpot(value, issues):
    if value is None or not value.strip():
        return MonetaryAmount("advertised_jackpot", ValueStatus.UNKNOWN)
    match = re.fullmatch(r"\$([0-9]+(?:\.[0-9]+)?)\s+(Million|Billion)", value.strip())
    if not match:
        issues.append(ValidationIssue("source.invalid_money", "draw.money.advertised_jackpot", "jackpot inválido", value, "$N Million/Billion"))
        return MonetaryAmount("advertised_jackpot", ValueStatus.UNKNOWN, source_text=value)
    try: amount = Decimal(match.group(1)) * (Decimal("1000000") if match.group(2) == "Million" else Decimal("1000000000"))
    except InvalidOperation:
        issues.append(ValidationIssue("source.invalid_money", "draw.money.advertised_jackpot", "jackpot inválido", value))
        return MonetaryAmount("advertised_jackpot", ValueStatus.UNKNOWN, source_text=value)
    return MonetaryAmount("advertised_jackpot", ValueStatus.KNOWN, amount, "USD", value)


def normalize_row(row: RawPowerballRow, provenance: RawProvenance) -> NormalizationResult:
    issues = []
    href_match = re.fullmatch(r"/powerball/drawing/(\d{4})/(\d{1,2})/(\d{1,2})", row.drawing_href or "")
    href_date = None
    if href_match:
        try: href_date = date(*(int(v) for v in href_match.groups()))
        except ValueError: pass
    if href_date is None:
        issues.append(ValidationIssue("source.invalid_reference_date", "draw.external_reference", "URL de sorteio inválida", row.drawing_href))
    visible_date = None
    try: visible_date = datetime.strptime(row.visible_date or "", "%a, %B, %d, %Y").date()
    except ValueError: issues.append(ValidationIssue("source.invalid_date", "draw.draw_date", "data visível inválida", row.visible_date))
    if href_date and visible_date and href_date != visible_date:
        issues.append(ValidationIssue("source.date_mismatch", "draw.draw_date", "URL e texto possuem datas diferentes", row.visible_date, href_date.isoformat()))
    draw_date = href_date or visible_date
    if draw_date is None:
        return NormalizationResult(None, tuple(issues), None)
    rule = POWERBALL.rule_for(draw_date)
    if rule is None:
        issues.append(ValidationIssue("draw.rule_not_found", "draw.draw_date", "não existe regra histórica para a data", draw_date.isoformat()))
        return NormalizationResult(None, tuple(issues), f"powerball:drawing_date:{draw_date.isoformat()}")
    main = _integers(row.main_values, "draw.series.primary.components.main", issues)
    powerball = _integers(row.powerball_values, "draw.series.primary.components.powerball", issues)
    if row.unknown_main_items:
        issues.append(ValidationIssue("source.unknown_result_item", "draw.series.primary", "elementos com classe desconhecida", row.unknown_main_items))
    attrs = []
    power_play_state = _power_play_state(draw_date)
    if row.multiplier_values:
        if len(row.multiplier_values) == 1 and re.fullmatch(r"\d+x", row.multiplier_values[0]):
            attrs.append(ResultAttribute("power_play", int(row.multiplier_values[0][:-1])))
        else: issues.append(ValidationIssue("source.invalid_multiplier", "draw.series.primary.attributes.power_play", "Power Play inválido", row.multiplier_values, "one Nx"))
    if power_play_state == "observed" and not row.multiplier_values:
        issues.append(ValidationIssue("source.missing_multiplier", "draw.series.primary.attributes.power_play", "multiplicador esperado pela regra histórica", None, "one Nx"))
    elif power_play_state != "observed" and row.multiplier_values:
        issues.append(ValidationIssue("source.unexpected_multiplier", "draw.series.primary.attributes.power_play", "multiplicador não se aplica à regra histórica", row.multiplier_values, power_play_state))
    series = [ResultSeries("primary", (ComponentResult("main", main), ComponentResult("powerball", powerball)), tuple(attrs))]
    dp_present = bool(row.double_play_main or row.double_play_powerball)
    double_play_expected = draw_date >= date(2021, 8, 23)
    if double_play_expected and not dp_present:
        issues.append(ValidationIssue("source.missing_double_play", "draw.series.double_play", "Double Play esperado pela vigência histórica"))
    elif dp_present and not double_play_expected:
        issues.append(ValidationIssue("source.unexpected_double_play", "draw.series.double_play", "Double Play anterior ao lançamento", draw_date.isoformat(), "from 2021-08-23"))
    if dp_present:
        series.append(ResultSeries("double_play", (ComponentResult("main", _integers(row.double_play_main, "draw.series.double_play.components.main", issues)), ComponentResult("powerball", _integers(row.double_play_powerball, "draw.series.double_play.components.powerball", issues)))))
    candidate = DrawCandidate("powerball", draw_date, rule.version_label, status=DrawStatus.CANDIDATE,
        series=tuple(series), external_references=(ExternalReference(SOURCE_KEY, "drawing_path", row.drawing_href or draw_date.isoformat()),),
        monetary_amounts=(_jackpot(row.jackpot_text, issues),), provenance=provenance,
        metadata=(("visible_date_source_text", row.visible_date or ""), ("power_play_state", power_play_state)))
    issues.extend(validate_draw(candidate, POWERBALL))
    key = f"powerball:drawing_date:{draw_date.isoformat()}"
    return NormalizationResult(candidate, tuple(issues), key)


def normalize_rows(rows: Iterable[RawPowerballRow], provenance: RawProvenance):
    return tuple(normalize_row(row, provenance) for row in rows)
