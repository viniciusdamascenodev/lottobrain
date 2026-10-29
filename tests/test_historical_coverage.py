"""Avaliador puro: snapshot mínimo EM MEMÓRIA com conteúdo de uma linha real.

Os identificadores são dublês locais, não resultados ou evidência de carga SQL.
O plano reduzido só existe nestes testes; o importador exige as 2.954 linhas.
"""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.application.historical_content import digest
from app.application.historical_coverage import coverage_report
from app.application.historical_import import CODE_VERSION, prepare_history_file
from app.application.mega_sena_bridge import POLICY_VERSION


@pytest.fixture(scope="module")
def real_plan():
    return prepare_history_file(Path(__file__).resolve().parents[1]/"data/raw/mega_sena/mega_sena_resultados.xlsx")


@pytest.fixture
def snapshot(real_plan):
    row = real_plan.rows[0]
    manifest = real_plan.manifest
    manifest["records_manifest_sha256"] = digest([{"locator":row.locator,"contest":row.contest,
        "content_hash":digest(row.content),"evidence_hash":digest(row.evidence)}])
    plan = SimpleNamespace(rows=(row,),adapter_version=real_plan.adapter_version,manifest=manifest,
                           fingerprint=real_plan.fingerprint,sha256=real_plan.sha256)
    registration = {"run_id":"unit-test-run","receipt_id":"unit-test-receipt",
                    "request_hash":digest("unit-test-request"),"catalog_fingerprint":digest("unit-test-catalog")}
    command = "historical-row:"+digest({"run":registration["run_id"],"locator":row.locator})
    observation = {"row_locator":row.locator,"decision":"new","processing_run_id":"unit-test-processing",
        "draw_id":"unit-test-draw","revision_id":"unit-test-revision","latest_candidate_revision_id":"unit-test-revision",
        "published_revision_id":None,"code_version":CODE_VERSION,"adapter_version":plan.adapter_version,
        "catalog_fingerprint":registration["catalog_fingerprint"],"validation_policy_version":f"{POLICY_VERSION}:{plan.fingerprint}",
        "canonicalization_version":row.content["schema_version"],"seal_state":"sealed","semantic_hash":digest(row.content),
        "diagnostic_payload":{"schema_version":"historical-import-observation-v1","plan_hash":plan.fingerprint,
            "policy_version":POLICY_VERSION,"input_contract":row.content["schema_version"],"input_hash":digest(row.content),
            "input_content":row.content,"evidence_hash":digest(row.evidence),"source_evidence":row.evidence}}
    return {"plan":plan,"registration":registration,"run_status":"completed","observations":[deepcopy(observation)],
        "attempts":[{"command_key":command,"processing_run_id":observation["processing_run_id"],"outcome":"new",
                     "request_hash":digest({"plan_request":registration["request_hash"],"locator":row.locator})}],
        "aliases":[{"draw_id":observation["draw_id"],"namespace":"official_draw_number","value":row.contest,
                    "active":True,"assurance":"official"}],"contents":{observation["revision_id"]:deepcopy(row.content)},
        "continuity":{"ingestion_baseline":0,"sync_checkpoint":0,"sync_step":0}}


def test_coverage_accepts_consistent_snapshot_without_mutating_inputs(snapshot):
    before = deepcopy(snapshot)
    report = coverage_report(**snapshot)
    assert report["qualified"] and report["verified_records"] == 1
    assert snapshot == before


@pytest.mark.parametrize("fault,code", [
    ("ledger","command_ledger_mismatch"), ("recipe","recipe_mismatch"),
    ("alias","identity_mismatch"), ("evidence","input_or_evidence_mismatch"),
    ("payload","invalid_observation_payload"), ("unsealed","missing_or_unsealed_revision"),
    ("hash","support_hash_or_version_mismatch"), ("relational","relational_content_mismatch"),
    ("head","missing_head"), ("publication","unexpected_publication"),
    ("quarantine","observation_not_accepted"),
])
def test_coverage_rejects_inconsistent_snapshot(snapshot,fault,code):
    observation = snapshot["observations"][0]
    if fault == "ledger": snapshot["attempts"].clear()
    elif fault == "recipe": observation["catalog_fingerprint"] = digest("changed")
    elif fault == "alias": snapshot["aliases"][0]["active"] = False
    elif fault == "evidence": observation["diagnostic_payload"]["evidence_hash"] = digest("changed")
    elif fault == "payload": observation["diagnostic_payload"] = {}
    elif fault == "unsealed": observation["seal_state"] = "draft"
    elif fault == "hash": observation["semantic_hash"] = digest("changed")
    elif fault == "relational": snapshot["contents"]["unit-test-revision"]["draw_date"] = "1996-03-12"
    elif fault == "head": observation["latest_candidate_revision_id"] = None
    elif fault == "publication": observation["published_revision_id"] = observation["revision_id"]
    elif fault == "quarantine": observation["decision"] = "quarantined"
    report = coverage_report(**snapshot)
    assert not report["qualified"] and report["verified_records"] == 0
    assert code in report["problems"][0]["codes"]


@pytest.mark.parametrize("fault", ["missing","duplicate","unexpected","extra_command","manifest"])
def test_coverage_rejects_coverage_and_manifest_gaps(snapshot,fault):
    if fault == "missing": snapshot["observations"].clear()
    elif fault == "duplicate": snapshot["observations"].append(deepcopy(snapshot["observations"][0]))
    elif fault == "unexpected":
        extra = deepcopy(snapshot["observations"][0]); extra["row_locator"] = "data_record:9999"
        snapshot["observations"].append(extra)
    elif fault == "extra_command":
        extra = dict(snapshot["attempts"][0]); extra["command_key"] = "unit-test-extra"
        snapshot["attempts"].append(extra)
    else: snapshot["plan"].manifest["records_manifest_sha256"] = digest("changed")
    assert not coverage_report(**snapshot)["qualified"]


