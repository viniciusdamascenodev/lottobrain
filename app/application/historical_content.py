"""Contrato puro de qualificação histórica; não escreve SQL nem substitui o JSON v1."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import re

from app.application.mega_sena_content import canonical_bytes, decimal_text, digest
from app.catalog import CATALOG
from app.domain import DrawCandidate, ValueStatus, assert_valid_draw

VERSION = "lottobrain.historical.result.v1"
CODE_VERSION = "spec-0026-v1"
POLICY_VERSION = "spec-0026-observed-sources-v1"


@dataclass(frozen=True)
class SourceProfile:
    lottery: str
    money: frozenset[str]
    tiers: frozenset[str] = frozenset()
    attributes: tuple[tuple[str, type], ...] = ()
    metadata: frozenset[str] = frozenset()
    scope: str = "common_result"
    currency: str = "BRL"


_BR_MONEY = frozenset({"rollover_amount", "sales_total", "next_estimated_jackpot", "special_draw_rollover"})
_BR_TEXT = frozenset({"winner_locations_source_text", "observation_source_text"})
_MS_TIERS = frozenset({"sena", "quina", "quadra"})
PROFILES = {
    "caixa_mega_sena_xlsx": SourceProfile("mega_sena", _BR_MONEY, _MS_TIERS, metadata=_BR_TEXT),
    "caixa_mega_sena_json": SourceProfile("mega_sena", _BR_MONEY | {"ending_zero_five_rollover"},
        _MS_TIERS, metadata=frozenset({"draw_order", "draw_city", "draw_location", "rollover", "observation_source_text"})),
    "caixa_lotofacil_xlsx": SourceProfile("lotofacil", _BR_MONEY,
        frozenset(f"hits_{n}" for n in range(11, 16)), metadata=_BR_TEXT),
    "caixa_mais_milionaria_xlsx": SourceProfile("mais_milionaria",
        frozenset({"sales_total", "next_estimated_jackpot"}),
        frozenset({"hits_6_clovers_2", "hits_6_clovers_0_or_1", "hits_5_clovers_2", "hits_5_clovers_0_or_1",
                   "hits_4_clovers_2", "hits_4_clovers_0_or_1", "hits_3_clovers_2", "hits_3_clovers_1",
                   "hits_2_clovers_2", "hits_2_clovers_1"}),
        (("rolled_over", bool),), _BR_TEXT | {"rollover_flag_source_text"}),
    "usamega_powerball_html": SourceProfile("powerball", frozenset({"advertised_jackpot"}),
        attributes=(("power_play", int),), metadata=frozenset({"visible_date_source_text", "power_play_state"}), currency="USD"),
    "usamega_mega_millions_html": SourceProfile("mega_millions", frozenset({"advertised_jackpot"}),
        attributes=(("megaplier", int),), metadata=frozenset({"visible_date_source_text", "multiplier_state"}), currency="USD"),
    "pedromealha_euromillions_api_json": SourceProfile("euro_millions", frozenset({"top_tier_prize_per_winner"}),
        attributes=(("has_jackpot_winner", bool),),
        metadata=frozenset({"date_source_text", "prize_scope", "prize_source_jurisdiction"}), scope="provider_pt_or_es", currency="EUR"),
}


def _profile(candidate: DrawCandidate) -> SourceProfile:
    key = candidate.provenance.source_key if candidate.provenance else None
    profile = PROFILES.get(key)
    if profile is None or profile.lottery != candidate.lottery_slug:
        raise ValueError("fonte/loteria sem perfil histórico qualificado")
    return profile


def identity(candidate: DrawCandidate) -> dict:
    """Alias não é PK SQL. Data é provisória e limitada aos seis históricos atuais."""
    profile = _profile(candidate)
    official = profile.lottery in {"mega_sena", "lotofacil", "mais_milionaria"}
    if official:
        if not re.fullmatch(r"[1-9][0-9]*", candidate.official_draw_number or ""):
            raise ValueError("número oficial positivo necessário")
        return {"namespace": "official_draw_number", "value": candidate.official_draw_number, "assurance": "official"}
    if candidate.official_draw_number is not None:
        raise ValueError("esta fonte não fornece sequência oficial qualificada")
    return {"namespace": "drawing_date", "value": candidate.draw_date.isoformat(), "assurance": "provisional"}


def _money(amount, profile: SourceProfile) -> dict:
    if amount.status is ValueStatus.KNOWN:
        if not isinstance(amount.amount, Decimal):
            raise ValueError("montante requer Decimal exato")
        text = "0" if amount.amount == 0 else decimal_text(amount.amount)
        normalized = Decimal(text)
        if (normalized < 0 or normalized > Decimal("1e18") or normalized.as_tuple().exponent < -6
                or amount.currency != profile.currency):
            raise ValueError("montante fora do envelope SQL")
    else:
        if amount.amount is not None or amount.currency is not None:
            raise ValueError("montante ausente não aceita valor/moeda")
        text = None
    return {"kind": amount.kind, "scope": profile.scope, "payout_form": "unspecified",
            "status": amount.status.value, "amount": text, "currency": amount.currency}


def to_content(candidate: DrawCandidate) -> dict:
    profile = _profile(candidate)
    assert_valid_draw(candidate, CATALOG.get(profile.lottery).lottery)
    metadata = dict(candidate.metadata)
    if set(metadata) - profile.metadata:
        raise ValueError("metadado sem mapeamento qualificado")
    namespaces = ({"official_draw_number"} if candidate.official_draw_number else
                  {"source_id", "draw_id"} if profile.lottery == "euro_millions" else {"drawing_path"})
    if ({r.namespace for r in candidate.external_references} != namespaces
            or len(candidate.external_references) != len(namespaces)):
        raise ValueError("referências externas esperadas ausentes ou repetidas")
    for ref in candidate.external_references:
        if (ref.source_key != candidate.provenance.source_key or ref.namespace not in namespaces
                or ref.namespace == "official_draw_number" and ref.value != candidate.official_draw_number):
            raise ValueError("referência externa sem contrato ou divergente")
    if profile.lottery == "euro_millions" and (
            metadata.get("prize_source_jurisdiction") != "PT_or_ES"
            or metadata.get("prize_scope") != "top_tier_5_plus_2_per_winner"):
        raise ValueError("contexto financeiro EuroMillions não qualificado")
    kinds = [m.kind for m in candidate.monetary_amounts]
    tiers = [t.tier_key for t in candidate.prize_tiers]
    if len(kinds) != len(set(kinds)) or set(kinds) != profile.money:
        raise ValueError("medidas financeiras incompatíveis com o perfil")
    if len(tiers) != len(set(tiers)) or set(tiers) != profile.tiers:
        raise ValueError("faixas incompatíveis com o perfil")
    series = []
    for item in sorted(candidate.series, key=lambda s: s.key):
        components = []
        for component in sorted(item.components, key=lambda c: c.key):
            extraction = ()
            if "draw_order" in metadata:
                if candidate.provenance.source_key != "caixa_mega_sena_json" or item.key != "primary" or component.key != "main":
                    raise ValueError("ordem de extração sem contrato")
                try:
                    extraction = tuple(int(v) for v in metadata["draw_order"].split(","))
                except ValueError as error:
                    raise ValueError("ordem de extração inválida") from error
                if sorted(extraction) != list(component.values):
                    raise ValueError("ordem de extração diverge do resultado")
            components.append({"key": component.key, "values": [
                {"ordinal": ordinal, "integer_value": value if type(value) is int else None,
                 "text_value": value if type(value) is str else None,
                 "extraction_ordinal": extraction.index(value) + 1 if extraction else None}
                for ordinal, value in enumerate(component.values, 1)]})
        attrs = []
        for attr in sorted(item.attributes, key=lambda a: a.key):
            expected = dict(profile.attributes).get(attr.key)
            if item.key != "primary" or expected is None or type(attr.value) is not expected:
                raise ValueError("atributo/tipo sem contrato nesta série")
            if expected is int and not -(2**63) <= attr.value < 2**63:
                raise ValueError("atributo fora do envelope bigint SQL")
            attrs.append({"key": attr.key, "value_type": "boolean" if expected is bool else "integer", "value": attr.value})
        series.append({"key": item.key, "components": components, "attributes": attrs})
    financial_tiers = []
    for tier in sorted(candidate.prize_tiers, key=lambda t: t.tier_key):
        if (tier.status is ValueStatus.KNOWN and type(tier.winners) is not int
                or tier.status is not ValueStatus.KNOWN and tier.winners is not None):
            raise ValueError("estado de ganhadores incompatível")
        if tier.winners is not None and not 0 <= tier.winners < 2**63:
            raise ValueError("ganhadores fora do envelope bigint SQL")
        if tier.prize_per_winner is None or tier.prize_per_winner.kind != "paid_per_winner":
            raise ValueError("medida da faixa não qualificada")
        financial_tiers.append({"key": tier.tier_key, "scope": profile.scope, "variant": "base",
            "winners_status": tier.status.value, "winners": tier.winners,
            "prize": _money(tier.prize_per_winner, profile)})
    return {"schema_version": VERSION, "lottery": candidate.lottery_slug, "identity": identity(candidate),
            "rule_version": candidate.rule_version_label, "draw_date": candidate.draw_date.isoformat(),
            "series": series, "prize_tiers": financial_tiers,
            "money": [_money(m, profile) for m in sorted(candidate.monetary_amounts, key=lambda m: m.kind)],
            "metadata": {k: v for k, v in metadata.items() if not k.endswith("source_text") and k != "draw_order"}}


def source_evidence(candidate: DrawCandidate) -> dict:
    """Evidência separada: não entra no hash do conteúdo, mas não pode ser descartada."""
    _profile(candidate)
    return {"source_key": candidate.provenance.source_key,
        "external_references": [{"source_key": r.source_key, "namespace": r.namespace, "value": r.value}
                                for r in sorted(candidate.external_references, key=lambda r: (r.source_key, r.namespace, r.value))],
        "metadata": dict(candidate.metadata),
        "money_source_texts": [{"tier": None, "kind": m.kind, "source_text": m.source_text}
                               for m in sorted(candidate.monetary_amounts, key=lambda m: m.kind)] + [
            {"tier": t.tier_key, "kind": t.prize_per_winner.kind, "source_text": t.prize_per_winner.source_text}
            for t in sorted(candidate.prize_tiers, key=lambda t: t.tier_key) if t.prize_per_winner]}


def compare_shared(left: dict, right: dict) -> dict:
    """Comparação explícita, não algoritmo de merge nem autorização de publicação."""
    def facts(content):
        result = {key: content[key] for key in ("lottery", "identity", "draw_date", "rule_version")}
        for series in content["series"]:
            for c in series["components"]:
                prefix = f"series.{series['key']}.{c['key']}"
                result[prefix] = [(v["integer_value"], v["text_value"]) for v in c["values"]]
                extraction = [v["extraction_ordinal"] for v in c["values"]]
                if any(v is not None for v in extraction):
                    result[prefix + ".extraction"] = extraction
            for attr in series["attributes"]:
                result[f"attribute.{series['key']}.{attr['key']}"] = attr
        for tier in content["prize_tiers"]:
            result[f"tier.{tier['key']}.{tier['scope']}.{tier['variant']}"] = tier
        for m in content["money"]:
            result[f"money.{m['kind']}.{m['scope']}.{m['payout_form']}"] = m
        for k, v in content["metadata"].items():
            result[f"metadata.{k}"] = v
        return result
    a, b = facts(left), facts(right)
    shared = a.keys() & b.keys()
    return {"equal": sorted(k for k in shared if a[k] == b[k]),
            "different": [{"path": k, "left": a[k], "right": b[k]} for k in sorted(shared) if a[k] != b[k]],
            "only_left": sorted(a.keys() - b.keys()), "only_right": sorted(b.keys() - a.keys())}
