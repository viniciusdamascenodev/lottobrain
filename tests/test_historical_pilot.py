from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from app.application.historical_content import digest, to_content
from app.application.historical_pilot import prepare_xlsx, prepare_json, restore_plan
from app.application.mega_sena_bridge import decide, project
from app.application.persistence import PersistenceError
from app.domain import RawProvenance
from app.ingestion.mega_sena_api import SOURCE_KEY, ADAPTER_VERSION, normalize_response

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026,10,21,tzinfo=timezone.utc)
BODY = (ROOT / "tests/fixtures/mega_sena_api_2954.json").read_bytes()


@pytest.fixture(scope="module")
def plans():
    return (prepare_xlsx(ROOT / "data/raw/mega_sena/mega_sena_resultados.xlsx",inspected_at=NOW),
            prepare_json(BODY,origin="test-fixture:mega_sena_api_2954.json",inspected_at=NOW))


def test_plan_limits_real_content_and_stable_manifest(plans):
    xlsx, _ = plans
    assert [r.contest for r in xlsx.rows] == ["1","2","2954"]
    assert [r.locator for r in xlsx.rows] == ["data_record:1","data_record:2","data_record:2954"]
    again = prepare_xlsx(ROOT / "data/raw/mega_sena/mega_sena_resultados.xlsx",(2954,2,1),inspected_at=NOW.replace(day=22))
    assert xlsx.fingerprint == again.fingerprint
    assert xlsx.sha256 == "0e1936e3ac94a35a89c13ef31d705d3fb363239779ad6224b5e41171a3238686"
    assert restore_plan(xlsx.body,xlsx.manifest).fingerprint == xlsx.fingerprint
    edited = deepcopy(xlsx.manifest)
    edited["rows"][0]["content_hash"] = "0" * 64
    with pytest.raises(PersistenceError,match="pilot_manifest_mismatch"):
        restore_plan(xlsx.body,edited)


@pytest.mark.parametrize("selection", [(),(3,),(1,1),(True,),(1,2,3,2954)])
def test_rejects_out_of_pilot_selections(selection):
    with pytest.raises(ValueError):
        prepare_xlsx(Path("must-not-read"),selection)


def test_rejects_unqualified_artifact_and_json(monkeypatch):
    monkeypatch.setattr(Path,"read_bytes",lambda p:b"negative-test-not-an-xlsx")
    with pytest.raises(PersistenceError,match="pilot_input_not_qualified"):
        prepare_xlsx(Path("negative-test"))
    with pytest.raises(PersistenceError,match="pilot_row_not_qualified"):
        prepare_json(b"{}",origin="negative-test")


def test_bridge_projection_matches_real_normalizer(plans):
    _, json_plan = plans
    c = normalize_response(BODY,RawProvenance(SOURCE_KEY,json_plan.sha256,NOW,ADAPTER_VERSION),expected_contest=2954).candidate
    assert project(json_plan.rows[0].content) == to_content(c)
    assert digest(json_plan.rows[0].content) == "62755ae7c8057839aa4fcb97c2840afbc6e0a296844f7b02fb6d66f81bbe6477"


def test_bridge_two_orders_are_support_or_enrichment_not_merge(plans):
    xlsx, json_plan = plans
    old, richer = xlsx.rows[-1].content, json_plan.rows[0].content
    original = deepcopy(richer)
    assert decide(richer,old)[0] == "support"
    assert decide(old,richer)[0] == "enrichment"
    assert decide(old,old)[0] == "support"
    assert decide(None,old)[0] == "new"
    assert richer == original


def test_conflicts_unknown_and_mixed_changes_fail_closed(plans):
    xlsx, json_plan = plans
    old, richer = xlsx.rows[-1].content, json_plan.rows[0].content
    altered = deepcopy(old)
    altered["money"][0]["amount"] = "1"
    assert decide(richer,altered)[0] == "quarantined"
    altered["money"][0].update(status="unknown",amount=None,currency=None)
    assert decide(richer,altered)[0] == "quarantined"
    altered = deepcopy(old)
    altered["metadata"]["new_field"] = "negative-test"
    assert decide(richer,altered)[0] == "quarantined"
    altered["schema_version"] = "unqualified-version"
    with pytest.raises(PersistenceError,match="canonicalization_conflict"):
        decide(richer,altered)
