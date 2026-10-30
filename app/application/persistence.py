"""Portas e valores da escrita transacional; sem driver ou framework."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Callable, Protocol, TypeVar, TYPE_CHECKING
from uuid import UUID

from app.application.collect_mega_sena import FetchResponse

if TYPE_CHECKING:
    from app.application.activate_mega_sena_baseline import BaselineRequest
    from app.application.historical_import import HistoricalImportPlan
    from app.application.sync_postgres import SyncBatchRequest
    from app.application.result_persistence import PreparedResult


class PersistenceError(RuntimeError):
    def __init__(self, code: str, *, retryable: bool = False):
        super().__init__(code)
        self.code = code
        self.retryable = retryable


def command_key(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,160}", value):
        raise ValueError("command_key deve ter 1–160 caracteres ASCII alfanuméricos/_.:-")
    return value


@dataclass(frozen=True)
class CatalogBinding:
    lottery_id: UUID
    source_id: UUID
    scope_id: UUID
    rule_id: UUID
    series_id: UUID
    component_id: UUID
    tiers: tuple[tuple[str, UUID], ...]
    fingerprint: str
    source_snapshot: dict


@dataclass(frozen=True)
class CaptureTicket:
    run_id: UUID
    attempt_id: UUID
    receipt_id: UUID | None = None
    error: str | None = None
    fresh: bool = False


@dataclass(frozen=True)
class Receipt:
    id: UUID
    run_id: UUID
    sha256: str
    object_key: str
    byte_count: int
    status: int
    content_type: str
    captured_at: datetime
    url: str
    expected_contest: int | None
    source_id: UUID


@dataclass(frozen=True)
class Lease:
    checkpoint_id: UUID
    token: int
    cursor: int
    until: datetime


@dataclass(frozen=True)
class Advance:
    checkpoint_id: UUID
    expected_cursor: int
    lease_token: int

    def __post_init__(self):
        if not isinstance(self.checkpoint_id, UUID) or type(self.expected_cursor) is not int or self.expected_cursor < 0:
            raise ValueError("checkpoint/cursor inválidos")
        if type(self.lease_token) is not int or self.lease_token < 1:
            raise ValueError("lease_token inválido")


@dataclass(frozen=True)
class ProcessingResult:
    receipt_id: UUID
    observation_id: UUID
    outcome: str
    draw_id: UUID | None
    revision_id: UUID | None
    revision_no: int | None
    advanced_to: int | None = None


@dataclass(frozen=True)
class BatchIntent(Advance):
    operation_id: UUID

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.operation_id,UUID): raise ValueError("operação UUID necessária")


class RawStorage(Protocol):
    def put(self, body: bytes) -> tuple[str, str]: ...
    def read(self, key: str, sha256: str, byte_count: int) -> bytes: ...


class CatalogRepository(Protocol):
    def qualify(self) -> CatalogBinding: ...


class CaptureRepository(Protocol):
    def start(self, binding: CatalogBinding, key: str, request_hash: str, contest: int | None) -> CaptureTicket: ...
    def receipt(self, receipt_id: UUID) -> Receipt: ...
    def complete(self, binding: CatalogBinding, ticket: CaptureTicket, response: FetchResponse, sha256: str, object_key: str) -> UUID: ...
    def fail(self, ticket: CaptureTicket, code: str) -> None: ...
    def finish(self, receipt_id: UUID, outcome: str) -> None: ...


class ProcessingRepository(Protocol):
    def lock_command(self, key: str, request_hash: str, *, compatible_hashes: tuple[str, ...] = ()): ...
    def claim(self, binding: CatalogBinding, receipt: Receipt): ...
    def observation(self, processing_id: UUID): ...
    def record(self, processing_id: UUID, key: str, request_hash: str, outcome: str) -> None: ...
    def quarantine(self, binding: CatalogBinding, processing_id: UUID, issues): ...
    def complete(self, processing_id: UUID) -> None: ...


class DrawRepository(Protocol):
    def reconcile(self, binding: CatalogBinding, processing_id: UUID, content: dict, content_hash: str, source_texts: dict, *, evidence: dict | None = None): ...
    def read_content(self, revision_id: UUID) -> dict: ...


class SyncRepository(Protocol):
    def lock(self, advance: Advance, binding: CatalogBinding): ...
    def advance(self, intent: Advance, checkpoint: dict, observation: dict) -> None: ...
    def claim_lease(self, checkpoint_id: UUID, binding: CatalogBinding, seconds: int) -> Lease: ...
    def throttle(self, receipt: Receipt, checkpoint_id: UUID) -> None: ...
    def mark_review(self, intent: BatchIntent, checkpoint: dict, next_review: int) -> None: ...


class BaselineRepository(Protocol):
    def activate(self, request: BaselineRequest, plan: HistoricalImportPlan) -> dict: ...


class SyncBatchRepository(Protocol):
    def open(self, request: SyncBatchRequest) -> dict: ...
    def snapshot(self, batch_id: UUID, token: int) -> dict: ...
    def heartbeat(self, batch_id: UUID, token: int) -> None: ...
    def reserve(self, batch_id: UUID, token: int, planned: dict) -> dict: ...
    def attach(self, batch_id: UUID, token: int, operation: UUID, receipt: UUID) -> None: ...
    def prepare_operation(self, batch_id: UUID, token: int, operation: UUID) -> dict: ...
    def finish(self, batch_id: UUID, token: int, reason: str) -> dict: ...
    def release(self, batch_id: UUID, token: int) -> None: ...
    def phase(self, intent: BatchIntent, receipt: UUID) -> str: ...
    def lock_operation(self, intent: BatchIntent, binding: CatalogBinding, key: str): ...
    def complete_operation(self, intent: BatchIntent, operation: dict, observation: dict, outcome: str) -> None: ...


class UnitOfWork(Protocol):
    catalog: CatalogRepository
    captures: CaptureRepository
    processing: ProcessingRepository
    draws: DrawRepository
    sync: SyncRepository
    baselines: BaselineRepository
    batches: SyncBatchRepository
    results: ResultRepository
    datasets: DatasetRepository
    admin: CatalogAdministration
    def __enter__(self) -> UnitOfWork: ...
    def __exit__(self, exc_type, exc, traceback): ...
    def checkpoint(self, stage: str) -> None: ...


class ResultRepository(Protocol):
    def store(self, prepared: PreparedResult, key: str, object_key: str, *, allow_correction: bool = False) -> dict: ...


class CatalogAdministration(Protocol):
    def bootstrap(self) -> dict: ...
    def inspect(self) -> dict: ...


class DatasetRepository(Protocol):
    def policy(self, lottery: str, version: str, sources: tuple[str, ...], actor: str) -> UUID: ...
    def approve(self, policy_id: UUID, revision_ids: list[UUID], actor: str, key: str) -> UUID: ...
    def activate(self, dataset: UUID, expected_version: int, actor: str, key: str) -> dict: ...
    def read(self, lottery: str, dataset_id: UUID | None, offset: int, limit: int) -> dict: ...


T = TypeVar("T")


def transact(factory: Callable[[], UnitOfWork], operation: Callable[[UnitOfWork], T]) -> T:
    """Retry só de transação abortada conhecida, nunca de GET/PUT/commit ambíguo."""
    for attempt in range(3):
        try:
            with factory() as unit:
                result = operation(unit)
            return result
        except PersistenceError as error:
            if not error.retryable or attempt == 2:
                raise
    raise AssertionError("unreachable")
