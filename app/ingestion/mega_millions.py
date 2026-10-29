"""Contrato conservador para o HTML histórico da Mega Millions."""
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

SOURCE_KEY = "usamega_mega_millions_html"
NORMALIZER_VERSION = "spec-0013"


def _series(main_max: int, mega_ball_max: int):
    return (ResultSeriesDefinition("primary", "Resultado principal", SeriesRole.PRIMARY, (
        ComponentDefinition("main", "Números", ValueType.INTEGER, 5, 5, 1, main_max, True, OrderSemantics.SORTED),
        ComponentDefinition("mega_ball", "Mega Ball", ValueType.INTEGER, 1, 1, 1, mega_ball_max, True, OrderSemantics.NONE, 1),
    )),)


RULES = (
    LotteryRuleVersion("mm_1996_50x25", date(1996, 9, 6), _series(50, 25), date(1999, 1, 13), source_reference="SPEC-0012"),
    LotteryRuleVersion("mm_1999_50x36", date(1999, 1, 15), _series(50, 36), date(2002, 5, 15), source_reference="SPEC-0012"),
    LotteryRuleVersion("mm_2002_52x52", date(2002, 5, 17), _series(52, 52), date(2005, 6, 22), source_reference="SPEC-0012"),
    LotteryRuleVersion("mm_2005_56x46", date(2005, 6, 24), _series(56, 46), date(2013, 10, 19), source_reference="SPEC-0012"),
    LotteryRuleVersion("mm_2013_75x15", date(2013, 10, 22), _series(75, 15), date(2017, 10, 28), source_reference="SPEC-0012"),
    LotteryRuleVersion("mm_2017_70x25", date(2017, 10, 31), _series(70, 25), date(2025, 4, 5), source_reference="SPEC-0012"),
    LotteryRuleVersion("mm_2025_70x24", date(2025, 4, 8), _series(70, 24), source_reference="SPEC-0012"),
)
MEGA_MILLIONS = Lottery(
    slug="mega_millions", display_name="Mega Millions", jurisdiction_code="US",
    default_timezone="America/New_York", default_currency="USD", status=LotteryStatus.ACTIVE,
    rules=RULES,
)


def _multiplier_state(draw_date: date) -> str:
    if draw_date < date(2003, 12, 5):
        return "not_applicable"
    if draw_date <= date(2025, 4, 4):
        return "drawn_optional_megaplier"
    return "ticket_assigned_multiplier"


@dataclass(frozen=True, slots=True)
class RawMegaMillionsRow:
    drawing_href: str | None
    visible_date: str | None
    main_values: tuple[str, ...]
    mega_ball_values: tuple[str, ...]
    multiplier_values: tuple[str, ...]
    jackpot_text: str | None
    unknown_result_items: tuple[str, ...] = ()
    unknown_result_blocks: int = 0


class _MegaMillionsHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self._row = None
        self._section_depth = 0
        self._ul = None
        self._li_classes = ()
        self._capture = None
        self._text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set(attrs.get("class", "").split())
        if tag == "tr":
            self._row = {"href": None, "date": None, "main": [], "bonus": [], "mult": [], "jackpot": None, "unknown": [], "ul_count": 0}
        if self._row is None:
            return
        if tag == "section" and "results" in classes:
            self._section_depth += 1
        elif tag == "ul" and self._section_depth:
            self._row["ul_count"] += 1
            self._ul = "main" if self._row["ul_count"] == 1 else "unknown"
        elif tag == "li" and self._ul:
            self._li_classes = tuple(classes)
            self._capture, self._text = "li", []
        elif tag == "a":
            href = attrs.get("href", "")
            if "/mega-millions/drawing/" in href:
                self._row["href"] = href
                self._capture, self._text = "date", []
            elif "/mega-millions/jackpot/" in href:
                self._capture, self._text = "jackpot", []

    def handle_data(self, data):
        if self._capture:
            self._text.append(data)

    def handle_endtag(self, tag):
        if self._row is None:
            return
        if tag in ("li", "a") and self._capture:
            value = " ".join("".join(self._text).split())
            if self._capture == "date":
                self._row["date"] = value
            elif self._capture == "jackpot":
                self._row["jackpot"] = value
            elif self._capture == "li":
                if self._ul == "unknown": target = "unknown"
                elif "bonus" in self._li_classes: target = "bonus"
                elif "multiplier" in self._li_classes: target = "mult"
                elif self._li_classes: target = "unknown"
                else: target = "main"
                self._row[target].append(value)
            self._capture, self._text = None, []
        if tag == "ul":
            self._ul = None
        elif tag == "section" and self._section_depth:
            self._section_depth -= 1
        elif tag == "tr":
            row = self._row
            if row["href"] or row["date"]:
                self.rows.append(RawMegaMillionsRow(
                    row["href"], row["date"], tuple(row["main"]), tuple(row["bonus"]),
                    tuple(row["mult"]), row["jackpot"], tuple(row["unknown"]),
                    max(0, row["ul_count"] - 1),
                ))
            self._row = None


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_html(text: str) -> tuple[RawMegaMillionsRow, ...]:
    parser = _MegaMillionsHTMLParser()
    parser.feed(text)
    parser.close()
    return tuple(parser.rows)


def read_html_rows(path: Path) -> tuple[RawMegaMillionsRow, ...]:
    return parse_html(path.read_text(encoding="utf-8"))


def _integers(values, path, issues):
    parsed = []
    for index, value in enumerate(values):
        if re.fullmatch(r"\d+", value):
            parsed.append(int(value))
        else:
            issues.append(ValidationIssue("source.invalid_integer", f"{path}[{index}]", "valor não inteiro", value, "integer"))
    return tuple(parsed)


def _jackpot(value, issues):
    if value is None or not value.strip():
        return MonetaryAmount("advertised_jackpot", ValueStatus.UNKNOWN)
    match = re.fullmatch(r"\$([0-9]+(?:\.[0-9]+)?)\s+(Million|Billion)", value.strip())
    if not match:
        issues.append(ValidationIssue("source.invalid_money", "draw.money.advertised_jackpot", "jackpot inválido", value, "$N Million/Billion"))
        return MonetaryAmount("advertised_jackpot", ValueStatus.UNKNOWN, source_text=value)
    try:
        amount = Decimal(match.group(1)) * (Decimal("1000000") if match.group(2) == "Million" else Decimal("1000000000"))
    except InvalidOperation:
        issues.append(ValidationIssue("source.invalid_money", "draw.money.advertised_jackpot", "jackpot inválido", value))
        return MonetaryAmount("advertised_jackpot", ValueStatus.UNKNOWN, source_text=value)
    return MonetaryAmount("advertised_jackpot", ValueStatus.KNOWN, amount, "USD", value)


def normalize_row(row: RawMegaMillionsRow, provenance: RawProvenance) -> NormalizationResult:
    issues = []
    href_match = re.fullmatch(r"/mega-millions/drawing/(\d{4})/(\d{1,2})/(\d{1,2})", row.drawing_href or "")
    href_date = None
    if href_match:
        try:
            href_date = date(*(int(value) for value in href_match.groups()))
        except ValueError:
            pass
    if href_date is None:
        issues.append(ValidationIssue("source.invalid_reference_date", "draw.external_reference", "URL de sorteio inválida", row.drawing_href))
    visible_date = None
    try:
        visible_date = datetime.strptime(row.visible_date or "", "%a, %B, %d, %Y").date()
    except ValueError:
        issues.append(ValidationIssue("source.invalid_date", "draw.draw_date", "data visível inválida", row.visible_date))
    if href_date and visible_date and href_date != visible_date:
        issues.append(ValidationIssue("source.date_mismatch", "draw.draw_date", "URL e texto possuem datas diferentes", row.visible_date, href_date.isoformat()))
    draw_date = href_date or visible_date
    if draw_date is None:
        return NormalizationResult(None, tuple(issues), None)
    rule = MEGA_MILLIONS.rule_for(draw_date)
    if rule is None:
        issues.append(ValidationIssue("draw.rule_not_found", "draw.draw_date", "não existe regra histórica para a data", draw_date.isoformat()))
        return NormalizationResult(None, tuple(issues), f"mega_millions:drawing_date:{draw_date.isoformat()}")

    main = _integers(row.main_values, "draw.series.primary.components.main", issues)
    mega_ball = _integers(row.mega_ball_values, "draw.series.primary.components.mega_ball", issues)
    if row.unknown_result_items or row.unknown_result_blocks:
        issues.append(ValidationIssue("source.unknown_result_structure", "draw.series.primary", "estrutura de resultado desconhecida", {"items": row.unknown_result_items, "blocks": row.unknown_result_blocks}))
    attributes = []
    multiplier_state = _multiplier_state(draw_date)
    if row.multiplier_values:
        if len(row.multiplier_values) == 1 and re.fullmatch(r"\d+x", row.multiplier_values[0]):
            attributes.append(ResultAttribute("megaplier", int(row.multiplier_values[0][:-1])))
        else:
            issues.append(ValidationIssue("source.invalid_multiplier", "draw.series.primary.attributes.megaplier", "Megaplier inválido", row.multiplier_values, "one Nx"))
    if multiplier_state == "drawn_optional_megaplier" and not row.multiplier_values:
        issues.append(ValidationIssue("source.missing_multiplier", "draw.series.primary.attributes.megaplier", "Megaplier esperado pela vigência histórica", None, "one Nx"))
    elif multiplier_state != "drawn_optional_megaplier" and row.multiplier_values:
        issues.append(ValidationIssue("source.unexpected_multiplier", "draw.series.primary.attributes.megaplier", "multiplicador não pertence ao resultado nesta vigência", row.multiplier_values, multiplier_state))
    candidate = DrawCandidate(
        "mega_millions", draw_date, rule.version_label, status=DrawStatus.CANDIDATE,
        series=(ResultSeries("primary", (ComponentResult("main", main), ComponentResult("mega_ball", mega_ball)), tuple(attributes)),),
        external_references=(ExternalReference(SOURCE_KEY, "drawing_path", row.drawing_href or draw_date.isoformat()),),
        monetary_amounts=(_jackpot(row.jackpot_text, issues),), provenance=provenance,
        metadata=(("visible_date_source_text", row.visible_date or ""), ("multiplier_state", multiplier_state)),
    )
    issues.extend(validate_draw(candidate, MEGA_MILLIONS))
    return NormalizationResult(candidate, tuple(issues), f"mega_millions:drawing_date:{draw_date.isoformat()}")


def normalize_rows(rows: Iterable[RawMegaMillionsRow], provenance: RawProvenance):
    return tuple(normalize_row(row, provenance) for row in rows)
