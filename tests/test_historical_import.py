from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from app.application.historical_import import HistoricalImportPlan, ImportMegaSenaHistory, prepare_history, restore_history
from app.application.persistence import PersistenceError

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def plan():
    body = (ROOT/"data/raw/mega_sena/mega_sena_resultados.xlsx").read_bytes()
    return prepare_history(body,inspected_at=datetime(2026,10,21,tzinfo=timezone.utc))


def test_complete_plan_pins_real_interval_and_compact_manifest(plan):
    assert len(plan.rows) == 2954
    assert [plan.rows[0].contest,plan.rows[-1].contest] == ["1","2954"]
    assert plan.manifest["first_date"] == "1996-03-11"
    assert plan.manifest["last_date"] == "2025-12-20"
    assert len(json.dumps(plan.manifest)) < 2048
    assert plan.fingerprint == restore_history(plan.body,plan.manifest).fingerprint
    # Propriedade em cache, sem reserializar 2.954 registros em cada consulta.
    original = plan.fingerprint
    assert all(plan.fingerprint == original for _ in range(6000))
    edited = plan.manifest; edited["record_count"] = 0
    assert plan.manifest["record_count"] == 2954


@pytest.mark.parametrize("change", ["missing","duplicate","reordered"])
def test_incomplete_or_ambiguous_selection_is_rejected(plan,change):
    rows = plan.rows[:-1] if change == "missing" else (plan.rows[0],)+plan.rows[:-1] if change == "duplicate" else tuple(reversed(plan.rows))
    with pytest.raises(PersistenceError):
        HistoricalImportPlan(plan.body,rows)


def test_corrupt_raw_or_manifest_is_rejected(plan):
    with pytest.raises(PersistenceError,match="historical_input_not_qualified"):
        prepare_history(b"negative-test-not-qualified-xlsx")
    changed = plan.manifest; changed["records_manifest_sha256"] = "0"*64
    with pytest.raises(PersistenceError,match="historical_manifest_mismatch"):
        restore_history(plan.body,changed)


@pytest.mark.parametrize("block", [0,101,True])
def test_verification_block_is_bounded(block):
    with pytest.raises(ValueError):
        ImportMegaSenaHistory(None,None,verification_block=block)
