"""Snapshots DUBLÊS de metadados; concursos/bytes reais, sem aprovação SQL simulada."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
from types import ModuleType
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.application.audit_sync_postgres import AuditMegaSenaPostgres, SyncAuditRequest
from app.application.historical_content import digest
from app.application.mega_sena_content import VERSION, to_content
from app.application.mega_sena_incremental import CODE_VERSION, POLICY_VERSION
from app.application.persistence import PersistenceError
from app.domain import RawProvenance
from app.ingestion.mega_sena_api import SOURCE_KEY, ADAPTER_VERSION, normalize_response

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 26, tzinfo=timezone.utc)


def snapshot_fixture():
    """Certificado arquivado é só dado para testes puros, não cria banco aprovado."""
    cp, lottery, source, historical_source, baseline, activation, run, batch = [uuid4() for _ in range(8)]
    artifact, history_artifact, receipt, history_receipt, process, observation, draw, revision = [uuid4() for _ in range(8)]
    discovery, forward = uuid4(), uuid4()
    body = (ROOT / "tests/fixtures/mega_sena_api_2955.json").read_bytes()
    raw = (ROOT / "data/raw/mega_sena/mega_sena_resultados.xlsx").read_bytes()
    sha = hashlib.sha256(body).hexdigest()
    content = to_content(normalize_response(body, RawProvenance(SOURCE_KEY, sha, NOW, ADAPTER_VERSION)).candidate)
    coverage = json.loads((ROOT / "docs/data/mega-sena-cobertura-spec-0029.json").read_text(encoding="utf-8"))["coverage"]
    catalog = "b" * 64
    policy = {"max_requests": 1, "review_window": 0, "interval_seconds": 2.0}
    ops = []
    attempts = []
    for ordinal, identifier, phase, contest, reuse, outcome in (
        (1, discovery, "discovery", None, None, "new"),
        (2, forward, "forward", 2955, discovery, "replayed")):
        key = "sync-process:" + digest({"operation": str(identifier), "token": 1})
        ops.append({"id": identifier, "batch_id": batch, "ordinal": ordinal, "phase": phase,
                    "contest": contest, "expected_cursor": 2954, "review_after": None,
                    "reuse_id": reuse, "capture_key": "sync-capture:" + digest(str(identifier)) if reuse is None else None,
                    "receipt_id": receipt, "processing_key": key, "lease_token": 1,
                    "state": "done", "observation_id": observation, "outcome": outcome, "observed_sequence": 2955})
        request_hash = digest({"format": "process-command-v1", "receipt": str(receipt), "adapter": ADAPTER_VERSION,
            "code": CODE_VERSION, "canonicalization": VERSION, "policy": POLICY_VERSION, "catalog": catalog,
            "advance": None, "batch": {"checkpoint_id": str(cp), "expected_cursor": 2954, "lease_token": 1,
                                       "operation_id": str(identifier)}})
        attempts.append({"command_key": key, "processing_run_id": process, "outcome": outcome, "request_hash": request_hash})
    report = {"report_version": "mega-sena-sql-sync-v1", "batch_id": str(batch), "status": "completed",
              "stop_reason": "caught_up", "cursor_before": 2954, "cursor_after": 2955, "review_next": 2955,
              "latest_observed": 2955, "request_slots_used": 1, "policy": policy, "remaining": 0,
              "cooldown_until": None, "operations": [{"ordinal": o["ordinal"], "phase": o["phase"],
                "contest": o["contest"], "observed": 2955, "outcome": o["outcome"], "reused_discovery": o["reuse_id"] is not None,
                "http_status": 200, "receipt_id": str(receipt), "observation_id": str(observation)} for o in ops]}
    s = {"at": NOW, "truncated": [], "content_errors": {}, "current_catalog": catalog,
         "checkpoint": {"id": cp, "lottery_id": lottery, "source_id": source, "baseline_id": baseline,
            "stream_key": "mega_sena_forward", "strategy": "official_numeric_sequence", "cursor_sequence": 2955,
            "review_next": 2955, "lease_token": 1, "lease_until": NOW, "cooldown_until": None},
         "source": {"slug": "mega_sena", "key": SOURCE_KEY},
         "baseline": {"id": baseline, "source_id": historical_source, "artifact_id": history_artifact,
            "materialization_status": "loaded", "last_sequence": 2954, "manifest_hash": coverage["expected_records_manifest_sha256"]},
         "activation": {"id": activation, "baseline_id": baseline, "target_source_id": source,
            "lottery_id": lottery, "stream_key": "mega_sena_forward", "historical_source_id": historical_source,
            "historical_receipt_id": history_receipt, "coverage_report": coverage, "coverage_hash": digest(coverage),
            "historical_plan_hash": coverage["plan_hash"]},
         "historical_run": {"id": run, "source_id": historical_source, "mode": "historical_import", "status": "completed"},
         "artifacts": [{"id": identifier, "object_key": key, "sha256": hashlib.sha256(data).hexdigest(),
                         "byte_count": len(data), "storage_state": "available"}
                        for identifier, key, data in ((artifact, "TEST_ONLY: json", body), (history_artifact, "TEST_ONLY: xlsx", raw))],
         "receipts": [{"id": receipt, "source_id": source, "lottery_id": lottery, "artifact_id": artifact,
            "capture_kind": "http", "byte_count": len(body), "http_status": 200, "content_type": "application/json", "captured_at": NOW},
            {"id": history_receipt, "source_id": historical_source, "artifact_id": history_artifact,
             "capture_kind": "legacy_import", "byte_count": len(raw)}],
         "processing": [{"id": process, "lottery_id": lottery, "receipt_id": receipt, "status": "completed",
            "adapter_version": ADAPTER_VERSION, "canonicalization_version": VERSION, "catalog_fingerprint": catalog}],
         "observations": [{"id": observation, "processing_run_id": process, "lottery_id": lottery,
            "draw_id": draw, "revision_id": revision, "decision": "new", "semantic_hash": digest(content), "row_locator": "/"}],
         "revisions": [{"id": revision, "draw_id": draw, "seal_state": "sealed", "content_hash": digest(content)}],
         "contents": {revision: content},
         "identities": [{"draw_id": draw, "active": True, "assurance": "official", "value": "2955"}],
         "steps": [{"sequence_no": 2955, "observation_id": observation, "lease_token": 1}],
         "captures": [{"capture_key": ops[0]["capture_key"], "receipt_id": receipt, "outcome": "response", "ordinal": 1,
            "lottery_id": lottery, "requested_identity": None,
            "request_hash": digest({"format": "capture-command-v1", "source": SOURCE_KEY, "contest": None})}],
         "operations": ops, "attempts": attempts,
         "batches": [{"id": batch, "cursor_start": 2954, "review_start": 2955, "policy": policy, "review_targets": [],
            "latest_sequence": 2955, "lease_token": 1, "status": "completed", "stop_reason": "caught_up", "report": report,
            "catalog_fingerprint": catalog, "request_hash": digest({"version": "spec-0031-v1", "checkpoint": str(cp), "policy": policy})}]}
    return s, {"TEST_ONLY: json": body, "TEST_ONLY: xlsx": raw}


def audit(snapshot, bodies):
    class Reader:
        def read(self, request): return snapshot
    class Storage:
        def read(self, key, sha, size): return bodies[key]
    return AuditMegaSenaPostgres(Reader(), Storage()).execute(SyncAuditRequest(snapshot["checkpoint"]["id"]))


@pytest.mark.parametrize("field,value", [("checkpoint_id", "bad"), ("max_batches", 0), ("max_batches", 201),
    ("max_batches", True), ("max_steps", 0), ("max_steps", 5001), ("max_steps", 1.5)])
def test_request_validation(field, value):
    with pytest.raises(ValueError): replace(SyncAuditRequest(uuid4()), **{field: value})


def test_real_bytes_and_consistent_metadata_are_deterministic_without_mutation():
    s, bodies = snapshot_fixture()
    before = deepcopy(s)
    report = audit(s, bodies)
    assert report["status"] == "healthy", report["issues"]
    assert report == audit(s, bodies)
    assert s == before


@pytest.mark.parametrize("mutate,code", [
    (lambda s: s["activation"].update(coverage_hash="a" * 64), "baseline_coverage_reference_invalid"),
    (lambda s: s.update(activation=None), "approved_baseline_missing"),
    (lambda s: s["checkpoint"].update(cursor_sequence=3071), "cursor_without_matching_steps"),
    (lambda s: s["steps"][0].update(sequence_no=2956), "step_sequence_gap_or_outside_cursor"),
    (lambda s: s["checkpoint"].update(review_next=1), "review_pointer_outside_coverage"),
    (lambda s: s["batches"][0]["report"].update(cursor_after=3071), "terminal_summary_mismatch"),
    (lambda s: s["operations"][1].update(reuse_id=uuid4()), "discovery_reuse_mismatch"),
    (lambda s: s["operations"][1].update(contest=3071), "forward_noncontiguous"),
    (lambda s: s["attempts"][0].update(request_hash="a" * 64), "operation_processing_request_mismatch"),
    (lambda s: s["attempts"][0].update(outcome="quarantined"), "operation_processing_ledger_mismatch"),
    (lambda s: s["contents"].clear(), "relational_content_invalid"),
    (lambda s: s["identities"][0].update(active=False), "observation_identity_mismatch"),
    (lambda s: s["processing"][0].update(receipt_id=uuid4()), "observation_processing_context_mismatch"),
    (lambda s: s["captures"][0].update(requested_identity="3071"), "capture_context_mismatch"),
    (lambda s: s["operations"][1].update(lease_token=2), "operation_token_ahead_of_batch"),
    (lambda s: s["operations"][1].update(phase="review", review_after=2955), "review_rotation_mismatch"),
])
def test_corrupt_snapshot_is_diagnosed_not_fixed(mutate, code):
    s, bodies = snapshot_fixture()
    mutate(s)
    before = deepcopy(s)
    report = audit(s, bodies)
    assert report["status"] == "inconsistent"
    assert code in report["issue_counts"]
    assert s == before


def test_old_batch_uses_its_own_end_cursor_even_when_checkpoint_advanced():
    s, bodies = snapshot_fixture()
    # Recorte parcial simulado: não cria JSON fictício 2956 nem declara cobertura.
    s["checkpoint"]["cursor_sequence"] = 2956
    s["truncated"] = ["steps"]
    report = audit(s, bodies)
    assert "terminal_summary_mismatch" not in report["issue_counts"]
    assert report["status"] == "incomplete"


def test_corrupt_bytes_cannot_be_hidden_by_storage_double():
    s, bodies = snapshot_fixture()
    bodies["TEST_ONLY: json"] = b"TEST_ONLY: corruption"
    assert "artifact_bytes_mismatch" in audit(s, bodies)["issue_counts"]


def test_blocked_catalog_warns_without_destroying_historical_diagnosis():
    s, bodies = snapshot_fixture()
    s["current_catalog"] = None
    report = audit(s, bodies)
    assert report["status"] == "attention"
    assert all(i["severity"] == "warning" for i in report["issues"])
    assert not report["collection_authorized"]


@pytest.mark.parametrize("capture_state,code", [
    ("none", "operation_not_started"), ("unresolved", "operation_capture_unresolved"),
    ("transport", "operation_transport_failed"), ("receipt", "operation_receipt_unattached")])
def test_pending_operation_states_do_not_become_corruption_or_trigger_recovery(capture_state, code):
    s, bodies = snapshot_fixture()
    s["checkpoint"].update(cursor_sequence=2954)
    s["steps"] = []
    s["observations"] = []
    s["processing"] = []
    s["attempts"] = []
    s["batches"][0].update(status="running", report=None, latest_sequence=None)
    s["operations"] = s["operations"][:1]
    s["operations"][0].update(state="pending", observation_id=None, processing_key=None, receipt_id=None,
                                outcome=None, observed_sequence=None, lease_token=None)
    if capture_state == "none":
        s["captures"] = []
    elif capture_state in ("unresolved", "transport"):
        s["captures"][0].update(receipt_id=None, outcome="running" if capture_state == "unresolved" else "transport_error")
    before = deepcopy(s)
    report = audit(s, bodies)
    assert report["status"] == "attention", report["issues"]
    assert code in report["issue_counts"]
    assert s == before


def test_active_lease_is_warning_not_proof_of_corruption_or_liveness():
    s, bodies = snapshot_fixture()
    s["batches"][0].update(status="running", report=None)
    s["checkpoint"]["lease_until"] = NOW + timedelta(seconds=60)
    report = audit(s, bodies)
    assert report["status"] == "attention"
    assert "running_active" in report["issue_counts"]
    assert {"action": "wait_and_audit_again", "automatic": False} in report["recommendations"]


def test_snapshot_errors_are_propagated_without_storage_access():
    class Reader:
        def read(self, request): raise PersistenceError("audit_database_unavailable")
    with pytest.raises(PersistenceError, match="audit_database_unavailable"):
        AuditMegaSenaPostgres(Reader(), object()).execute(SyncAuditRequest(uuid4()))


def test_cli_missing_configuration_and_invalid_limits(capsys, monkeypatch):
    from app.interfaces.audit_sync_postgres import main
    monkeypatch.delenv("LOTTOBRAIN_PG_AUDIT_DSN", raising=False)
    args = ["--checkpoint", str(uuid4()), "--object-root", "TEST_ONLY: absent"]
    assert main(args) == 1
    assert json.loads(capsys.readouterr().out)["error"] == "audit_database_not_configured"
    assert main(args + ["--max-batches", "201"]) == 1
    assert json.loads(capsys.readouterr().out)["error"] == "invalid_arguments"


def test_cli_does_not_expose_infrastructure_secrets(capsys, monkeypatch):
    from app.interfaces.audit_sync_postgres import main
    monkeypatch.setenv("LOTTOBRAIN_PG_AUDIT_DSN", "TEST_ONLY: secret")
    module = ModuleType("app.infrastructure.postgres.sync_audit")
    class Reader:
        def __init__(self, **kwargs): pass
        def read(self, request): raise PersistenceError("SECRET DSN SQL PATH")
    module.PgSyncAuditReader = Reader
    with patch.dict(sys.modules, {module.__name__: module}):
        assert main(["--checkpoint", str(uuid4()), "--object-root", "TEST_ONLY: absent"]) == 1
    assert json.loads(capsys.readouterr().out) == {"error": "audit_unavailable"}
