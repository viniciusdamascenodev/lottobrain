from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, time
from enum import Enum
from urllib.parse import urlparse

from app.domain.models import Lottery, _require_key


_TIMEZONE_PATTERN = re.compile(r"^[A-Za-z_]+(?:/[A-Za-z0-9_+\-]+)+$")


class SourceAuthority(str, Enum):
    OFFICIAL = "official"
    SECONDARY = "secondary"
    MANUAL = "manual"


class CollectionReadiness(str, Enum):
    RESEARCH_REQUIRED = "research_required"
    CONTRACT_OBSERVED = "contract_observed"
    APPROVED = "approved"
    DISABLED = "disabled"


class ExtensionKind(str, Enum):
    BET_FEATURE = "bet_feature"
    LINKED_DRAW = "linked_draw"
    NATIONAL_RAFFLE = "national_raffle"
    SPECIAL_DRAW = "special_draw"


@dataclass(frozen=True, slots=True)
class DrawTime:
    weekday: int
    local_time: time

    def __post_init__(self) -> None:
        if not 0 <= self.weekday <= 6:
            raise ValueError("weekday deve estar entre 0 (segunda) e 6 (domingo)")
        if self.local_time.tzinfo is not None:
            raise ValueError("local_time deve ser hora civil sem timezone embutido")


@dataclass(frozen=True, slots=True)
class ScheduleDefinition:
    key: str
    timezone: str
    draw_times: tuple[DrawTime, ...]
    observed_at: date
    source_url: str
    valid_from: date | None = None
    valid_to: date | None = None

    def __post_init__(self) -> None:
        _require_key(self.key, "schedule.key")
        if not _TIMEZONE_PATTERN.fullmatch(self.timezone):
            raise ValueError("schedule.timezone deve usar nome IANA")
        if not self.draw_times or len(self.draw_times) != len(set(self.draw_times)):
            raise ValueError("schedule.draw_times deve ser não vazio e sem duplicidade")
        if self.valid_to is not None and (
            self.valid_from is None or self.valid_to <= self.valid_from
        ):
            raise ValueError("schedule.valid_to requer início anterior")
        _require_http_url(self.source_url, "schedule.source_url")


@dataclass(frozen=True, slots=True)
class DataSourceDefinition:
    key: str
    name: str
    authority: SourceAuthority
    purposes: tuple[str, ...]
    data_format: str
    url: str
    readiness: CollectionReadiness

    def __post_init__(self) -> None:
        _require_key(self.key, "source.key")
        if not self.name.strip() or not self.data_format.strip():
            raise ValueError("source.name e source.data_format são obrigatórios")
        if not self.purposes or any(not item.strip() for item in self.purposes):
            raise ValueError("source.purposes deve ser não vazio")
        if len(self.purposes) != len(set(self.purposes)):
            raise ValueError("source.purposes contém duplicidade")
        _require_http_url(self.url, "source.url")


@dataclass(frozen=True, slots=True)
class MarketDefinition:
    jurisdiction_code: str
    currency: str
    role: str = "primary"

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{1,31}", self.jurisdiction_code):
            raise ValueError("market.jurisdiction_code inválido")
        if not re.fullmatch(r"[A-Z]{3}", self.currency):
            raise ValueError("market.currency deve usar ISO 4217")
        _require_key(self.role, "market.role")


@dataclass(frozen=True, slots=True)
class ExtensionDefinition:
    key: str
    label: str
    kind: ExtensionKind
    jurisdictions: tuple[str, ...]
    valid_from: date | None = None

    def __post_init__(self) -> None:
        _require_key(self.key, "extension.key")
        if not self.label.strip() or not self.jurisdictions:
            raise ValueError("extension requer rótulo e jurisdição")
        if len(self.jurisdictions) != len(set(self.jurisdictions)):
            raise ValueError("extension.jurisdictions contém duplicidade")


@dataclass(frozen=True, slots=True)
class LotteryCatalogEntry:
    lottery: Lottery
    markets: tuple[MarketDefinition, ...]
    sources: tuple[DataSourceDefinition, ...]
    schedules: tuple[ScheduleDefinition, ...] = ()
    extensions: tuple[ExtensionDefinition, ...] = ()
    capabilities: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.markets:
            raise ValueError("entrada de catálogo requer ao menos um mercado")
        if not self.sources:
            raise ValueError("entrada de catálogo requer ao menos uma fonte")
        _require_unique(self.sources, "key", "catalog.sources")
        _require_unique(self.schedules, "key", "catalog.schedules")
        _require_unique(self.extensions, "key", "catalog.extensions")
        if len(self.markets) != len(
            {(item.jurisdiction_code, item.currency, item.role) for item in self.markets}
        ):
            raise ValueError("catalog.markets contém duplicidade")
        for capability in self.capabilities:
            _require_key(capability, "catalog.capability")
        if len(self.capabilities) != len(set(self.capabilities)):
            raise ValueError("catalog.capabilities contém duplicidade")
        market_codes = {market.jurisdiction_code for market in self.markets}
        for extension in self.extensions:
            unknown = set(extension.jurisdictions) - market_codes
            if unknown:
                raise ValueError(f"extensão referencia mercados ausentes: {sorted(unknown)}")


@dataclass(frozen=True, slots=True)
class LotteryCatalog:
    entries: tuple[LotteryCatalogEntry, ...]

    def __post_init__(self) -> None:
        slugs = [entry.lottery.slug for entry in self.entries]
        if len(slugs) != len(set(slugs)):
            raise ValueError("catálogo contém slugs duplicados")

    def get(self, slug: str) -> LotteryCatalogEntry | None:
        return next((entry for entry in self.entries if entry.lottery.slug == slug), None)

    def register(self, entry: LotteryCatalogEntry) -> LotteryCatalog:
        if self.get(entry.lottery.slug) is not None:
            raise ValueError(f"loteria já cadastrada: {entry.lottery.slug}")
        return LotteryCatalog((*self.entries, entry))


def _require_unique(items: tuple, attribute: str, field_name: str) -> None:
    values = [getattr(item, attribute) for item in items]
    if len(values) != len(set(values)):
        raise ValueError(f"{field_name} contém chaves duplicadas")


def _require_http_url(value: str, field_name: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{field_name} deve ser URL HTTP(S) absoluta")
