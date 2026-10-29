"""Aprovação explícita de cobertura histórica; sem SQL, HTTP ou configuração global."""
from dataclasses import dataclass
import re

from app.application.historical_import import XLSX_SOURCE, restore_history
from app.application.persistence import command_key, PersistenceError, transact

POLICY_VERSION = "mega-sena-baseline-activation-v1"
STREAM_KEY = "mega_sena_forward"


@dataclass(frozen=True)
class BaselineRequest:
    command: str
    history_key: str
    expected_plan_hash: str
    approval_reference: str

    def __post_init__(self):
        command_key(self.command)
        command_key(self.history_key)
        if not isinstance(self.expected_plan_hash,str) or not re.fullmatch(r"[0-9a-f]{64}",self.expected_plan_hash):
            raise ValueError("hash esperado do plano deve ser SHA-256")
        reference = self.approval_reference
        if not isinstance(reference,str) or not 1 <= len(reference) <= 512 or reference != reference.strip() or any(ord(c) < 32 for c in reference):
            raise ValueError("referência de aprovação explícita, sem controles, entre 1 e 512 caracteres")


def require_eligible_coverage(report):
    if report["run_status"] != "completed" or report["qualified"] is not True:
        raise PersistenceError("baseline_not_eligible")
    if (report["first_contest"],report["last_contest"],report["expected_records"],report["verified_records"]) != (1,2954,2954,2954):
        raise PersistenceError("baseline_not_eligible")


class ActivateMegaSenaBaseline:
    def __init__(self, units, storage):
        self.units, self.storage = units, storage

    def execute(self, request: BaselineRequest):
        if not isinstance(request,BaselineRequest):
            raise ValueError("pedido de baseline explícito necessário")
        saved = transact(self.units,lambda unit:unit.history.describe(XLSX_SOURCE,request.history_key))
        body = self.storage.read(saved["object_key"],saved["sha256"],saved["byte_count"])
        plan = restore_history(body,saved["manifest"])
        if plan.fingerprint != request.expected_plan_hash:
            raise PersistenceError("historical_manifest_mismatch")
        # Nenhum relatório do chamador autoriza promoção: o repositório reaudita
        # o banco na mesma transação que cria baseline, vínculo e checkpoint.
        return transact(self.units,lambda unit:unit.baselines.activate(request,plan))
