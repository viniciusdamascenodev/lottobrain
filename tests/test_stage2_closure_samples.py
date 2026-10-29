"""Amostras oficiais SELAE e decisões de contrato; sem rede ou ingestão operacional."""
import csv
from datetime import datetime
from decimal import Decimal
from email.utils import parsedate_to_datetime
import hashlib
import html
import io
import json
from pathlib import Path
import re
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPORT = json.loads((ROOT / "docs/data/encerramento-etapa-2.json").read_bytes())


def sample(name):
    return ROOT / next(s["path"] for s in REPORT["samples"] if s["name"] == name)


def fdj_rows():
    with zipfile.ZipFile(ROOT / "docs/data/fechamento-etapa-2-2026-10-27/amostras/fdj_recente.zip") as z:
        rows = list(csv.DictReader(io.StringIO(z.read(z.namelist()[0]).decode("cp1252")), delimiter=";"))
    return {datetime.strptime(r["date_de_tirage"], "%d/%m/%Y").date().isoformat(): r for r in rows}


@pytest.mark.parametrize("item", REPORT["samples"], ids=lambda r: r["name"])
def test_official_evidence_bytes(item):
    body = (ROOT / item["path"]).read_bytes()
    assert len(body) == item["byte_count"]
    assert hashlib.sha256(body).hexdigest() == item["sha256"]


@pytest.mark.parametrize("summary", REPORT["selae_analysis"]["draw_samples"], ids=lambda r: r["date"])
def test_returned_identity_dates_and_historical_components_match_preserved_reference(summary):
    records = json.loads(sample(summary["sample"]).read_bytes())
    assert isinstance(records, list) and len(records) == 1
    row = records[0]
    assert row["game_id"] == "EMIL" and isinstance(row["id_sorteo"], str)
    assert row["id_sorteo"] == summary["source_id"]
    day = datetime.strptime(row["fecha_sorteo"], "%Y-%m-%d %H:%M:%S").date().isoformat()
    assert day == summary["date"]
    numbers = list(map(int, re.findall(r"\d+", row["combinacion"])))
    assert len(numbers) == 7
    assert len(set(numbers[:5])) == 5 and len(set(numbers[5:])) == 2
    assert all(1 <= n <= 50 for n in numbers[:5])
    assert all(1 <= n <= summary["star_limit"] for n in numbers[5:])
    assert numbers[:5] == summary["main"] and numbers[5:] == summary["stars"]
    if day < "2026":
        legacy = json.loads((ROOT / "data/raw/euro_millions/euro_millions_resultados.json").read_bytes())
        ref = next(r for r in legacy if parsedate_to_datetime(r["date"]).date().isoformat() == day)
        assert sorted(numbers[:5]) == sorted(map(int, ref["numbers"]))
        assert sorted(numbers[5:]) == sorted(map(int, ref["stars"]))
    else:
        ref = fdj_rows()[day]
        assert sorted(numbers[:5]) == sorted(int(ref[f"boule_{i}"]) for i in range(1, 6))
        assert sorted(numbers[5:]) == sorted(int(ref[f"etoile_{i}"]) for i in range(1, 3))


def test_historical_financial_nulls_and_category_order_cannot_use_a_single_recent_mapping():
    first = json.loads(sample("selae_20040213").read_bytes())[0]
    changed = json.loads(sample("selae_20110510").read_bytes())[0]
    assert len(first["escrutinio"]) == 12 and len(changed["escrutinio"]) == 13
    assert all(t["ganadores_eu"] is None for t in first["escrutinio"])
    assert first["recaudacion_europea"] == "-" and first["millon"] is None
    assert first["premio_bote"] == "0"
    assert Decimal(first["escrutinio"][0]["premio"]) == Decimal("15000000")
    pairs = [tuple(map(int, re.findall(r"\d+", t["tipo"])[1:])) for t in changed["escrutinio"]]
    assert len(set(pairs)) == 13
    assert pairs[5] == (4, 0) and pairs[6] == (3, 2)
    current = json.loads(sample("selae_20261027").read_bytes())[0]
    current_pairs = [tuple(map(int, re.findall(r"\d+", t["tipo"])[1:])) for t in current["escrutinio"]]
    assert current_pairs[5] == (3, 2) and current_pairs[6] == (4, 0)


def test_recent_europe_winners_match_but_country_payouts_are_not_overwritten():
    fdj = fdj_rows(); count = 0
    for name in ("selae_20261023", "selae_20261027"):
        row = json.loads(sample(name).read_bytes())[0]
        ref = fdj[row["fecha_sorteo"][:10]]
        assert len(row["escrutinio"]) == 13
        for tier in row["escrutinio"]:
            rank, main, stars = map(int, re.findall(r"\d+", tier["tipo"]))
            assert int(tier["ganadores_eu"]) == int(ref[f"nombre_de_gagnant_au_rang{rank}_Euro_Millions_en_europe"])
            assert 0 <= int(tier["ganadores"]) <= int(tier["ganadores_eu"])
            assert Decimal(tier["premio"].replace(",", ".")) >= 0
            count += 1
    assert count == 26
    latest = json.loads(sample("selae_20261027").read_bytes())[0]
    third = latest["escrutinio"][2]
    assert third["ganadores"] == "0" and third["ganadores_eu"] == "1"
    assert Decimal(third["premio"].replace(",", ".")) == Decimal("630456.7")
    assert Decimal(fdj["2026-10-27"]["rapport_du_rang3_Euro_Millions"].replace(",", ".")) == Decimal("630456.6")
    assert latest["millon"]["combinacion"] == "GXP83881"


def test_http_200_no_record_message_is_not_a_draw_or_latest_result_fallback():
    payload = json.loads(sample("selae_no_draw").read_bytes())
    assert isinstance(payload, str) and payload.startswith("No se ha encontrado")
    receipt = next(p for p in REPORT["probes"] if p["name"] == "selae_no_draw")
    assert receipt["http_status"] == 200
    assert "20261026" in receipt["url"]


def test_official_sharing_chain_is_preserved_and_its_scope_is_not_invented():
    sharing = html.unescape(re.sub(r"<[^>]+>", " ", sample("selae_sharing").read_text(encoding="utf-8")))
    sharing = " ".join(sharing.split())
    assert "If you want to post information on the latest results of our games on your website" in sharing
    wrapper = sample("selae_embed_latest").read_text(encoding="utf-8")
    assert '/servicios/fechav3?game_id=' in wrapper and '&fecha_sorteo=' in wrapper
    policy = html.unescape(re.sub(r"<[^>]+>", " ", sample("selae_use_policy").read_text(encoding="utf-8")))
    assert "exclusivamente personal" in " ".join(policy.split())
    assert REPORT["all_sources_unrestricted_licensed"] is False
    for probe in REPORT["probes"]:
        assert probe["tls_verified"] and probe["check_hostname"]
        assert probe["verify_mode"] == 2 and probe["automatic_retries"] == 0
