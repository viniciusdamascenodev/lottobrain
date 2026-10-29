"""Adaptador específico da exportação XLSX da +Milionária."""
from __future__ import annotations

from datetime import date
import re
from pathlib import Path
from typing import Iterable, Mapping

from app.domain import (
    ComponentDefinition, ComponentResult, DrawCandidate, DrawStatus, ExternalReference,
    Lottery, LotteryRuleVersion, LotteryStatus, MonetaryAmount, OrderSemantics,
    PrizeTierResult, RawProvenance, ResultAttribute, ResultSeries,
    ResultSeriesDefinition, SeriesRole, ValidationIssue, ValueStatus, ValueType, validate_draw,
)
from app.ingestion.lotofacil import (
    NormalizationResult, file_sha256, _header_key, _is_missing, _lookup,
    _parse_date, _parse_integer, _parse_money,
)

SOURCE_KEY = "caixa_mais_milionaria_xlsx"
RULE_VERSION = "baseline_2022"
# Sufixos normalizados realmente presentes na exportação; as duas faixas
# superiores com 0/1 trevo são agregadas pela fonte, não faixas inventadas.
TIERS = (
    ("hits_6_clovers_2", "6acertos2trevos", "6numeros2trevos"),
    ("hits_6_clovers_0_or_1", "6acertos1ounenhumtrevo", "6acertos1ounenhumtrevo"),
    ("hits_5_clovers_2", "5acertos2trevos", "5acertos2trevos"),
    ("hits_5_clovers_0_or_1", "5acertos1ounenhumtrevo", "5acertos1ounenhumtrevo"),
    ("hits_4_clovers_2", "4acertos2trevos", "4acertos2trevos"),
    ("hits_4_clovers_0_or_1", "4acertos1ounenhumtrevo", "4acertos1ounenhumtrevo"),
    ("hits_3_clovers_2", "3acertos2trevos", "3acertos2trevos"),
    ("hits_3_clovers_1", "3acertos1trevo", "3acertos1trevo"),
    ("hits_2_clovers_2", "2acertos2trevos", "2acertos2trevos"),
    ("hits_2_clovers_1", "2acertos1trevo", "2acertos1trevo"),
)
MAIS_MILIONARIA = Lottery(
    slug="mais_milionaria", display_name="+Milionária", jurisdiction_code="BR",
    default_timezone="America/Sao_Paulo", default_currency="BRL", status=LotteryStatus.ACTIVE,
    rules=(LotteryRuleVersion(
        version_label=RULE_VERSION, valid_from=date(2022, 5, 28),
        source_reference="SPEC-0001: limites observados, sem certificação oficial histórica",
        series=(ResultSeriesDefinition(
            key="primary", label="Resultado principal", role=SeriesRole.PRIMARY,
            components=(
                ComponentDefinition(key="main", label="Números", value_type=ValueType.INTEGER,
                                    min_count=6, max_count=6, min_value=1, max_value=50,
                                    unique_values=True, order_semantics=OrderSemantics.SORTED),
                ComponentDefinition(key="clovers", label="Trevos", value_type=ValueType.INTEGER,
                                    min_count=2, max_count=2, min_value=1, max_value=6,
                                    unique_values=True, order_semantics=OrderSemantics.NONE,
                                    position=1),
            ),
        ),),
    ),),
)


def iter_xlsx_rows(path: Path, *, limit: int | None = None):
    from openpyxl import load_workbook
    if limit is not None and limit < 0:
        raise ValueError("limit não pode ser negativo")
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        worksheet = workbook.worksheets[0]
        worksheet.reset_dimensions()
        rows = worksheet.iter_rows(values_only=True)
        headers = tuple(str(v).strip() if v is not None else "" for v in next(rows, ()))
        keys = tuple(_header_key(v) for v in headers)
        required = {"concurso", "datasorteio", *(f"bola{i}" for i in range(1, 7)), "trevo1", "trevo2"}
        required.update("ganhadores" + winners for _, _, winners in TIERS)
        required.update("rateio" + prize for _, prize, _ in TIERS)
        if not headers or len(set(keys)) != len(keys) or required - set(keys):
            raise ValueError("cabeçalhos essenciais ausentes ou nomes repetidos")
        produced = 0
        for values in rows:
            if limit is not None and produced >= limit:
                break
            if not any(v is not None for v in values):
                continue
            produced += 1
            if len(values) != len(headers):
                raise ValueError(f"estrutura incompatível no registro {produced}")
            yield dict(zip(headers, values))
    finally:
        workbook.close()


def _nonnegative_integer(value, path, issues, *, positive=False):
    parsed = _parse_integer(value, path, issues)
    if parsed is not None and parsed < (1 if positive else 0):
        issues.append(ValidationIssue("source.invalid_count", path, "inteiro fora do limite", parsed, ">=1" if positive else ">=0"))
        return None
    return parsed


def _money(value, kind, path, issues):
    try:
        return _parse_money(value, kind, path, issues)
    except ValueError:
        issues.append(ValidationIssue("source.invalid_money", path, "montante negativo", str(value), ">=0"))
        return MonetaryAmount(kind=kind, status=ValueStatus.UNKNOWN, source_text=str(value))


def normalize_row(row: Mapping[str, object], provenance: RawProvenance) -> NormalizationResult:
    indexed = {_header_key(str(k)): v for k, v in row.items()}
    issues = []
    if len(indexed) != len(row):
        return NormalizationResult(None, (ValidationIssue("source.duplicate_header", "headers", "nomes normalizados repetidos"),), None)
    allowed_numbers = {*(f"bola{i}" for i in range(1, 7)), "trevo1", "trevo2"}
    for key in indexed:
        if re.fullmatch(r"(?:bola|trevo)\d+", key) and key not in allowed_numbers:
            issues.append(ValidationIssue("source.unexpected_number_field", key, "coluna de número excedente", key, sorted(allowed_numbers)))
    number = _nonnegative_integer(_lookup(indexed, "concurso"), "draw.official_draw_number", issues, positive=True)
    draw_date = _parse_date(_lookup(indexed, "datasorteio", "datadosorteio"), "draw.draw_date", issues)
    components = []
    for key, prefix, count in (("main", "bola", 6), ("clovers", "trevo", 2)):
        values = []
        for i in range(1, count + 1):
            parsed = _parse_integer(_lookup(indexed, f"{prefix}{i}"), f"draw.series.primary.components.{key}[{i-1}]", issues)
            if parsed is not None:
                values.append(parsed)
        components.append(ComponentResult(key, tuple(values)))
    if number is None or draw_date is None:
        return NormalizationResult(None, tuple(issues), None)
    tiers = []
    for key, prize_suffix, winner_suffix in TIERS:
        winners = _nonnegative_integer(_lookup(indexed, "ganhadores" + winner_suffix), f"draw.prize_tiers.{key}.winners", issues)
        prize = _money(_lookup(indexed, "rateio" + prize_suffix), "paid_per_winner", f"draw.prize_tiers.{key}.prize_per_winner", issues)
        tiers.append(PrizeTierResult(key, ValueStatus.KNOWN if winners is not None else ValueStatus.UNKNOWN, winners, prize))
    money = tuple(_money(_lookup(indexed, *aliases), kind, f"draw.money.{kind}", issues)
                  for kind, aliases in (("sales_total", ("arrecadacaototal", "arrecadaototal")),
                                        ("next_estimated_jackpot", ("estimativapremio", "estimativaprmio"))))
    metadata = []
    for key, aliases in (("winner_locations_source_text", ("cidadeuf",)),
                         ("observation_source_text", ("observacao", "observao")),
                         ("rollover_flag_source_text", ("acumulado6acertos2trevos",))):
        value = _lookup(indexed, *aliases)
        if not _is_missing(value):
            metadata.append((key, str(value).strip()))
    raw_flag = _lookup(indexed, "acumulado6acertos2trevos")
    attributes = ()
    if not _is_missing(raw_flag):
        flag_key = _header_key(str(raw_flag))
        if flag_key in ("sim", "nao"):
            attributes = (ResultAttribute("rolled_over", flag_key == "sim"),)
        else:
            issues.append(ValidationIssue("source.invalid_category", "draw.series.primary.attributes.rolled_over", "categoria desconhecida", raw_flag, "Sim/Não"))
    candidate = DrawCandidate(
        lottery_slug=MAIS_MILIONARIA.slug, draw_date=draw_date, rule_version_label=RULE_VERSION,
        official_draw_number=str(number), status=DrawStatus.CANDIDATE,
        series=(ResultSeries("primary", tuple(components), attributes),),
        external_references=(ExternalReference(SOURCE_KEY, "official_draw_number", str(number)),),
        monetary_amounts=money, prize_tiers=tuple(tiers), provenance=provenance, metadata=tuple(metadata),
    )
    issues.extend(validate_draw(candidate, MAIS_MILIONARIA))
    return NormalizationResult(candidate, tuple(issues), f"mais_milionaria:official_draw_number:{number}")


def normalize_rows(rows: Iterable[Mapping[str, object]], provenance: RawProvenance):
    return tuple(normalize_row(row, provenance) for row in rows)
