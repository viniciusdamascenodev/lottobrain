"""Representação relacional v1 Mega-Sena; IDs SQL e proveniência não são conteúdo."""
from __future__ import annotations

from decimal import Decimal
import hashlib
import json
import re

from app.domain import DrawCandidate, ValueStatus, assert_valid_draw
from app.ingestion.mega_sena import MEGA_SENA

VERSION = "lottobrain.mega_sena.result.v1"
CODE_VERSION = "spec-0025-v1"
POLICY_VERSION = "mega-sena-api-observed-v1"


def decimal_text(value: Decimal) -> str:
    if not value.is_finite():
        raise ValueError("decimal não finito")
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def canonical_bytes(content: dict) -> bytes:
    return json.dumps(content, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(content: dict) -> str:
    return hashlib.sha256(canonical_bytes(content)).hexdigest()


def money_content(amount) -> dict:
    return {"kind": amount.kind, "scope": "common_result", "payout_form": "unspecified",
            "status": amount.status.value,
            "amount": decimal_text(amount.amount) if amount.status is ValueStatus.KNOWN else None,
            "currency": amount.currency}


def to_content(candidate: DrawCandidate) -> dict:
    assert_valid_draw(candidate, MEGA_SENA)
    if not candidate.official_draw_number or not re.fullmatch(r"[1-9][0-9]*",candidate.official_draw_number):
        raise ValueError("identidade oficial necessária")
    if len(candidate.series) != 1 or candidate.series[0].key != "primary" or candidate.series[0].attributes:
        raise ValueError("série/atributos não suportados pelo mapper v1")
    metadata = dict(candidate.metadata)
    order = metadata.pop("draw_order", None)
    numbers = candidate.series[0].components[0].values
    extraction = tuple(int(v) for v in order.split(",")) if order is not None else ()
    if extraction and (len(extraction) != len(numbers) or sorted(extraction) != list(numbers)):
        raise ValueError("ordem de extração não corresponde ao resultado")
    values = [{"ordinal": index, "integer_value": value,
               "extraction_ordinal": extraction.index(value) + 1 if extraction else None}
              for index, value in enumerate(numbers, 1)]
    return {
        "schema_version": VERSION, "lottery": "mega_sena", "identity": candidate.official_draw_number,
        "rule_version": candidate.rule_version_label, "draw_date": candidate.draw_date.isoformat(),
        "series": [{"key": "primary", "components": [{"key": "main", "values": values}]}],
        "prize_tiers": [{"key": tier.tier_key, "scope": "common_result", "variant": "base",
                         "winners_status": tier.status.value, "winners": tier.winners,
                         "prize": money_content(tier.prize_per_winner) if tier.prize_per_winner else None}
                        for tier in sorted(candidate.prize_tiers, key=lambda t: t.tier_key)],
        "money": [money_content(amount) for amount in sorted(candidate.monetary_amounts, key=lambda m: m.kind)],
        "metadata": metadata,
    }


def source_texts(candidate: DrawCandidate) -> dict:
    return {**{(None, m.kind): m.source_text for m in candidate.monetary_amounts},
            **{(t.tier_key, t.prize_per_winner.kind): t.prize_per_winner.source_text
               for t in candidate.prize_tiers if t.prize_per_winner}}
