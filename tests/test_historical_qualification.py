"""Qualificação em memória; mutações abaixo são testes negativos, não dados históricos."""
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path

import pytest

from app.application.historical_content import canonical_bytes, compare_shared, digest, source_evidence, to_content
from app.catalog import CATALOG
from app.domain import RawProvenance, ResultAttribute, ValueStatus
from app.ingestion import mega_sena, lotofacil, mais_milionaria, powerball, mega_millions, euro_millions
from app.ingestion.historical_qualification import qualify
from app.ingestion.mega_sena_api import ADAPTER_VERSION, SOURCE_KEY, normalize_response

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 21, tzinfo=timezone.utc)
MODULES = {m.__name__.rsplit(".", 1)[-1]: m for m in
           (mega_sena, lotofacil, mais_milionaria, powerball, mega_millions, euro_millions)}


def candidate(slug="mega_sena", index=0):
    module = MODULES[slug]
    body = (ROOT / f"tests/fixtures/{slug}_rows.json").read_bytes()
    row = json.loads(body, parse_float=Decimal)[index]
    if slug in {"powerball", "mega_millions"}:
        cls = powerball.RawPowerballRow if slug == "powerball" else mega_millions.RawMegaMillionsRow
        row = cls(**{k: tuple(v) if isinstance(v, list) else v for k, v in row.items()})
    elif slug == "euro_millions":
        row = euro_millions.RawEuroMillionsRow(row["date"], row["draw_id"], row["has_winner"], row["id"],
                                              row["numbers"], row["prize"], row["stars"])
    result = module.normalize_row(row, RawProvenance(module.SOURCE_KEY, hashlib.sha256(body).hexdigest(), NOW, "test-fixture"))
    assert result.is_valid, result.issues
    return result.candidate


@pytest.fixture(scope="module")
def qualified():
    return qualify(observed_at=NOW)


def test_complete_report_and_fixed_vectors(qualified):
    report, vectors = qualified
    assert report == json.loads((ROOT / "docs/data/qualificacao-importacao-spec-0026.json").read_text(encoding="utf-8"))
    assert vectors == json.loads((ROOT / "tests/fixtures/historical_relational_v1.json").read_text(encoding="utf-8"))
    assert report["qualified"]
    assert [r["representable_records"] for r in report["histories"]] == [2954, 3571, 314, 3742, 2984, 1906]
    assert sum(len(s["vectors"]) for s in vectors["sources"]) == 45
    for source in vectors["sources"]:
        for vector in source["vectors"]:
            assert vector["sha256"] == digest(vector["content"])
            assert vector["evidence_sha256"] == digest(vector["source_evidence"])
            assert canonical_bytes(vector["content"]) == canonical_bytes(json.loads(canonical_bytes(vector["content"])))
            assert all(v["extraction_ordinal"] is None for s in vector["content"]["series"]
                       for c in s["components"] for v in c["values"])


def test_every_rule_has_two_real_boundary_vectors(qualified):
    _, vectors = qualified
    for source in vectors["sources"]:
        coverage = {tag for v in source["vectors"] for tag in v["coverage"]}
        for rule in CATALOG.get(source["lottery"]).lottery.rules:
            assert f"rule_first:{rule.version_label}" in coverage
            assert f"rule_last:{rule.version_label}" in coverage
    assert sum(len(CATALOG.get(s["lottery"]).lottery.rules) for s in vectors["sources"]) == 20


def test_observation_clock_does_not_change_report_or_vectors(qualified):
    assert qualified == qualify(observed_at=datetime(2026, 10, 22, tzinfo=timezone.utc))


@pytest.mark.parametrize("slug", list(MODULES))
def test_transport_provenance_does_not_change_content(slug):
    c = candidate(slug)
    changed = replace(c, provenance=replace(c.provenance, raw_sha256="a" * 64, captured_at=NOW.replace(day=22),
                                           adapter_version="another-test-version"))
    assert digest(to_content(c)) == digest(to_content(changed))


def test_texts_and_private_ids_are_preserved_as_evidence_not_official_identity():
    c = candidate("euro_millions")
    changed = replace(c, external_references=tuple(replace(r, value="99999") for r in c.external_references),
                      metadata=tuple((k, "other observed text" if k == "date_source_text" else v) for k, v in c.metadata))
    assert to_content(c) == to_content(changed)
    assert source_evidence(c) != source_evidence(changed)
    assert to_content(c)["identity"] == {"namespace": "drawing_date", "value": "2004-02-13", "assurance": "provisional"}
    assert {r["namespace"] for r in source_evidence(c)["external_references"]} == {"source_id", "draw_id"}


def test_financial_scale_source_text_and_negative_zero():
    c = candidate()
    changed = replace(c, monetary_amounts=tuple(replace(m, amount=m.amount.quantize(Decimal("0.0000")),
                                                       source_text="alternative test format") for m in c.monetary_amounts))
    assert to_content(c) == to_content(changed)
    assert source_evidence(c) != source_evidence(changed)
    assert to_content(replace(c, monetary_amounts=tuple(replace(m, amount=Decimal("-0")) if m.amount == 0 else m
                                                      for m in c.monetary_amounts))) == to_content(c)


def test_absence_and_zero_are_different_and_em_flag_is_not_winner_count(qualified):
    _, vectors = qualified
    em = next(s for s in vectors["sources"] if s["lottery"] == "euro_millions")
    unknown = next(v["content"] for v in em["vectors"] if v["content"]["money"][0]["status"] == "unknown")
    assert unknown["money"][0]["amount"] is None
    assert unknown["money"][0]["currency"] is None
    assert unknown["money"][0]["scope"] == "provider_pt_or_es"
    assert not unknown["prize_tiers"]
    c = candidate()
    zero = to_content(c)["money"][0]
    absent = to_content(replace(c, monetary_amounts=tuple(replace(m, status=ValueStatus.UNKNOWN, amount=None, currency=None)
                                                        for m in c.monetary_amounts)))["money"][0]
    assert (zero["status"], zero["amount"], zero["currency"]) == ("known", "0", "BRL")
    assert absent != zero


def test_special_series_attributes_and_clovers_are_not_flattened():
    pb = to_content(candidate("powerball"))
    assert {s["key"] for s in pb["series"]} == {"primary", "double_play"}
    assert next(s for s in pb["series"] if s["key"] == "primary")["attributes"][0]["value_type"] == "integer"
    mm = to_content(candidate("mega_millions"))
    assert not mm["series"][0]["attributes"]
    assert mm["metadata"]["multiplier_state"] == "ticket_assigned_multiplier"
    c = candidate("mais_milionaria")
    content = to_content(c)
    clovers = next(x for x in content["series"][0]["components"] if x["key"] == "clovers")
    assert [v["integer_value"] for v in clovers["values"]] == list(c.series[0].components[1].values)
    assert all(v["extraction_ordinal"] is None for v in clovers["values"])
    assert len(content["prize_tiers"]) == 10
    assert content["series"][0]["attributes"][0]["value_type"] == "boolean"


def test_mega_sena_overlap_and_v1_are_explicitly_different_contracts(qualified):
    report, _ = qualified
    comparison = report["mega_sena_overlap"]
    assert not comparison["comparison"]["different"]
    assert len(comparison["comparison"]["equal"]) == 12
    assert len(comparison["comparison"]["only_right"]) == 5
    assert comparison["legacy_json_v1_sha256"] == "62755ae7c8057839aa4fcb97c2840afbc6e0a296844f7b02fb6d66f81bbe6477"
    assert len({comparison[k] for k in ("legacy_json_v1_sha256", "historical_json_sha256", "historical_xlsx_sha256")}) == 3
    body = (ROOT / comparison["json_input"]).read_bytes()
    result = normalize_response(body, RawProvenance(SOURCE_KEY, hashlib.sha256(body).hexdigest(), NOW, ADAPTER_VERSION), expected_contest=2954)
    api = to_content(result.candidate)
    next(m for m in api["money"] if m["kind"] == "sales_total")["amount"] = "999"  # mutação negativa
    assert compare_shared(to_content(candidate(index=2)), api)["different"]


@pytest.mark.parametrize("amount", [Decimal("1e19"), Decimal("0.1234567"), Decimal("Infinity"), 1.2])
def test_unrepresentable_money_is_rejected(amount):
    c = candidate()
    with pytest.raises(ValueError):
        to_content(replace(c, monetary_amounts=tuple(replace(m, amount=amount) for m in c.monetary_amounts)))


def test_wrong_currency_duplicate_measure_and_unknown_field_are_rejected():
    c = candidate()
    cases = [replace(c, monetary_amounts=(c.monetary_amounts[0],) + c.monetary_amounts),
             replace(c, monetary_amounts=tuple(replace(m, currency="USD") for m in c.monetary_amounts)),
             replace(c, metadata=c.metadata + (("unqualified_field", "test"),)),
             replace(c, external_references=()),
             replace(c, provenance=replace(c.provenance, source_key="unqualified_source")),
             replace(c, prize_tiers=c.prize_tiers[:-1]),
             replace(c, prize_tiers=tuple(replace(t, status=ValueStatus.UNKNOWN) for t in c.prize_tiers))]
    for changed in cases:
        with pytest.raises(ValueError):
            to_content(changed)


def test_identity_scope_rule_and_attribute_mismatches_are_rejected():
    c = candidate("euro_millions")
    cases = [replace(c, official_draw_number="12004"),
             replace(c, rule_version_label="em_2016_50x12"),
             replace(c, metadata=tuple((k, "PT" if k == "prize_source_jurisdiction" else v) for k, v in c.metadata)),
             replace(c, series=(replace(c.series[0], attributes=(ResultAttribute("has_jackpot_winner", 1),)),))]
    for changed in cases:
        with pytest.raises(ValueError):
            to_content(changed)


def test_bigint_overflow_is_rejected_before_sql():
    c = candidate()
    with pytest.raises(ValueError, match="bigint"):
        to_content(replace(c, prize_tiers=tuple(replace(t, winners=2**63) for t in c.prize_tiers)))
    c = candidate("powerball")
    primary = replace(c.series[0], attributes=(ResultAttribute("power_play", 2**63),))
    with pytest.raises(ValueError, match="bigint"):
        to_content(replace(c, series=(primary,) + c.series[1:]))


@pytest.mark.parametrize("mutation", ["duplicate", "invalid_row"])
def test_auditor_reports_negative_input_without_changing_raw(monkeypatch, mutation):
    import app.ingestion.historical_qualification as audit
    module, history, extension, reader, adapter = audit.HISTORIES[0]

    def changed_reader(path):
        for ordinal, row in enumerate(reader(path), 1):
            if ordinal == 1 and mutation == "invalid_row":
                yield {**row, "Bola6": 99}  # fora de 1..60, somente em memória
            else:
                yield row
            if ordinal == 1 and mutation == "duplicate":
                yield row

    monkeypatch.setattr(audit, "HISTORIES", ((module, history, extension, changed_reader, adapter),))
    report, _ = audit.qualify(observed_at=NOW)
    assert not report["qualified"]
    assert report["histories"][0]["source_unchanged"]
    if mutation == "duplicate":
        assert report["histories"][0]["duplicate_identities"][0]["rows"] == [1, 2]
        assert report["histories"][0]["duplicate_external_references"]
    else:
        assert "component.out_of_range" in report["histories"][0]["errors"][0]["issues"]


def test_cli_json_transport_preserves_unicode_and_reports_failure(monkeypatch, capsys):
    import app.ingestion.historical_qualification as audit
    monkeypatch.setattr(audit, "qualify", lambda: ({"qualified": False}, {"text": "prêmio"}))
    assert audit.main(["--vectors"]) == 1
    output = capsys.readouterr().out
    assert "\\u00ea" in output
    assert json.loads(output) == {"text": "prêmio"}
