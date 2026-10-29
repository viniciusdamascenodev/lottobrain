"""Contratos de domínio independentes de banco e framework web."""

from app.domain.catalog import (
    CollectionReadiness,
    DataSourceDefinition,
    DrawTime,
    ExtensionDefinition,
    ExtensionKind,
    LotteryCatalog,
    LotteryCatalogEntry,
    MarketDefinition,
    ScheduleDefinition,
    SourceAuthority,
)

from app.domain.errors import DomainValidationError, ValidationIssue
from app.domain.models import (
    ComponentDefinition,
    ComponentResult,
    DrawCandidate,
    ExternalReference,
    Lottery,
    LotteryRuleVersion,
    MonetaryAmount,
    PrizeTierResult,
    RawProvenance,
    ResultAttribute,
    ResultSeries,
    ResultSeriesDefinition,
)
from app.domain.types import (
    DrawStatus,
    LotteryStatus,
    OrderSemantics,
    RuleStatus,
    SeriesRole,
    ValueStatus,
    ValueType,
)
from app.domain.validation import assert_valid_draw, validate_draw

__all__ = [
    "CollectionReadiness",
    "ComponentDefinition",
    "ComponentResult",
    "DataSourceDefinition",
    "DomainValidationError",
    "DrawCandidate",
    "DrawStatus",
    "DrawTime",
    "ExternalReference",
    "ExtensionDefinition",
    "ExtensionKind",
    "Lottery",
    "LotteryCatalog",
    "LotteryCatalogEntry",
    "LotteryRuleVersion",
    "LotteryStatus",
    "MonetaryAmount",
    "MarketDefinition",
    "OrderSemantics",
    "PrizeTierResult",
    "RawProvenance",
    "ResultAttribute",
    "ResultSeries",
    "ResultSeriesDefinition",
    "RuleStatus",
    "ScheduleDefinition",
    "SeriesRole",
    "SourceAuthority",
    "ValidationIssue",
    "ValueStatus",
    "ValueType",
    "assert_valid_draw",
    "validate_draw",
]

