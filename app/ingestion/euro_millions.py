"""Contrato conservador para o JSON histórico do EuroMillions."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Iterable

from app.domain import (
    ComponentDefinition, ComponentResult, DrawCandidate, DrawStatus, ExternalReference,
    Lottery, LotteryRuleVersion, LotteryStatus, MonetaryAmount, OrderSemantics,
    RawProvenance, ResultAttribute, ResultSeries, ResultSeriesDefinition, SeriesRole,
    ValidationIssue, ValueStatus, ValueType, validate_draw,
)
from app.ingestion.lotofacil import NormalizationResult

SOURCE_KEY = "pedromealha_euromillions_api_json"
NORMALIZER_VERSION = "spec-0016"
EXPECTED_FIELDS = frozenset({"date", "draw_id", "has_winner", "id", "numbers", "prize", "stars"})


def _series(stars_max: int):
    return (ResultSeriesDefinition("primary", "Resultado principal", SeriesRole.PRIMARY, (
        ComponentDefinition("main", "Números", ValueType.INTEGER, 5, 5, 1, 50, True, OrderSemantics.SORTED),
        ComponentDefinition("stars", "Estrelas", ValueType.INTEGER, 2, 2, 1, stars_max, True, OrderSemantics.SORTED, 1),
    )),)


RULES = (
    LotteryRuleVersion("em_2004_50x9", date(2004, 2, 13), _series(9), date(2011, 5, 7), source_reference="SPEC-0015"),
    LotteryRuleVersion("em_2011_50x11", date(2011, 5, 10), _series(11), date(2016, 9, 24), source_reference="SPEC-0015"),
    LotteryRuleVersion("em_2016_50x12", date(2016, 9, 27), _series(12), source_reference="SPEC-0015"),
)
EURO_MILLIONS = Lottery(
    slug="euro_millions", display_name="EuroMillions", jurisdiction_code="EU",
    default_timezone="Europe/Paris", default_currency="EUR", status=LotteryStatus.ACTIVE,
    rules=RULES,
)


@dataclass(frozen=True, slots=True)
class RawEuroMillionsRow:
    date_value: object
    draw_id: object
    has_winner: object
    source_id: object
    numbers: object
    prize: object
    stars: object
    extra_fields: tuple[str, ...] = ()
    missing_fields: tuple[str, ...] = ()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_json(text: str) -> tuple[RawEuroMillionsRow, ...]:
    payload = json.loads(text, parse_float=Decimal)
    if not isinstance(payload, list):
        raise ValueError("fonte EuroMillions deve ser uma lista JSON")
    rows = []
    for position, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"item {position} deve ser objeto JSON")
        keys = set(item)
        rows.append(RawEuroMillionsRow(
            item.get("date"), item.get("draw_id"), item.get("has_winner"), item.get("id"),
            item.get("numbers"), item.get("prize"), item.get("stars"),
            tuple(sorted(keys - EXPECTED_FIELDS)), tuple(sorted(EXPECTED_FIELDS - keys)),
        ))
    return tuple(rows)


def read_json_rows(path: Path) -> tuple[RawEuroMillionsRow, ...]:
    return parse_json(path.read_text(encoding="utf-8"))


def _integers(value, path, issues):
    if not isinstance(value, list):
        issues.append(ValidationIssue("source.invalid_collection", path, "campo deve ser uma lista", value, "array of integer strings"))
        return ()
    parsed = []
    for index, item in enumerate(value):
        if isinstance(item, str) and re.fullmatch(r"\d+", item):
            parsed.append(int(item))
        else:
            issues.append(ValidationIssue("source.invalid_integer", f"{path}[{index}]", "valor deve ser string inteira", item, "integer string"))
    return tuple(parsed)


def _positive_identifier(value, field, issues):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        issues.append(ValidationIssue("source.invalid_identifier", f"draw.external_reference.{field}", "identificador deve ser inteiro positivo", value))
        return None
    return str(value)


def normalize_row(row: RawEuroMillionsRow, provenance: RawProvenance) -> NormalizationResult:
    issues = []
    if row.extra_fields or row.missing_fields:
        issues.append(ValidationIssue("source.invalid_structure", "draw", "campos JSON inesperados ou ausentes", {"extra": row.extra_fields, "missing": row.missing_fields}))
    draw_date = None
    if isinstance(row.date_value, str):
        try:
            parsed = datetime.strptime(row.date_value, "%a, %d %b %Y %H:%M:%S GMT").replace(tzinfo=timezone.utc)
            draw_date = parsed.date()
            if parsed.time().isoformat() != "00:00:00":
                issues.append(ValidationIssue("source.unverified_time", "draw.draw_date", "horário não zero exige semântica pesquisada", row.date_value, "00:00:00 GMT"))
        except ValueError:
            pass
    if draw_date is None:
        issues.append(ValidationIssue("source.invalid_date", "draw.draw_date", "data inválida", row.date_value, "RFC-like GMT date"))
        return NormalizationResult(None, tuple(issues), None)
    rule = EURO_MILLIONS.rule_for(draw_date)
    if rule is None:
        issues.append(ValidationIssue("draw.rule_not_found", "draw.draw_date", "não existe regra histórica para a data", draw_date.isoformat()))
        return NormalizationResult(None, tuple(issues), f"euro_millions:drawing_date:{draw_date.isoformat()}")

    source_id = _positive_identifier(row.source_id, "source_id", issues)
    draw_id = _positive_identifier(row.draw_id, "draw_id", issues)
    main = _integers(row.numbers, "draw.series.primary.components.main", issues)
    stars = _integers(row.stars, "draw.series.primary.components.stars", issues)
    attributes = []
    if type(row.has_winner) is bool:
        attributes.append(ResultAttribute("has_jackpot_winner", row.has_winner))
    else:
        issues.append(ValidationIssue("source.invalid_boolean", "draw.series.primary.attributes.has_winner", "has_winner deve ser booleano", row.has_winner))

    if isinstance(row.prize, bool) or not isinstance(row.prize, (int, Decimal)) or not Decimal(row.prize).is_finite() or Decimal(row.prize) < 0:
        issues.append(ValidationIssue("source.invalid_money", "draw.money.reported_prize", "prêmio deve ser número finito não negativo", row.prize))
        prize_text = None if row.prize is None else str(row.prize)
        prize_amount = MonetaryAmount("top_tier_prize_per_winner", ValueStatus.UNKNOWN, source_text=prize_text)
    else:
        prize_text = str(row.prize)
        value = Decimal(row.prize)
        prize_amount = (
            MonetaryAmount("top_tier_prize_per_winner", ValueStatus.KNOWN, value, "EUR", prize_text)
            if value > 0 else
            MonetaryAmount("top_tier_prize_per_winner", ValueStatus.UNKNOWN, source_text=prize_text)
        )
    references = []
    if source_id is not None:
        references.append(ExternalReference(SOURCE_KEY, "source_id", source_id))
    if draw_id is not None:
        references.append(ExternalReference(SOURCE_KEY, "draw_id", draw_id))
    candidate = DrawCandidate(
        "euro_millions", draw_date, rule.version_label, status=DrawStatus.CANDIDATE,
        series=(ResultSeries("primary", (ComponentResult("main", main), ComponentResult("stars", stars)), tuple(attributes)),),
        external_references=tuple(references),
        monetary_amounts=(prize_amount,),
        provenance=provenance,
        metadata=(
            ("date_source_text", str(row.date_value)),
            ("prize_scope", "top_tier_5_plus_2_per_winner"),
            ("prize_source_jurisdiction", "PT_or_ES"),
        ),
    )
    issues.extend(validate_draw(candidate, EURO_MILLIONS))
    return NormalizationResult(candidate, tuple(issues), f"euro_millions:drawing_date:{draw_date.isoformat()}")


def normalize_rows(rows: Iterable[RawEuroMillionsRow], provenance: RawProvenance):
    return tuple(normalize_row(row, provenance) for row in rows)
