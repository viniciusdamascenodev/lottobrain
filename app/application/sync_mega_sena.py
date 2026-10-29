"""Sincronização limitada: checkpoint contíguo e revisão circular independente."""
from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Callable, Protocol

from app.application.collect_mega_sena import CollectMegaSena, CollectionError


@dataclass(frozen=True, slots=True)
class SyncAnchor:
    last_contest: int
    raw_sha256: str

    def __post_init__(self):
        if type(self.last_contest) is not int or self.last_contest < 0:
            raise ValueError("baseline deve indicar concurso não negativo")
        if not re.fullmatch(r"[0-9a-f]{64}", self.raw_sha256):
            raise ValueError("baseline requer SHA-256")


@dataclass(frozen=True, slots=True)
class SyncState:
    anchor: SyncAnchor
    cursor: int
    review_next: int
    cooldown_until: datetime | None = None

    def __post_init__(self):
        if type(self.cursor) is not int or self.cursor < self.anchor.last_contest:
            raise ValueError("cursor anterior à baseline")
        if type(self.review_next) is not int or not self.anchor.last_contest < self.review_next <= self.cursor + 1:
            raise ValueError("posição de revisão fora da cobertura incremental")
        if self.cooldown_until is not None and self.cooldown_until.utcoffset() is None:
            raise ValueError("cooldown requer timezone")


@dataclass(frozen=True, slots=True)
class SyncPolicy:
    max_requests: int = 4
    review_window: int = 3
    interval_seconds: float = 2

    def __post_init__(self):
        if type(self.max_requests) is not int or not 1 <= self.max_requests <= 10:
            raise ValueError("orçamento deve estar entre 1 e 10 GETs")
        if type(self.review_window) is not int or not 0 <= self.review_window <= 20:
            raise ValueError("janela deve estar entre 0 e 20 concursos")
        if not 2 <= self.interval_seconds <= 30:
            raise ValueError("intervalo deve estar entre 2 e 30 segundos")


class SyncStateStore(Protocol):
    def load_sync_state(self) -> SyncState | None: ...
    def save_sync_state(self, state: SyncState) -> None: ...
    def record_sync_run(self, report: dict) -> None: ...


class SyncMegaSena:
    def __init__(
        self, collector: CollectMegaSena, states: SyncStateStore,
        *, wait: Callable[[float], None],
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ):
        self.collector = collector
        self.states = states
        self.wait = wait
        self.clock = clock

    def execute(self, policy: SyncPolicy = SyncPolicy(), *, anchor: SyncAnchor | None = None) -> dict:
        state = self.states.load_sync_state()
        if state is None:
            if anchor is None:
                raise CollectionError("sync_not_initialized")
            state = SyncState(anchor, anchor.last_contest, anchor.last_contest + 1)
            self.states.save_sync_state(state)
        elif anchor is not None and anchor != state.anchor:
            raise CollectionError("sync_baseline_mismatch")
        started = self.clock()
        report = {
            "schema_version": 1, "started_at": started.isoformat(),
            "cursor_before": state.cursor, "requests": 0, "operations": [],
            "latest_observed": None, "stop_reason": "budget_exhausted",
        }

        def finish(reason):
            report.update(
                stop_reason=reason, cursor_after=state.cursor,
                review_next=state.review_next, finished_at=self.clock().isoformat(),
                cooldown_until=state.cooldown_until.isoformat() if state.cooldown_until else None,
            )
            target = report["latest_observed"]
            report["remaining"] = max(0, target - state.cursor) if target is not None else None
            self.states.record_sync_run(report)
            return report

        def request(contest, phase):
            nonlocal state
            # Inclui a primeira consulta: duas invocações seguidas também são espaçadas.
            self.wait(policy.interval_seconds)
            report["requests"] += 1
            try:
                result = self.collector.execute(contest)
            except CollectionError as error:
                report["operations"].append({"phase": phase, "contest": contest, "outcome": "failed", "code": str(error)})
                return None
            report["operations"].append({"phase": phase, "contest": contest, **result})
            if result["outcome"] == "quarantined":
                if any(issue["code"] == "http.status_429" for issue in result["issues"]):
                    state = replace(state, cooldown_until=self.clock() + timedelta(minutes=15))
                    self.states.save_sync_state(state)
                return None
            if result["outcome"] not in {"new", "unchanged", "correction_candidate", "replayed"}:
                raise CollectionError("sync_unexpected_collection_outcome")
            return result

        if state.cooldown_until is not None and started < state.cooldown_until:
            return finish("cooldown")

        discovered = request(None, "discovery")
        if discovered is None:
            return finish("collection_stopped")
        latest = int(discovered["official_draw_number"])
        report["latest_observed"] = latest
        if latest < state.cursor:
            return finish("source_behind_cursor")

        # Janela baseada na cobertura anterior ao lote: evita rever dados recém-coletados.
        low = max(state.anchor.last_contest + 1, state.cursor - policy.review_window + 1)
        review_targets = []
        if policy.review_window and low <= state.cursor:
            start = state.review_next if low <= state.review_next <= state.cursor else low
            review_targets = list(range(start, state.cursor + 1)) + list(range(low, start))
        remaining_budget = policy.max_requests - report["requests"]
        reserve = 1 if review_targets and latest > state.cursor and remaining_budget >= 2 else 0

        while state.cursor < latest:
            contest = state.cursor + 1
            if contest == latest:
                report["operations"].append({"phase": "forward", "contest": contest, "reused_discovery": True, **discovered})
            elif report["requests"] < policy.max_requests - reserve:
                if request(contest, "forward") is None:
                    return finish("collection_stopped")
            else:
                break
            # Só acontece após raw, validação, reconciliação e outcome concluídos.
            state = replace(state, cursor=contest)
            self.states.save_sync_state(state)

        # Uma revisão por lote durante backlog; quando em dia, usa orçamento disponível.
        for contest in review_targets:
            if contest == latest:
                report["operations"].append({"phase": "review", "contest": contest, "reused_discovery": True, **discovered})
            elif report["requests"] < policy.max_requests:
                if request(contest, "review") is None:
                    return finish("collection_stopped")
            else:
                break
            # Rotação usa o limite superior da janela original, não cursor avançado.
            upper = max(review_targets)
            next_review = contest + 1 if contest < upper else low
            state = replace(state, review_next=next_review)
            self.states.save_sync_state(state)
            if state.cursor < latest:
                break
        return finish("caught_up" if state.cursor == latest else "budget_exhausted")
