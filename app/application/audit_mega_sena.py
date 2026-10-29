"""Auditoria determinística sobre um snapshot de evidências; nenhuma escrita."""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.application.collect_mega_sena import MAX_RESPONSE_BYTES, canonical_json, content_hash, semantic_payload
from app.application.sync_mega_sena import SyncAnchor, SyncState
from app.domain import RawProvenance
from app.ingestion.mega_sena_api import ADAPTER_VERSION, SOURCE_KEY, normalize_response

API_URL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena"
ACCEPTED = {"new", "unchanged", "correction_candidate", "replayed"}
SHA = re.compile(r"[0-9a-f]{64}")
RECEIPT_ID = re.compile(r"[0-9a-f]{32}")


@dataclass(frozen=True, slots=True)
class AuditFile:
    path: str
    body: bytes | None
    size: int | None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class BaselineEvidence:
    last_contest: int
    expected_sha256: str
    observed_sha256: str | None


@dataclass(frozen=True, slots=True)
class AuditSnapshot:
    exists: bool
    files: tuple[AuditFile, ...]
    baseline: BaselineEvidence

    def manifest(self) -> dict:
        return {
            "exists": self.exists,
            "baseline": {
                "last_contest": self.baseline.last_contest,
                "expected_sha256": self.baseline.expected_sha256,
                "observed_sha256": self.baseline.observed_sha256,
            },
            "files": [
                {"path": f.path, "size": f.size, "error": f.error,
                 "sha256": hashlib.sha256(f.body).hexdigest() if f.body is not None else None}
                for f in sorted(self.files, key=lambda item: item.path)
            ],
        }


class AuditReader(Protocol):
    def capture(self) -> AuditSnapshot: ...


def _strict_json(body: bytes):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("chave duplicada")
            result[key] = value
        return result

    def invalid(value):
        raise ValueError("constante inválida")

    value = json.loads(body, object_pairs_hook=unique, parse_constant=invalid)
    canonical_json(value).encode("utf-8")
    return value


def _instant(value):
    if not isinstance(value, str):
        raise ValueError("instante deve ser texto")
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise ValueError("timezone ausente")
    return parsed


def missing_ranges(first: int, last: int, present: set[int]) -> list[dict]:
    """Lacunas compactas; não aloca uma lista para cada identificador ausente."""
    gaps = []
    pointer = first
    for value in sorted(v for v in present if first <= v <= last):
        if pointer < value:
            gaps.append({"first": pointer, "last": value - 1, "count": value - pointer})
        pointer = value + 1
    if pointer <= last:
        gaps.append({"first": pointer, "last": last, "count": last - pointer + 1})
    return gaps


class AuditMegaSena:
    def __init__(self, reader: AuditReader):
        self.reader = reader

    def execute(self) -> dict:
        snapshot = self.reader.capture()
        report = audit_snapshot(snapshot)
        after = self.reader.capture()
        if canonical_json(snapshot.manifest()) != canonical_json(after.manifest()):
            report["issues"].append({
                "code": "workspace.changed_during_audit", "severity": "error", "path": ".",
                "recovery": "retry_stable_snapshot",
            })
        return finalize_report(report)


def audit_snapshot(snapshot: AuditSnapshot) -> dict:
    issues = []

    def issue(code, path, *, severity="error", recovery="inspect_evidence"):
        issues.append({"code": code, "path": path, "severity": severity, "recovery": recovery})

    files = {item.path: item for item in snapshot.files}
    manifest = snapshot.manifest()
    baseline_ok = snapshot.baseline.observed_sha256 == snapshot.baseline.expected_sha256
    if not snapshot.exists:
        issue("workspace.missing", ".", recovery="restore_workspace")
    if not baseline_ok:
        issue("baseline.hash_mismatch", "baseline", recovery="restore_baseline")
    for item in snapshot.files:
        if item.error:
            issue("file." + item.error, item.path)
        if item.path == ".collection.lock":
            issue("workspace.lock_present", item.path, recovery="retry_stable_snapshot")
        elif ".pending-" in item.path:
            issue("file.pending_write", item.path, severity="warning", recovery="inspect_interrupted_write")

    def document(path):
        item = files.get(path)
        if item is None or item.body is None:
            return None
        try:
            value = _strict_json(item.body)
            if not isinstance(value, dict):
                raise ValueError("objeto obrigatório")
            return value
        except (ValueError, UnicodeError, RecursionError):
            issue("file.invalid_json", path)
            return None

    artifacts, artifact_paths = _audit_artifacts(files, issue)
    receipts = _audit_receipts(files, artifacts, artifact_paths, document, issue)
    outcomes = _audit_outcomes(files, receipts, document, issue)
    valid_contests, materialized_contests, revision_count = _audit_revisions(
        files, receipts, outcomes, document, issue,
    )
    state = _audit_checkpoint(files, snapshot, document, issue)
    operational_stops, valid_runs = _audit_runs(files, receipts, outcomes, state, document, issue)

    recognized = {"artifacts", "receipts", "revisions", "outcomes", "sync-runs"}
    for path in sorted(files):
        if path not in {"sync-state.json", ".collection.lock"} and path.split("/", 1)[0] not in recognized and ".pending-" not in path:
            issue("file.unexpected", path, severity="warning")

    anchor = snapshot.baseline.last_contest
    gaps = missing_ranges(anchor + 1, state.cursor, valid_contests) if state else []
    if gaps:
        issue("cursor.coverage_gap", "sync-state.json", recovery="restore_contiguous_evidence")
    verified_cursor = (gaps[0]["first"] - 1 if gaps else state.cursor) if state and baseline_ok else None
    observed = {
        int(receipt["semantic"]["official_draw_number"])
        for receipt in receipts.values() if receipt["semantic"] is not None
    }
    highest = max(observed, default=None)
    claimed = state.cursor if state else None
    missing_after = missing_ranges(claimed + 1, highest, valid_contests) if claimed is not None and highest is not None else []
    return {
        "report_version": "spec-0022-v1", "normalizer_version": ADAPTER_VERSION,
        "input_manifest": manifest, "input_manifest_sha256": content_hash(manifest),
        "baseline_verified": baseline_ok,
        "counts": {
            "artifacts": len(artifact_paths), "verified_artifacts": len(artifacts),
            "verified_receipts": len(receipts), "outcome_documents_checked": len(outcomes),
            "revision_records": revision_count, "materialized_candidate_contests": len(materialized_contests),
            "verified_candidate_contests": len(valid_contests), "structurally_valid_runs": valid_runs,
        },
        "coverage": {
            "baseline_referenced_through": anchor, "cursor_claimed": claimed,
            "cursor_verified_through": verified_cursor,
            "unverified_within_cursor": gaps,
            "materialized_candidate_contests": sorted(materialized_contests),
            "verified_candidate_contests": sorted(valid_contests),
            "ahead_candidates": sorted(n for n in valid_contests if claimed is not None and n > claimed),
            "baseline_overlap_candidates": sorted(n for n in valid_contests if n <= anchor),
            "highest_observed_in_saved_captures": highest,
            "pending_identifiers_to_observed": max(0, highest - claimed) if highest is not None and claimed is not None else None,
            "unverified_after_cursor": missing_after,
            "publication_status": "candidates_only",
        },
        "operational_stops": dict(sorted(operational_stops.items())),
        "issues": issues,
    }


def _audit_artifacts(files, issue):
    artifacts = {}
    artifact_paths = set()
    for path, item in sorted(files.items()):
        if not path.startswith("artifacts/") or ".pending-" in path:
            continue
        artifact_paths.add(path)
        name = path.removeprefix("artifacts/").removesuffix(".json")
        if not path.endswith(".json") or not SHA.fullmatch(name):
            issue("artifact.invalid_name", path)
        elif item.body is not None:
            if len(item.body) > MAX_RESPONSE_BYTES:
                issue("artifact.too_large", path)
            elif hashlib.sha256(item.body).hexdigest() != name:
                issue("artifact.hash_mismatch", path, recovery="restore_artifact")
            else:
                artifacts[name] = item.body

    return artifacts, artifact_paths

def _audit_receipts(files, artifacts, artifact_paths, document, issue):
    receipts = {}
    referenced_artifacts = set()
    for path in sorted(files):
        if not path.startswith("receipts/") or ".pending-" in path:
            continue
        receipt_id = path.removeprefix("receipts/").removesuffix(".json")
        if not path.endswith(".json") or not RECEIPT_ID.fullmatch(receipt_id):
            issue("receipt.invalid_name", path)
            continue
        payload = document(path)
        if payload is None:
            continue
        try:
            if set(payload) != {"schema_version", "receipt_id", "sha256", "url", "status", "content_type", "captured_at", "byte_count"}:
                raise ValueError
            if type(payload["schema_version"]) is not int or payload["schema_version"] != 1 or payload["receipt_id"] != receipt_id:
                raise ValueError
            sha = payload["sha256"]
            if not isinstance(sha, str) or not SHA.fullmatch(sha):
                raise ValueError
            referenced_artifacts.add(f"artifacts/{sha}.json")
            if type(payload["byte_count"]) is not int or not 0 <= payload["byte_count"] <= MAX_RESPONSE_BYTES:
                raise ValueError
            if type(payload["status"]) is not int or not 100 <= payload["status"] <= 599:
                raise ValueError
            if not isinstance(payload["content_type"], str):
                raise ValueError
            url = payload["url"]
            if not isinstance(url, str):
                raise ValueError
            if url == API_URL:
                expected = None
            elif re.fullmatch(re.escape(API_URL) + r"/[1-9][0-9]*", url):
                expected = int(url.rsplit("/", 1)[1])
            else:
                raise ValueError
            captured = _instant(payload["captured_at"])
        except (ValueError, KeyError, TypeError, OverflowError):
            issue("receipt.invalid_metadata", path)
            continue
        body = artifacts.get(sha)
        if body is None:
            issue("receipt.artifact_unavailable", path, recovery="restore_artifact")
            continue
        if len(body) != payload["byte_count"]:
            issue("receipt.byte_count_mismatch", path, recovery="restore_artifact")
            continue
        normalized = None
        if payload["status"] == 200 and payload["content_type"].split(";", 1)[0].strip().lower() == "application/json":
            normalized = normalize_response(
                body, RawProvenance(SOURCE_KEY, sha, captured, ADAPTER_VERSION), expected_contest=expected,
            )
        try:
            semantic = semantic_payload(normalized.candidate) if normalized and normalized.is_valid else None
            if semantic is not None:
                content_hash(semantic)
        except (ValueError, TypeError, UnicodeError, RecursionError):
            issue("receipt.normalization_failure", path, recovery="reconcile_normalizer_version")
            continue
        receipts[receipt_id] = {"metadata": payload, "semantic": semantic}

    for path in sorted(artifact_paths - referenced_artifacts):
        issue("artifact.orphan", path, severity="warning", recovery="inspect_orphan")

    return receipts

def _audit_outcomes(files, receipts, document, issue):
    outcomes = []
    outcome_receipts = set()
    for path in sorted(files):
        if not path.startswith("outcomes/") or ".pending-" in path:
            continue
        match = re.fullmatch(r"outcomes/([0-9a-f]{32})-([0-9a-f]{32})\.json", path)
        if not match:
            issue("outcome.invalid_name", path)
            continue
        payload = document(path)
        if payload is None:
            continue
        receipt_id = payload.get("receipt_id")
        if not isinstance(receipt_id, str) or receipt_id != match[1] or receipt_id not in receipts:
            issue("outcome.receipt_unavailable", path, recovery="restore_receipt")
            continue
        receipt = receipts[receipt_id]
        if payload.get("raw_sha256") != receipt["metadata"]["sha256"]:
            issue("outcome.raw_hash_mismatch", path)
            continue
        outcome = payload.get("outcome")
        if not isinstance(outcome, str) or outcome not in ACCEPTED | {"quarantined"} or not isinstance(payload.get("issues"), list):
            issue("outcome.invalid_structure", path)
            continue
        if any(not isinstance(i, dict) or not isinstance(i.get("code"), str) or not isinstance(i.get("path"), str) for i in payload["issues"]):
            issue("outcome.invalid_issues", path)
            continue
        if outcome in ACCEPTED:
            semantic = receipt["semantic"]
            if semantic is None or payload["issues"]:
                issue("outcome.not_reproducible", path, recovery="reconcile_normalizer_version")
                continue
            contest = semantic["official_draw_number"]
            if payload.get("canonical_key") != f"mega_sena:official_draw_number:{contest}" or (
                "official_draw_number" in payload and payload["official_draw_number"] != contest
            ) or type(payload.get("revision")) is not int or payload["revision"] < 1:
                issue("outcome.identity_mismatch", path)
                continue
        elif not payload["issues"]:
            issue("outcome.empty_quarantine", path)
            continue
        if outcome == "quarantined":
            issue("capture.quarantined", path, severity="warning", recovery="inspect_quarantine")
        outcome_receipts.add(receipt_id)
        outcomes.append((path, payload))

    for receipt_id in sorted(set(receipts) - outcome_receipts):
        issue("receipt.outcome_missing", f"receipts/{receipt_id}.json", severity="warning", recovery="replay_receipt")

    return outcomes

def _audit_revisions(files, receipts, outcomes, document, issue):
    accepted_outcomes = {
        (p["receipt_id"], p["revision"])
        for _, p in outcomes if p["outcome"] in ACCEPTED
    }
    revision_records = {}
    valid_contests = set()
    materialized_contests = set()
    revision_count = 0
    for path in sorted(files):
        if not path.startswith("revisions/") or ".pending-" in path:
            continue
        match = re.fullmatch(r"revisions/([1-9][0-9]*)\.json", path)
        if not match:
            issue("revision.invalid_name", path)
            continue
        contest = int(match[1])
        materialized_contests.add(contest)
        payload = document(path)
        if payload is None:
            continue
        if type(payload.get("schema_version")) is not int or payload["schema_version"] != 1 or set(payload) != {"schema_version", "revisions"} or not isinstance(payload.get("revisions"), list) or not payload["revisions"]:
            issue("revision.invalid_structure", path)
            continue
        valid = True
        previous_hash = None
        for position, record in enumerate(payload["revisions"], start=1):
            revision_count += 1
            ref = f"{path}#{position}"
            if not isinstance(record, dict) or set(record) != {"revision", "state", "content_sha256", "receipt_id", "payload"}:
                issue("revision.invalid_structure", ref)
                valid = False
                continue
            candidate = record["payload"]
            receipt_id = record["receipt_id"]
            if type(record["revision"]) is not int or record["revision"] != position or record["state"] != "candidate":
                issue("revision.invalid_sequence_or_state", ref)
                valid = False
            if not isinstance(candidate, dict) or candidate.get("official_draw_number") != str(contest) or candidate.get("lottery_slug") != "mega_sena":
                issue("revision.identity_mismatch", ref)
                valid = False
                continue
            if content_hash(candidate) != record["content_sha256"]:
                issue("revision.hash_mismatch", ref, recovery="restore_revision")
                valid = False
                continue
            if previous_hash == record["content_sha256"]:
                issue("revision.redundant_copy", ref, recovery="inspect_evidence")
                valid = False
            previous_hash = record["content_sha256"]
            revision_records[(contest, position)] = record
            if not isinstance(receipt_id, str) or receipt_id not in receipts:
                issue("revision.receipt_unavailable", ref, recovery="restore_receipt")
                valid = False
                continue
            semantic = receipts[receipt_id]["semantic"]
            if semantic is None or content_hash(semantic) != record["content_sha256"]:
                issue("revision.not_reproducible", ref, recovery="reconcile_normalizer_version")
                valid = False
            if (receipt_id, position) not in accepted_outcomes:
                issue("revision.outcome_missing", ref, severity="warning", recovery="replay_receipt")
                valid = False
        if valid:
            valid_contests.add(contest)

    for path, payload in outcomes:
        if payload["outcome"] not in ACCEPTED:
            continue
        semantic = receipts[payload["receipt_id"]]["semantic"]
        contest = int(semantic["official_draw_number"])
        record = revision_records.get((contest, payload["revision"]))
        if record is None or content_hash(semantic) != record["content_sha256"]:
            issue("outcome.revision_mismatch", path, recovery="restore_revision")

    return valid_contests, materialized_contests, revision_count

def _audit_checkpoint(files, snapshot, document, issue):
    state = None
    if "sync-state.json" in files:
        payload = document("sync-state.json")
        if payload is not None:
            try:
                if set(payload) != {"schema_version", "source_key", "anchor", "cursor", "review_next", "cooldown_until"} or type(payload["schema_version"]) is not int or payload["schema_version"] != 1 or payload["source_key"] != SOURCE_KEY:
                    raise ValueError
                state = SyncState(
                    SyncAnchor(**payload["anchor"]), payload["cursor"], payload["review_next"],
                    _instant(payload["cooldown_until"]) if payload["cooldown_until"] else None,
                )
                if state.anchor.last_contest != snapshot.baseline.last_contest or state.anchor.raw_sha256 != snapshot.baseline.expected_sha256:
                    issue("cursor.baseline_mismatch", "sync-state.json", recovery="inspect_checkpoint")
                    state = None
            except (ValueError, KeyError, TypeError, OverflowError):
                issue("cursor.invalid_checkpoint", "sync-state.json", recovery="inspect_checkpoint")
    else:
        issue("cursor.missing", "sync-state.json", severity="warning", recovery="inspect_checkpoint")

    return state

def _audit_runs(files, receipts, outcomes, state, document, issue):
    operational_stops = Counter()
    valid_runs = 0
    for path in sorted(files):
        if not path.startswith("sync-runs/") or ".pending-" in path:
            continue
        if not re.fullmatch(r"sync-runs/[0-9a-f]{32}\.json", path):
            issue("run.invalid_name", path)
            continue
        run = document(path)
        if run is None:
            continue
        try:
            if type(run.get("schema_version")) is not int or run["schema_version"] != 1:
                raise ValueError
            if type(run.get("requests")) is not int or not 0 <= run["requests"] <= 10 or not isinstance(run.get("operations"), list):
                raise ValueError
            if type(run.get("cursor_before")) is not int or type(run.get("cursor_after")) is not int or run["cursor_after"] < run["cursor_before"]:
                raise ValueError
            if _instant(run["finished_at"]) < _instant(run["started_at"]):
                raise ValueError
            if run.get("stop_reason") not in {"caught_up", "budget_exhausted", "collection_stopped", "source_behind_cursor", "cooldown"}:
                raise ValueError
            latest = run.get("latest_observed")
            if latest is not None and (type(latest) is not int or latest < 1):
                raise ValueError
            remaining = max(0, latest - run["cursor_after"]) if latest is not None else None
            if run.get("remaining") != remaining:
                issue("run.remaining_mismatch", path)
            if type(run.get("review_next")) is not int or not 0 < run["review_next"] <= run["cursor_after"] + 1:
                raise ValueError
            requests = 0
            discovery_receipt = None
            discovery_contest = None
            for operation in run["operations"]:
                if not isinstance(operation, dict) or operation.get("phase") not in {"discovery", "forward", "review"}:
                    raise ValueError
                if operation.get("reused_discovery") is not True:
                    requests += 1
                if operation["phase"] == "discovery":
                    if operation.get("contest") is not None:
                        raise ValueError
                elif type(operation.get("contest")) is not int or operation["contest"] < 1:
                    raise ValueError
                if operation.get("outcome") == "failed":
                    if not isinstance(operation.get("code"), str):
                        raise ValueError
                    continue
                receipt_id = operation.get("receipt_id")
                if not isinstance(receipt_id, str) or not any(
                    p == {k: v for k, v in operation.items() if k not in {"phase", "contest", "reused_discovery"}}
                    for _, p in outcomes if p["receipt_id"] == receipt_id
                ):
                    issue("run.outcome_unavailable", path, recovery="inspect_run")
                semantic = receipts.get(receipt_id, {}).get("semantic") if isinstance(receipt_id, str) else None
                if operation["phase"] == "discovery" and operation.get("outcome") in ACCEPTED and semantic is not None:
                    if discovery_receipt is not None:
                        raise ValueError
                    discovery_receipt = receipt_id
                    discovery_contest = int(semantic["official_draw_number"])
                elif semantic is not None and operation.get("contest") != int(semantic["official_draw_number"]):
                    issue("run.contest_mismatch", path)
                if operation.get("reused_discovery") is True and (
                    operation["phase"] == "discovery" or receipt_id != discovery_receipt
                ):
                    issue("run.invalid_discovery_reuse", path)
            if requests != run["requests"]:
                issue("run.request_count_mismatch", path)
            if latest != discovery_contest:
                issue("run.latest_mismatch", path)
            if run["stop_reason"] == "caught_up" and latest != run["cursor_after"]:
                issue("run.false_caught_up", path)
            if state and run["cursor_after"] > state.cursor:
                issue("run.ahead_of_checkpoint", path, recovery="inspect_checkpoint")
            valid_runs += 1
            operational_stops[run["stop_reason"]] += 1
        except (ValueError, TypeError, KeyError, OverflowError):
            issue("run.invalid_structure", path, recovery="inspect_run")

    return operational_stops, valid_runs


def finalize_report(report: dict) -> dict:
    report["issues"] = sorted(report["issues"], key=lambda i: (i["severity"], i["code"], i["path"]))
    counts = Counter(i["severity"] for i in report["issues"])
    report["issue_counts"] = dict(sorted(counts.items()))
    report["status"] = "failed" if counts["error"] else "attention" if counts["warning"] else "healthy"
    plan = {}
    for item in report["issues"]:
        plan.setdefault(item["recovery"], set()).add(item["path"])
    if not counts["error"] and (report["coverage"]["pending_identifiers_to_observed"] or 0) > 0:
        plan["continue_bounded_sync"] = {"sync-state.json"}
    report["recovery_plan"] = [
        {"action": action, "paths": sorted(paths), "automatic": False}
        for action, paths in sorted(plan.items())
    ]
    return report
