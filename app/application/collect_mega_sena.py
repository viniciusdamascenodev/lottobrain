"""Uma execução coleta um concurso e apenas prepara revisões candidatas."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Protocol

from app.domain import DrawCandidate, RawProvenance
from app.ingestion.mega_sena_api import ADAPTER_VERSION, SOURCE_KEY, normalize_response

MAX_RESPONSE_BYTES = 262144


class CollectionError(RuntimeError):
    """Código estável; não inclui headers ou conteúdo arbitrário da rede."""


@dataclass(frozen=True, slots=True)
class FetchResponse:
    body: bytes
    url: str
    status: int
    content_type: str
    captured_at: datetime

    def __post_init__(self):
        if self.captured_at.utcoffset() is None:
            raise ValueError("captured_at requer timezone")
        if len(self.body) > MAX_RESPONSE_BYTES:
            raise CollectionError("response_too_large")


@dataclass(frozen=True, slots=True)
class ArchivedResponse:
    receipt_id: str
    sha256: str
    response: FetchResponse


class MegaSenaSource(Protocol):
    def fetch(self, contest: int | None) -> FetchResponse: ...


class ArtifactStore(Protocol):
    def save(self, response: FetchResponse) -> ArchivedResponse: ...
    def record_result(self, receipt_id: str, result: dict) -> None: ...


class RevisionRepository(Protocol):
    def reconcile(self, contest: str, payload: dict, receipt_id: str) -> tuple[str, int]: ...


def json_value(value):
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        text = format(value, "f")
        return text.rstrip("0").rstrip(".") if "." in text else text
    raise TypeError(f"tipo não serializável: {type(value).__name__}")


def canonical_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=json_value, allow_nan=False)


def semantic_payload(candidate: DrawCandidate) -> dict:
    """Identidade/conteúdo normalizados sem relógio, transporte ou texto monetário."""
    payload = asdict(candidate)
    for key in ("provenance", "external_references", "status"):
        payload.pop(key)
    for amount in payload["monetary_amounts"]:
        amount.pop("source_text")
    for tier in payload["prize_tiers"]:
        if tier["prize_per_winner"]:
            tier["prize_per_winner"].pop("source_text")
    return json.loads(canonical_json(payload))


def content_hash(payload: dict) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


class CollectMegaSena:
    def __init__(self, source: MegaSenaSource, artifacts: ArtifactStore, revisions: RevisionRepository):
        self.source = source
        self.artifacts = artifacts
        self.revisions = revisions

    def execute(self, contest: int | None = None) -> dict:
        if contest is not None and (type(contest) is not int or contest <= 0):
            raise ValueError("concurso deve ser inteiro positivo")
        archived = self.artifacts.save(self.source.fetch(contest))
        return self.replay(archived, expected_contest=contest)

    def replay(self, archived: ArchivedResponse, *, expected_contest: int | None = None) -> dict:
        response = archived.response
        result = {
            "receipt_id": archived.receipt_id, "raw_sha256": archived.sha256,
            "outcome": "quarantined", "issues": [],
        }
        if hashlib.sha256(response.body).hexdigest() != archived.sha256:
            raise CollectionError("artifact_hash_mismatch")
        if response.status != 200:
            result["issues"] = [{"code": f"http.status_{response.status}", "path": "response"}]
        elif response.content_type.split(";", 1)[0].strip().lower() != "application/json":
            result["issues"] = [{"code": "http.invalid_content_type", "path": "response"}]
        else:
            normalized = normalize_response(
                response.body,
                RawProvenance(SOURCE_KEY, archived.sha256, response.captured_at, ADAPTER_VERSION),
                expected_contest=expected_contest,
            )
            result["issues"] = [asdict(issue) for issue in normalized.issues]
            result["canonical_key"] = normalized.canonical_key
            if normalized.is_valid:
                candidate = normalized.candidate
                outcome, revision = self.revisions.reconcile(
                    candidate.official_draw_number, semantic_payload(candidate), archived.receipt_id,
                )
                result.update(outcome=outcome, revision=revision)
                result["official_draw_number"] = candidate.official_draw_number
        self.artifacts.record_result(archived.receipt_id, result)
        return result
