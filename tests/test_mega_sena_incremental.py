from copy import deepcopy
import json
from pathlib import Path

import pytest

from app.application.mega_sena_incremental import decide_incremental
from app.application.persistence import PersistenceError

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def contents():
    historical = json.loads((ROOT/"tests/fixtures/historical_relational_v1.json").read_text(encoding="utf-8"))
    xlsx = next(s for s in historical["sources"] if s["lottery"] == "mega_sena")["vectors"][-1]["content"]
    current = json.loads((ROOT/"tests/fixtures/mega_sena_relational_v1.json").read_text(encoding="utf-8"))["content"]
    return xlsx,current


def test_incremental_distinguishes_history_enrichment_from_json_correction(contents):
    xlsx,current = contents
    assert decide_incremental(None,current)[0] == "new"
    assert decide_incremental(xlsx,current)[0] == "enrichment"
    assert decide_incremental(current,current)[0] == "unchanged"
    changed = deepcopy(current)
    changed["money"][0]["amount"] = "999"
    assert decide_incremental(current,changed)[0] == "correction"
    # Modificação só em fato exclusivo seria enriquecimento se compartilhado igual.
    next(m for m in changed["money"] if m["kind"] == "sales_total")["amount"] = "1"
    assert decide_incremental(xlsx,changed)[0] == "quarantined"


def test_unknown_contract_and_wrong_input_are_not_recanonicalized(contents):
    xlsx,current = contents
    with pytest.raises(PersistenceError,match="canonicalization_conflict"):
        decide_incremental(current,xlsx)
    unknown = {**xlsx,"schema_version":"unqualified"}
    with pytest.raises(PersistenceError,match="canonicalization_conflict"):
        decide_incremental(unknown,current)


def test_cross_contract_partial_support_is_quarantined_not_forged(contents):
    _,current = contents
    from app.application.mega_sena_bridge import project
    # Contrato histórico contendo os mesmos fatos: cenário negativo de compatibilidade,
    # não um novo resultado histórico nem saída do importador XLSX atual.
    equal_projection = project(current)
    assert decide_incremental(equal_projection,current)[0] == "quarantined"
