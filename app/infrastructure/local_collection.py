"""Workspace local de ingestão; uso serial protegido por lock exclusivo.

O lock pertence à unidade de execução da CLI e protege leitura/reconciliação/escrita.
Este adaptador não é uma solução de coordenação distribuída.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app.application.collect_mega_sena import (
    ArchivedResponse, CollectionError, FetchResponse, canonical_json, content_hash,
)
from app.application.sync_mega_sena import SyncAnchor, SyncState
from app.ingestion.mega_sena_api import SOURCE_KEY


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic_write(path: Path, content: bytes, *, immutable: bool = False):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if immutable:
            try:
                os.link(temporary, path)
            except FileExistsError:
                if path.read_bytes() != content:
                    raise CollectionError("immutable_artifact_conflict")
        else:
            os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class LocalCollectionWorkspace:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self._locked = False

    @contextmanager
    def exclusive(self):
        self.root.mkdir(parents=True, exist_ok=True)
        lock = self.root / ".collection.lock"
        try:
            handle = lock.open("x", encoding="ascii")
        except FileExistsError as exc:
            raise CollectionError("workspace_locked") from exc
        try:
            with handle:
                handle.write(str(os.getpid()))
            self._locked = True
            yield self
        finally:
            self._locked = False
            lock.unlink()

    def save(self, response: FetchResponse) -> ArchivedResponse:
        self._require_lock()
        sha = hashlib.sha256(response.body).hexdigest()
        _atomic_write(self.root / "artifacts" / f"{sha}.json", response.body, immutable=True)
        receipt_id = uuid4().hex
        receipt = {
            "schema_version": 1, "receipt_id": receipt_id, "sha256": sha,
            "url": response.url, "status": response.status, "content_type": response.content_type,
            "captured_at": response.captured_at.isoformat(), "byte_count": len(response.body),
        }
        _atomic_write(self._receipt_path(receipt_id), canonical_json(receipt).encode("utf-8"), immutable=True)
        return ArchivedResponse(receipt_id, sha, response)

    def load(self, receipt_id: str) -> ArchivedResponse:
        receipt = _read_json(self._receipt_path(receipt_id))
        sha = receipt["sha256"]
        if not re.fullmatch(r"[0-9a-f]{64}", sha):
            raise CollectionError("invalid_artifact_reference")
        path = self.root / "artifacts" / f"{sha}.json"
        if path.stat().st_size != receipt["byte_count"]:
            raise CollectionError("artifact_size_mismatch")
        body = path.read_bytes()
        if hashlib.sha256(body).hexdigest() != sha:
            raise CollectionError("artifact_hash_mismatch")
        return ArchivedResponse(receipt_id, sha, FetchResponse(
            body, receipt["url"], receipt["status"], receipt["content_type"],
            datetime.fromisoformat(receipt["captured_at"]),
        ))

    def record_result(self, receipt_id: str, result: dict) -> None:
        self._require_lock()
        self._receipt_path(receipt_id)  # valida identificador antes de compor path
        # Tentativas de replay também são preservadas em arquivos independentes.
        path = self.root / "outcomes" / f"{receipt_id}-{uuid4().hex}.json"
        _atomic_write(path, canonical_json(result).encode("utf-8"), immutable=True)

    def reconcile(self, contest: str, payload: dict, receipt_id: str) -> tuple[str, int]:
        self._require_lock()
        if not re.fullmatch(r"[1-9][0-9]*", contest):
            raise CollectionError("invalid_contest_reference")
        self._receipt_path(receipt_id)
        path = self.root / "revisions" / f"{contest}.json"
        history = _read_json(path) if path.exists() else {"schema_version": 1, "revisions": []}
        revisions = history["revisions"]
        for item in revisions:
            if content_hash(item["payload"]) != item["content_sha256"]:
                raise CollectionError("revision_hash_mismatch")
        sha = content_hash(payload)
        if revisions and revisions[-1]["content_sha256"] == sha:
            return "unchanged", len(revisions)
        # Reexecutar uma captura antiga não cria rollback depois de uma correção.
        for item in revisions:
            if item["receipt_id"] == receipt_id:
                return "replayed", item["revision"]
        revision = len(revisions) + 1
        revisions.append({
            "revision": revision, "state": "candidate", "content_sha256": sha,
            "receipt_id": receipt_id, "payload": payload,
        })
        _atomic_write(path, canonical_json(history).encode("utf-8"))
        return ("new" if revision == 1 else "correction_candidate"), revision

    def _receipt_path(self, receipt_id: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{32}", receipt_id):
            raise CollectionError("invalid_receipt_reference")
        return self.root / "receipts" / f"{receipt_id}.json"

    def _require_lock(self) -> None:
        if not self._locked:
            raise CollectionError("workspace_lock_required")

    def load_sync_state(self) -> SyncState | None:
        path = self.root / "sync-state.json"
        if not path.exists():
            return None
        try:
            payload = _read_json(path)
            if set(payload) != {"schema_version", "source_key", "anchor", "cursor", "review_next", "cooldown_until"}:
                raise ValueError("schema de checkpoint inválido")
            if type(payload["schema_version"]) is not int or payload["schema_version"] != 1 or payload["source_key"] != SOURCE_KEY:
                raise ValueError("versão ou fonte de checkpoint incompatível")
            state = SyncState(
                anchor=SyncAnchor(**payload["anchor"]), cursor=payload["cursor"],
                review_next=payload["review_next"],
                cooldown_until=datetime.fromisoformat(payload["cooldown_until"]) if payload["cooldown_until"] else None,
            )
            self._verify_sync_cursor(state)
            return state
        except (ValueError, TypeError, KeyError) as exc:
            raise CollectionError("invalid_sync_checkpoint") from exc

    def save_sync_state(self, state: SyncState) -> None:
        self._require_lock()
        previous = self.load_sync_state()
        if previous is not None:
            if state.anchor != previous.anchor or state.cursor not in (previous.cursor, previous.cursor + 1):
                raise CollectionError("invalid_sync_transition")
        elif state.cursor != state.anchor.last_contest:
            raise CollectionError("invalid_sync_initial_cursor")
        self._verify_sync_cursor(state)
        payload = {
            "schema_version": 1, "source_key": SOURCE_KEY,
            "anchor": {"last_contest": state.anchor.last_contest, "raw_sha256": state.anchor.raw_sha256},
            "cursor": state.cursor, "review_next": state.review_next,
            "cooldown_until": state.cooldown_until.isoformat() if state.cooldown_until else None,
        }
        _atomic_write(self.root / "sync-state.json", canonical_json(payload).encode("utf-8"))

    def record_sync_run(self, report: dict) -> None:
        self._require_lock()
        path = self.root / "sync-runs" / f"{uuid4().hex}.json"
        _atomic_write(path, canonical_json(report).encode("utf-8"), immutable=True)

    def _verify_sync_cursor(self, state: SyncState) -> None:
        if state.cursor == state.anchor.last_contest:
            return
        path = self.root / "revisions" / f"{state.cursor}.json"
        if not path.exists():
            raise CollectionError("sync_revision_missing")
        revisions = _read_json(path)["revisions"]
        if not revisions or any(
            item["payload"].get("lottery_slug") != "mega_sena"
            or item["payload"].get("official_draw_number") != str(state.cursor)
            or content_hash(item["payload"]) != item["content_sha256"]
            for item in revisions
        ):
            raise CollectionError("revision_hash_mismatch")
