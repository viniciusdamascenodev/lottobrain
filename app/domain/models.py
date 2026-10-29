from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.domain.types import (
    DrawStatus,
    LotteryStatus,
    OrderSemantics,
    RuleStatus,
    SeriesRole,
    ValueStatus,
    ValueType,
)


_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
_CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _require_key(value: str, field_name: str) -> None:
    if not _KEY_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} deve usar snake_case ASCII: {value!r}")


def _require_unique_keys(items: tuple, field_name: str) -> None:
    keys = [item.key for item in items]
    if len(keys) != len(set(keys)):
        raise ValueError(f"{field_name} contém chaves duplicadas")


@dataclass(frozen=True, slots=True)
class ComponentDefinition:
    key: str
    label: str
    value_type: ValueType
    min_count: int
    max_count: int
    min_value: int | None = None
    max_value: int | None = None
    unique_values: bool = True
    order_semantics: OrderSemantics = OrderSemantics.SORTED
    position: int = 0

    def __post_init__(self) -> None:
        _require_key(self.key, "component.key")
        if not self.label.strip():
            raise ValueError("component.label é obrigatório")
        if self.min_count < 0 or self.max_count < self.min_count:
            raise ValueError("cardinalidade do componente é inválida")
        if self.value_type is ValueType.INTEGER:
            if self.min_value is None or self.max_value is None:
                raise ValueError("componente inteiro requer limites")
            if self.min_value > self.max_value:
                raise ValueError("limites do componente são inválidos")
        elif self.min_value is not None or self.max_value is not None:
            raise ValueError("componente textual não aceita limites numéricos")
        if self.position < 0:
            raise ValueError("component.position não pode ser negativo")


@dataclass(frozen=True, slots=True)
class ResultSeriesDefinition:
    key: str
    label: str
    role: SeriesRole
    components: tuple[ComponentDefinition, ...]
    required: bool = True

    def __post_init__(self) -> None:
        _require_key(self.key, "series.key")
        if not self.label.strip():
            raise ValueError("series.label é obrigatório")
        if not self.components:
            raise ValueError("série requer ao menos um componente")
        _require_unique_keys(self.components, "series.components")
        positions = [component.position for component in self.components]
        if len(positions) != len(set(positions)):
            raise ValueError("series.components contém posições duplicadas")

    def component(self, key: str) -> ComponentDefinition | None:
        return next((item for item in self.components if item.key == key), None)


@dataclass(frozen=True, slots=True)
class LotteryRuleVersion:
    version_label: str
    valid_from: date
    series: tuple[ResultSeriesDefinition, ...]
    valid_to: date | None = None
    status: RuleStatus = RuleStatus.VALIDATED
    source_reference: str | None = None

    def __post_init__(self) -> None:
        _require_key(self.version_label, "rule.version_label")
        if self.valid_to is not None and self.valid_to <= self.valid_from:
            raise ValueError("rule.valid_to deve ser posterior a valid_from")
        if not self.series:
            raise ValueError("regra requer ao menos uma série")
        _require_unique_keys(self.series, "rule.series")
        primary_count = sum(item.role is SeriesRole.PRIMARY for item in self.series)
        if primary_count != 1:
            raise ValueError("regra requer exatamente uma série principal")

    def applies_on(self, draw_date: date) -> bool:
        return self.valid_from <= draw_date and (
            self.valid_to is None or draw_date < self.valid_to
        )

    def series_definition(self, key: str) -> ResultSeriesDefinition | None:
        return next((item for item in self.series if item.key == key), None)


@dataclass(frozen=True, slots=True)
class Lottery:
    slug: str
    display_name: str
    jurisdiction_code: str
    rules: tuple[LotteryRuleVersion, ...]
    status: LotteryStatus = LotteryStatus.DRAFT
    default_timezone: str | None = None
    default_currency: str | None = None

    def __post_init__(self) -> None:
        _require_key(self.slug, "lottery.slug")
        if not self.display_name.strip() or not self.jurisdiction_code.strip():
            raise ValueError("nome e jurisdição da loteria são obrigatórios")
        if self.default_currency and not _CURRENCY_PATTERN.fullmatch(self.default_currency):
            raise ValueError("moeda deve usar código ISO 4217 em maiúsculas")
        labels = [rule.version_label for rule in self.rules]
        if len(labels) != len(set(labels)):
            raise ValueError("loteria contém versões de regra duplicadas")
        validated = sorted(
            (rule for rule in self.rules if rule.status is RuleStatus.VALIDATED),
            key=lambda rule: rule.valid_from,
        )
        if self.status is LotteryStatus.ACTIVE and not validated:
            raise ValueError("loteria ativa requer ao menos uma regra validada")
        for previous, current in zip(validated, validated[1:]):
            if previous.valid_to is None or current.valid_from < previous.valid_to:
                raise ValueError("versões validadas da regra não podem se sobrepor")

    def rule_for(self, draw_date: date) -> LotteryRuleVersion | None:
        matches = [
            rule
            for rule in self.rules
            if rule.status is RuleStatus.VALIDATED and rule.applies_on(draw_date)
        ]
        return matches[0] if len(matches) == 1 else None


@dataclass(frozen=True, slots=True)
class ComponentResult:
    key: str
    values: tuple[int | str, ...]

    def __post_init__(self) -> None:
        _require_key(self.key, "component_result.key")


@dataclass(frozen=True, slots=True)
class ResultAttribute:
    key: str
    value: int | str | bool | Decimal

    def __post_init__(self) -> None:
        _require_key(self.key, "attribute.key")


@dataclass(frozen=True, slots=True)
class ResultSeries:
    key: str
    components: tuple[ComponentResult, ...]
    attributes: tuple[ResultAttribute, ...] = ()

    def __post_init__(self) -> None:
        _require_key(self.key, "result_series.key")
        _require_unique_keys(self.components, "result_series.components")
        _require_unique_keys(self.attributes, "result_series.attributes")


@dataclass(frozen=True, slots=True)
class MonetaryAmount:
    kind: str
    status: ValueStatus
    amount: Decimal | None = None
    currency: str | None = None
    source_text: str | None = None

    def __post_init__(self) -> None:
        _require_key(self.kind, "money.kind")
        if self.status is ValueStatus.KNOWN:
            if self.amount is None or self.currency is None:
                raise ValueError("montante conhecido requer valor e moeda")
            if not _CURRENCY_PATTERN.fullmatch(self.currency):
                raise ValueError("moeda deve usar código ISO 4217 em maiúsculas")
            if self.amount < 0:
                raise ValueError("montante não pode ser negativo")
        elif self.amount is not None or self.currency is not None:
            raise ValueError("montante não conhecido não aceita valor ou moeda normalizados")


@dataclass(frozen=True, slots=True)
class PrizeTierResult:
    tier_key: str
    status: ValueStatus
    winners: int | None = None
    prize_per_winner: MonetaryAmount | None = None

    def __post_init__(self) -> None:
        _require_key(self.tier_key, "prize_tier.key")
        if self.winners is not None and self.winners < 0:
            raise ValueError("quantidade de ganhadores não pode ser negativa")
        if self.status is ValueStatus.KNOWN and self.winners is None:
            raise ValueError("faixa conhecida requer quantidade de ganhadores")


@dataclass(frozen=True, slots=True)
class ExternalReference:
    source_key: str
    namespace: str
    value: str

    def __post_init__(self) -> None:
        _require_key(self.source_key, "external_reference.source_key")
        _require_key(self.namespace, "external_reference.namespace")
        if not self.value.strip():
            raise ValueError("external_reference.value é obrigatório")


@dataclass(frozen=True, slots=True)
class RawProvenance:
    source_key: str
    raw_sha256: str
    captured_at: datetime
    adapter_version: str

    def __post_init__(self) -> None:
        _require_key(self.source_key, "provenance.source_key")
        if not _SHA256_PATTERN.fullmatch(self.raw_sha256):
            raise ValueError("raw_sha256 deve ser hexadecimal SHA-256 em minúsculas")
        if self.captured_at.tzinfo is None:
            raise ValueError("captured_at deve possuir timezone")
        if not self.adapter_version.strip():
            raise ValueError("adapter_version é obrigatório")


@dataclass(frozen=True, slots=True)
class DrawCandidate:
    lottery_slug: str
    draw_date: date
    rule_version_label: str
    series: tuple[ResultSeries, ...]
    official_draw_number: str | None = None
    status: DrawStatus = DrawStatus.CANDIDATE
    external_references: tuple[ExternalReference, ...] = ()
    monetary_amounts: tuple[MonetaryAmount, ...] = ()
    prize_tiers: tuple[PrizeTierResult, ...] = ()
    provenance: RawProvenance | None = None
    metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        _require_key(self.lottery_slug, "draw.lottery_slug")
        _require_key(self.rule_version_label, "draw.rule_version_label")
        _require_unique_keys(self.series, "draw.series")
        if self.official_draw_number is not None and not self.official_draw_number.strip():
            raise ValueError("official_draw_number não pode ser vazio")
        reference_keys = [
            (reference.source_key, reference.namespace, reference.value)
            for reference in self.external_references
        ]
        if len(reference_keys) != len(set(reference_keys)):
            raise ValueError("draw.external_references contém duplicidade")
        metadata_keys = [key for key, _ in self.metadata]
        if len(metadata_keys) != len(set(metadata_keys)):
            raise ValueError("draw.metadata contém chaves duplicadas")
