"""Pedido/política puros; relatórios dublês não são aprovação de banco real."""
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import pytest

from app.application.activate_mega_sena_baseline import BaselineRequest, require_eligible_coverage
from app.application.persistence import PersistenceError
from app.domain import RawProvenance
from app.ingestion.mega_sena_api import SOURCE_KEY, ADAPTER_VERSION, normalize_response


REQUEST = BaselineRequest("activate-test","history-test","a"*64,"TEST_ONLY: explicit approval")


@pytest.mark.parametrize("field,value", [
    ("command","unsafe key"),("history_key",""),("expected_plan_hash","bad"),
    ("expected_plan_hash",None),("approval_reference",""),("approval_reference"," space "),
    ("approval_reference","x\ny"),("approval_reference","x"*513),
])
def test_request_rejects_invalid_intent(field,value):
    with pytest.raises(ValueError):
        replace(REQUEST,**{field:value})


def test_request_is_immutable_and_keeps_explicit_approval():
    with pytest.raises(AttributeError): REQUEST.command = "changed"
    assert REQUEST.approval_reference.startswith("TEST_ONLY:")


@pytest.mark.parametrize("status,qualified", [("running",True),("stopped",True),("failed",True),("completed",False)])
def test_terminal_success_and_current_quality_are_both_required(status,qualified):
    with pytest.raises(PersistenceError,match="baseline_not_eligible"):
        require_eligible_coverage({"run_status":status,"qualified":qualified})


def test_only_full_qualified_scope_is_accepted():
    report = {"run_status":"completed","qualified":True,"first_contest":1,"last_contest":2954,
              "expected_records":2954,"verified_records":2954}
    require_eligible_coverage(report)
    with pytest.raises(PersistenceError): require_eligible_coverage({**report,"verified_records":100})


@pytest.mark.parametrize("contest,sha", [
    (2955,"06529163206f05fcaecdc6dc589eee5026ab2183f4c072bd072d7079e43b0c6d"),
    (3071,"7a4d0c4e3decee29a652b5d9a417c97b10c88daebd975b00db056ca0bec701e8"),
])
def test_archived_json_fixtures_are_exact_and_normalize_without_local_workspace(contest,sha):
    body = (Path(__file__).parent/f"fixtures/mega_sena_api_{contest}.json").read_bytes()
    assert hashlib.sha256(body).hexdigest() == sha
    provenance = RawProvenance(SOURCE_KEY,sha,datetime(2026,10,21,tzinfo=timezone.utc),ADAPTER_VERSION)
    result = normalize_response(body,provenance,expected_contest=contest)
    assert result.is_valid, result.issues
    assert result.candidate.official_draw_number == str(contest)
