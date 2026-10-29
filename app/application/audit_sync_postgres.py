"""Auditoria sem efeitos: snapshot SQL fechado, depois evidência em bytes."""
from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
from typing import Protocol
from uuid import UUID

from app.application.activate_mega_sena_baseline import STREAM_KEY, require_eligible_coverage
from app.application.historical_content import digest
from app.application.mega_sena_content import to_content
from app.application.mega_sena_content import VERSION as JSON_CONTRACT
from app.application.mega_sena_incremental import CODE_VERSION as PROCESS_CODE, POLICY_VERSION as PROCESS_POLICY
from app.application.persistence import PersistenceError
from app.application.sync_mega_sena import SyncPolicy
from app.application.sync_postgres import CODE_VERSION, review_targets
from app.domain import RawProvenance
from app.ingestion.mega_sena_api import SOURCE_KEY, ADAPTER_VERSION, normalize_response


@dataclass(frozen=True)
class SyncAuditRequest:
    checkpoint_id: UUID
    max_batches: int = 100
    max_steps: int = 5000

    def __post_init__(self):
        if not isinstance(self.checkpoint_id, UUID):
            raise ValueError("checkpoint UUID necessário")
        for value, upper in ((self.max_batches, 200), (self.max_steps, 5000)):
            if type(value) is not int or not 1 <= value <= upper:
                raise ValueError("limite de auditoria inválido")


class SyncAuditReader(Protocol):
    def read(self, request: SyncAuditRequest) -> dict: ...


class AuditMegaSenaPostgres:
    def __init__(self, reader: SyncAuditReader, storage):
        self.reader, self.storage = reader, storage

    def execute(self, request: SyncAuditRequest):
        if not isinstance(request, SyncAuditRequest):
            raise ValueError("pedido de auditoria necessário")
        return _Audit(self.reader.read(request), self.storage, request).run()


class _Audit:
    def __init__(self, snapshot, storage, request):
        self.s, self.storage, self.request = snapshot, storage, request
        self.issues, self.batches, self.objects = [], [], []
        self.bodies, self.normalized = {}, {}
        self.cp = snapshot["checkpoint"]
        for name in ("receipts", "artifacts", "observations", "processing", "revisions"):
            setattr(self, name, {row["id"]: row for row in snapshot.get(name, [])})
        self.attempts = {row["command_key"]: row for row in snapshot.get("attempts", [])}
        self.steps = {row["sequence_no"]: row for row in snapshot.get("steps", [])}
        self.captures = defaultdict(list)
        for capture in snapshot.get("captures", []):
            self.captures[capture["capture_key"]].append(capture)

    def issue(self, code, reference=None, severity="error"):
        item = {"code": code, "severity": severity}
        if reference is not None:
            item["reference"] = str(reference)
        if item not in self.issues:
            self.issues.append(item)

    def run(self):
        if self.cp is None:
            self.issue("checkpoint_not_found")
            return self.report("not_found")
        self.baseline()
        self.verify_bytes()
        for observation in self.observations.values():
            self.observation(observation)
        self.continuity()
        for batch in self.s.get("batches", []):
            self.batch(batch)
        if self.s.get("current_catalog") is None:
            self.issue("source_not_qualified_for_collection", severity="warning")
        if self.cp["cooldown_until"] and self.cp["cooldown_until"] > self.s["at"]:
            self.issue("source_cooldown", severity="warning")
        for part in self.s["truncated"]:
            self.issue("snapshot_limit_" + part, severity="warning")
        status = ("inconsistent" if any(i["severity"] == "error" for i in self.issues)
                  else "incomplete" if self.s["truncated"]
                  else "attention" if self.issues else "healthy")
        return self.report(status)

    def baseline(self):
        cp, baseline, activation = self.cp, self.s.get("baseline"), self.s.get("activation")
        source = self.s.get("source") or {}
        if (source.get("slug") != "mega_sena" or source.get("key") != SOURCE_KEY
                or cp["stream_key"] != STREAM_KEY or cp["strategy"] != "official_numeric_sequence"):
            self.issue("checkpoint_context_mismatch", cp["id"])
        if not baseline or not activation:
            self.issue("approved_baseline_missing", cp["id"])
            return
        historical = self.s.get("historical_run") or {}
        receipt = self.receipts.get(activation["historical_receipt_id"], {})
        report = activation["coverage_report"]
        try:
            require_eligible_coverage(report)
            valid_report = (digest(report) == activation["coverage_hash"]
                            and report["expected_records_manifest_sha256"] == baseline["manifest_hash"]
                            and report["plan_hash"] == activation["historical_plan_hash"])
        except (PersistenceError, KeyError, TypeError, ValueError):
            valid_report = False
        if not valid_report:
            self.issue("baseline_coverage_reference_invalid", baseline["id"])
        if (baseline["materialization_status"] != "loaded" or baseline["id"] != activation["baseline_id"]
                or activation["target_source_id"] != cp["source_id"]
                or activation["lottery_id"] != cp["lottery_id"]
                or activation["stream_key"] != cp["stream_key"]
                or baseline["source_id"] != activation["historical_source_id"]
                or historical.get("source_id") != baseline["source_id"]
                or historical.get("status") != "completed" or historical.get("mode") != "historical_import"
                or receipt.get("source_id") != baseline["source_id"]
                or receipt.get("capture_kind") != "legacy_import"
                or receipt.get("artifact_id") != baseline["artifact_id"]):
            self.issue("baseline_activation_link_mismatch", baseline["id"])
        artifact = self.artifacts.get(baseline["artifact_id"], {})
        if artifact.get("sha256") != report.get("raw_sha256"):
            self.issue("baseline_raw_reference_mismatch", baseline["id"])

    def verify_bytes(self):
        for identifier, artifact in sorted(self.artifacts.items(), key=lambda pair: str(pair[0])):
            code = None
            if artifact["storage_state"] != "available":
                code = "artifact_not_available"
            else:
                try:
                    body = self.storage.read(artifact["object_key"], artifact["sha256"], artifact["byte_count"])
                    if (not isinstance(body, bytes) or len(body) != artifact["byte_count"]
                            or hashlib.sha256(body).hexdigest() != artifact["sha256"]):
                        code = "artifact_bytes_mismatch"
                    else:
                        self.bodies[identifier] = body
                except PersistenceError as error:
                    code = {"evidence_missing": "artifact_bytes_missing",
                            "artifact_hash_mismatch": "artifact_bytes_mismatch"}.get(error.code, "artifact_read_failed")
                except OSError:
                    code = "artifact_read_failed"
            if code:
                self.issue(code, identifier)
            self.objects.append({"artifact_id": str(identifier), "sha256": artifact["sha256"],
                                 "byte_count": artifact["byte_count"], "verified": code is None})
        for receipt in self.receipts.values():
            artifact = self.artifacts.get(receipt["artifact_id"])
            if not artifact or receipt["byte_count"] != artifact["byte_count"]:
                self.issue("receipt_artifact_mismatch", receipt["id"])

    def observation(self, observation):
        identifier = observation["id"]
        processing = self.processing.get(observation["processing_run_id"], {})
        receipt = self.receipts.get(processing.get("receipt_id"), {})
        if (processing.get("status") != "completed" or processing.get("lottery_id") != self.cp["lottery_id"]
                or receipt.get("source_id") != self.cp["source_id"]
                or observation["lottery_id"] != self.cp["lottery_id"]
                or processing.get("adapter_version") != ADAPTER_VERSION
                or processing.get("canonicalization_version") != JSON_CONTRACT):
            self.issue("observation_processing_context_mismatch", identifier)
        if observation["revision_id"] is None:
            if observation["decision"] != "quarantined":
                self.issue("observation_outcome_mismatch", identifier)
            return
        revision = self.revisions.get(observation["revision_id"], {})
        content = self.s["contents"].get(observation["revision_id"])
        if (not content or revision.get("seal_state") != "sealed"
                or revision.get("draw_id") != observation["draw_id"]
                or digest(content) != observation["semantic_hash"]
                or revision.get("content_hash") != observation["semantic_hash"]):
            self.issue("relational_content_invalid", identifier)
        identities = [i for i in self.s.get("identities", []) if i["draw_id"] == observation["draw_id"]
                      and i["active"] and i["assurance"] == "official"]
        if len(identities) != 1 or not content or identities[0]["value"] != content["identity"]:
            self.issue("observation_identity_mismatch", identifier)
        # Releitura/normalização pura: bytes não são reprocessados no writer.
        body = self.bodies.get(receipt.get("artifact_id"))
        if body is not None:
            if receipt["id"] not in self.normalized:
                normalized = normalize_response(body, RawProvenance(
                    SOURCE_KEY, self.artifacts[receipt["artifact_id"]]["sha256"],
                    receipt["captured_at"], ADAPTER_VERSION))
                self.normalized[receipt["id"]] = to_content(normalized.candidate) if normalized.is_valid else None
            incoming = self.normalized[receipt["id"]]
            if (receipt["http_status"] != 200 or not incoming
                    or receipt["content_type"].split(";", 1)[0].strip().lower() != "application/json"
                    or digest(incoming) != observation["semantic_hash"]):
                self.issue("raw_observation_mismatch", identifier)

    def continuity(self):
        baseline = self.s.get("baseline")
        if not baseline:
            return
        anchor, cursor = baseline["last_sequence"], self.cp["cursor_sequence"]
        sequences = sorted(self.steps)
        # Sem criar range proporcional a um cursor potencialmente corrompido.
        if cursor < anchor or any(n != anchor + 1 + i for i, n in enumerate(sequences)):
            self.issue("step_sequence_gap_or_outside_cursor", self.cp["id"])
        if "steps" not in self.s["truncated"] and len(sequences) != cursor - anchor:
            self.issue("cursor_without_matching_steps", self.cp["id"])
        if sequences and sequences[-1] > cursor:
            self.issue("step_sequence_gap_or_outside_cursor", self.cp["id"])
        if not anchor < self.cp["review_next"] <= cursor + 1:
            self.issue("review_pointer_outside_coverage", self.cp["id"])
        for sequence, step in self.steps.items():
            observation = self.observations.get(step["observation_id"], {})
            content = self.s["contents"].get(observation.get("revision_id"), {})
            if not observation.get("revision_id") or content.get("identity") != str(sequence):
                self.issue("step_observation_mismatch", sequence)
            if step["lease_token"] > self.cp["lease_token"]:
                self.issue("step_token_ahead_of_checkpoint", sequence)
            if not any(a["processing_run_id"] == observation.get("processing_run_id")
                       and a["outcome"] != "quarantined" for a in self.attempts.values()):
                self.issue("step_processing_ledger_missing", sequence)

    def operation(self, op, batch, operations):
        identifier, receipt_id = op["id"], op["receipt_id"]
        capture_state = "reused_discovery" if op["reuse_id"] else "not_started"
        if op["reuse_id"]:
            origin = next((o for o in operations if o["id"] == op["reuse_id"]), {})
            if (origin.get("phase") != "discovery" or origin.get("state") != "done"
                    or origin.get("observed_sequence") != op["contest"]
                    or receipt_id is not None and receipt_id != origin.get("receipt_id")):
                self.issue("discovery_reuse_mismatch", identifier)
            receipt_id = receipt_id or origin.get("receipt_id")
        else:
            captures = self.captures[op["capture_key"]]
            expected_key = "sync-capture:" + digest(str(identifier))
            if op["capture_key"] != expected_key:
                self.issue("capture_key_mismatch", identifier)
            if len(captures) > 1:
                self.issue("capture_attempt_multiplicity", identifier)
            elif captures:
                capture = captures[0]
                capture_state = ("receipt_committed" if capture["receipt_id"] else
                                 "transport_failed" if capture["outcome"] == "transport_error" else "capture_unresolved")
                expected_hash = digest({"format": "capture-command-v1", "source": SOURCE_KEY, "contest": op["contest"]})
                if (capture["request_hash"] != expected_hash
                        or capture["requested_identity"] != (str(op["contest"]) if op["contest"] else None)
                        or capture["lottery_id"] != self.cp["lottery_id"] or capture["ordinal"] != 1
                        or receipt_id is not None and capture["receipt_id"] != receipt_id):
                    self.issue("capture_context_mismatch", identifier)
                if receipt_id is None and capture["receipt_id"]:
                    capture_state = "receipt_unattached"
                receipt_id = receipt_id or capture["receipt_id"]
            if receipt_id and not captures:
                self.issue("receipt_without_capture_command", identifier)
        receipt = self.receipts.get(receipt_id, {})
        if receipt_id and (not receipt or receipt["source_id"] != self.cp["source_id"]
                           or receipt["lottery_id"] != self.cp["lottery_id"] or receipt["capture_kind"] != "http"):
            self.issue("operation_receipt_mismatch", identifier)
        observation = self.observations.get(op["observation_id"], {})
        attempt = self.attempts.get(op["processing_key"])
        if op["state"] == "done":
            processing = self.processing.get(observation.get("processing_run_id"), {})
            if (not attempt or attempt["processing_run_id"] != observation.get("processing_run_id")
                    or attempt["outcome"] != op["outcome"] or processing.get("receipt_id") != op["receipt_id"]
                    or observation.get("row_locator") != "/"):
                self.issue("operation_processing_ledger_mismatch", identifier)
            expected_request = digest({"format": "process-command-v1", "receipt": str(op["receipt_id"]),
                "adapter": ADAPTER_VERSION, "code": PROCESS_CODE, "canonicalization": JSON_CONTRACT,
                "policy": PROCESS_POLICY, "catalog": batch["catalog_fingerprint"], "advance": None,
                "batch": {"checkpoint_id": str(self.cp["id"]), "expected_cursor": op["expected_cursor"],
                          "lease_token": op["lease_token"], "operation_id": str(identifier)}})
            if (attempt and attempt["request_hash"] != expected_request
                    or processing.get("catalog_fingerprint") != batch["catalog_fingerprint"]):
                self.issue("operation_processing_request_mismatch", identifier)
            if op["processing_key"] != "sync-process:" + digest({"operation": str(identifier), "token": op["lease_token"]}):
                self.issue("processing_key_mismatch", identifier)
            if op["lease_token"] > batch["lease_token"]:
                self.issue("operation_token_ahead_of_batch", identifier)
            accepted = observation.get("revision_id") is not None
            if accepted != (op["outcome"] != "quarantined"):
                self.issue("operation_outcome_mismatch", identifier)
            content = self.s["contents"].get(observation.get("revision_id"), {})
            if accepted and (content.get("identity") != str(op["observed_sequence"])
                             or op["phase"] != "discovery" and op["contest"] != op["observed_sequence"]):
                self.issue("operation_identity_mismatch", identifier)
            if accepted and op["phase"] == "forward" and "steps" not in self.s["truncated"]:
                step = self.steps.get(op["contest"], {})
                if step.get("observation_id") != op["observation_id"] or step.get("lease_token") != op["lease_token"]:
                    self.issue("forward_step_mismatch", identifier)
            state = "confirmed_quarantine" if not accepted else "confirmed"
        else:
            if attempt:
                self.issue("pending_operation_has_committed_processing", identifier)
            state = "interpretation_pending" if receipt_id else capture_state
            self.issue("operation_" + (capture_state if capture_state == "receipt_unattached" else state),
                       identifier, "warning")
        return {"operation_id": str(identifier), "ordinal": op["ordinal"], "phase": op["phase"],
                "contest": op["contest"], "state": state, "capture_state": capture_state,
                "receipt_id": str(receipt_id) if receipt_id else None,
                "observation_id": str(op["observation_id"]) if op["observation_id"] else None}

    def batch(self, batch):
        identifier = batch["id"]
        operations = sorted((o for o in self.s.get("operations", []) if o["batch_id"] == identifier),
                            key=lambda o: o["ordinal"])
        cursor, review = batch["cursor_start"], batch["review_start"]
        slots, latest, review_count, pending = 0, None, 0, False
        try:
            SyncPolicy(**batch["policy"])
            expected_hash = digest({"version": CODE_VERSION, "checkpoint": str(self.cp["id"]), "policy": batch["policy"]})
            if batch["request_hash"] != expected_hash:
                self.issue("batch_request_hash_mismatch", identifier)
            baseline = self.s.get("baseline")
            if baseline and batch["review_targets"] != review_targets(baseline["last_sequence"], cursor, review,
                                                                      batch["policy"]["review_window"]):
                self.issue("batch_review_window_mismatch", identifier)
        except (TypeError, ValueError):
            self.issue("batch_policy_invalid", identifier)
        results = []
        for ordinal, op in enumerate(operations, 1):
            if op["ordinal"] != ordinal or op["expected_cursor"] != cursor or pending:
                self.issue("operation_order_or_cursor_mismatch", op["id"])
            if (ordinal == 1) != (op["phase"] == "discovery"):
                self.issue("discovery_order_mismatch", op["id"])
            slots += op["reuse_id"] is None
            results.append(self.operation(op, batch, operations))
            accepted = op["state"] == "done" and op["outcome"] != "quarantined"
            if op["state"] == "pending":
                pending = True
            if op["phase"] == "discovery" and accepted:
                latest = op["observed_sequence"]
            if op["phase"] == "forward":
                if op["contest"] != cursor + 1 or latest is None or op["contest"] > latest:
                    self.issue("forward_noncontiguous", op["id"])
                if accepted:
                    cursor += 1
            if op["phase"] == "review":
                targets = batch["review_targets"]
                if (review_count >= len(targets) or op["contest"] != targets[review_count]
                        or op["review_after"] != targets[(review_count + 1) % len(targets)]):
                    self.issue("review_rotation_mismatch", op["id"])
                if accepted:
                    review = op["review_after"]
                review_count += 1
        if slots > batch["policy"].get("max_requests", 0):
            self.issue("batch_budget_exceeded", identifier)
        if latest != batch["latest_sequence"]:
            self.issue("discovery_frontier_mismatch", identifier)
        if cursor > self.cp["cursor_sequence"]:
            self.issue("batch_ahead_of_checkpoint", identifier)
        if self.s.get("current_catalog") != batch["catalog_fingerprint"]:
            self.issue("batch_catalog_changed", identifier, "warning")
        if batch["status"] == "running":
            if cursor != self.cp["cursor_sequence"]:
                self.issue("running_batch_checkpoint_mismatch", identifier)
            lease_active = self.cp["lease_until"] is not None and self.cp["lease_until"] > self.s["at"]
            situation = "running_active" if lease_active and self.cp["lease_token"] == batch["lease_token"] else "running_interrupted"
            self.issue(situation, identifier, "warning")
            if operations and not pending:
                self.issue("batch_summary_or_next_operation_pending", identifier, "warning")
        else:
            situation = batch["status"]
            expected = {"report_version": "mega-sena-sql-sync-v1", "batch_id": str(identifier),
                        "status": batch["status"], "stop_reason": batch["stop_reason"],
                        "cursor_before": batch["cursor_start"], "cursor_after": cursor, "review_next": review,
                        "latest_observed": latest, "request_slots_used": slots, "policy": batch["policy"],
                        "remaining": max(0, latest - cursor) if latest is not None else None,
                        "operations": [{"ordinal": o["ordinal"], "phase": o["phase"], "contest": o["contest"],
                            "observed": o["observed_sequence"], "outcome": o["outcome"],
                            "reused_discovery": o["reuse_id"] is not None,
                            "http_status": self.receipts.get(o["receipt_id"], {}).get("http_status"),
                            "receipt_id": str(o["receipt_id"]) if o["receipt_id"] else None,
                            "observation_id": str(o["observation_id"]) if o["observation_id"] else None} for o in operations]}
            saved = batch["report"] or {}
            if any(saved.get(k) != v for k, v in expected.items()):
                self.issue("terminal_summary_mismatch", identifier)
            if (batch["status"] == "completed" and (pending or batch["stop_reason"] not in ("caught_up", "budget_exhausted"))
                    or batch["stop_reason"] == "caught_up" and cursor != latest):
                self.issue("terminal_decision_mismatch", identifier)
            if batch["status"] == "stopped":
                self.issue("batch_stopped", identifier, "warning")
        self.batches.append({"batch_id": str(identifier), "status": batch["status"], "situation": situation,
                             "cursor_start": batch["cursor_start"], "cursor_verified_at_end": cursor,
                             "request_slots_used": slots, "operations": results})

    def report(self, status):
        issues = sorted(self.issues, key=lambda i: (i["code"], i.get("reference", "")))
        codes = {i["code"] for i in issues}
        actions = set()
        if any(i["severity"] == "error" for i in issues):
            actions.add("investigate_evidence_without_mutation")
        if self.s["truncated"]:
            actions.add("review_audit_limits_before_full_diagnosis")
        if codes & {"running_active", "source_cooldown"}:
            actions.add("wait_and_audit_again")
        if "running_interrupted" in codes:
            actions.add("review_same_command_recovery_manually")
        if "operation_capture_unresolved" in codes:
            actions.add("investigate_capture_without_reissuing_http")
        return {"report_version": "mega-sena-sql-sync-audit-v1", "status": status,
                "snapshot_at": self.s["at"].isoformat(), "checkpoint_id": str(self.request.checkpoint_id),
                "read_only": True, "scope": "approved_baseline_reference_and_incremental_sync",
                "limits": {"max_batches": self.request.max_batches, "max_steps": self.request.max_steps},
                "truncated": self.s["truncated"], "cursor_claimed": self.cp["cursor_sequence"] if self.cp else None,
                "steps_checked": len(self.steps), "batches": self.batches, "artifacts": self.objects,
                "issue_counts": dict(sorted(Counter(i["code"] for i in issues).items())), "issues": issues,
                "recommendations": [{"action": a, "automatic": False} for a in sorted(actions)],
                "collection_authorized": False, "current_provider_coverage_claimed": False}
