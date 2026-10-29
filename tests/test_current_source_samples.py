"""Contratos das amostras de 27/10/2026; offline, sem coletor novo de produção."""
import csv
from datetime import datetime
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
import zipfile

import pytest

from app.domain import RawProvenance
from app.ingestion.mega_sena_api import normalize_response, SOURCE_KEY, ADAPTER_VERSION, EXPECTED_FIELDS

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs/data/fontes-atuais-2026-10-27/amostras"
REPORT = ROOT / "docs/data/verificacao-fontes-atuais-2026-10-27.json"


def read_json(name):
    return json.loads((DATA / (name + ".json")).read_bytes(), parse_float=Decimal)


def previous(slug, day):
    vectors = json.loads((ROOT / "tests/fixtures/historical_relational_v1.json").read_text(encoding="utf-8"))
    source = next(s for s in vectors["sources"] if s["lottery"] == slug)
    return next(v["content"] for v in source["vectors"] if v["content"]["draw_date"] == day)


def values(content, key):
    primary = next(s for s in content["series"] if s["key"] == "primary")
    return [v["integer_value"] for c in primary["components"] if c["key"] == key for v in c["values"]]


@pytest.mark.parametrize("name", ["caixa_mega_latest", "caixa_mega_2954", "caixa_loto_latest", "caixa_loto_3571",
                                 "caixa_mili_latest", "caixa_mili_314", "texas_powerball", "texas_megamillions", "fdj_recent_zip"])
def test_wire_sample_matches_recorded_hash_and_length(name):
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    sample = next(s for s in report["samples"] if s["name"] == name)
    body = (ROOT / sample["path"]).read_bytes()
    assert len(body) == sample["byte_count"]
    assert hashlib.sha256(body).hexdigest() == sample["sha256"]


@pytest.mark.parametrize("name,number", [("caixa_mega_latest", 3075), ("caixa_mega_2954", 2954)])
def test_existing_mega_parser_accepts_actual_new_and_overlap_bytes(name, number):
    body = (DATA / (name + ".json")).read_bytes()
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    receipt = next(r for r in report["direct_probes"] if r["name"] == name)
    result = normalize_response(body, RawProvenance(SOURCE_KEY, hashlib.sha256(body).hexdigest(),
        datetime.fromisoformat(receipt["observed_at_utc"]), ADAPTER_VERSION), expected_contest=number)
    assert result.is_valid, result.issues
    assert result.candidate.official_draw_number == str(number)


@pytest.mark.parametrize("name,game,count,upper,tiers", [
    ("caixa_loto_latest", "LOTOFACIL", 15, 25, 5), ("caixa_loto_3571", "LOTOFACIL", 15, 25, 5),
    ("caixa_mili_latest", "MAIS_MILIONARIA", 6, 50, 10), ("caixa_mili_314", "MAIS_MILIONARIA", 6, 50, 10),
])
def test_other_caixa_contracts_are_explicit_not_mega_parser_parameters(name, game, count, upper, tiers):
    payload = read_json(name)
    assert payload["tipoJogo"] == game and payload["tipoPublicacao"] == 3
    assert set(payload) == EXPECTED_FIELDS | ({"trevosSorteados"} if game == "MAIS_MILIONARIA" else set())
    main = list(map(int, payload["listaDezenas"]))
    order = list(map(int, payload["dezenasSorteadasOrdemSorteio"]))
    assert len(main) == len(set(main)) == count and all(1 <= n <= upper for n in main)
    assert sorted(order[:count]) == main
    if game == "MAIS_MILIONARIA":
        clovers = list(map(int, payload["trevosSorteados"]))
        assert len(order) == 8 and len(clovers) == len(set(clovers)) == 2
        assert all(1 <= n <= 6 for n in clovers) and sorted(order[6:]) == sorted(clovers)
    assert [t["faixa"] for t in payload["listaRateioPremio"]] == list(range(1, tiers + 1))


@pytest.mark.parametrize("name,slug,day", [("caixa_loto_3571", "lotofacil", "2025-12-24"),
                                           ("caixa_mili_314", "mais_milionaria", "2025-12-24")])
def test_caixa_overlap_with_already_qualified_historical_numbers_and_tiers(name, slug, day):
    payload = read_json(name)
    content = previous(slug, day)
    assert values(content, "main") == list(map(int, payload["listaDezenas"]))
    observed = sorted((t["numeroDeGanhadores"], Decimal(t["valorPremio"])) for t in payload["listaRateioPremio"])
    historical = sorted((t["winners"], Decimal(t["prize"]["amount"])) for t in content["prize_tiers"])
    assert observed == historical


@pytest.mark.parametrize("name,slug,old_day,last_day,expected,special_key", [
    ("texas_powerball", "powerball", "2025-12-24", "2026-10-26", [18, 26, 49, 50, 54, 1], "powerball"),
    ("texas_megamillions", "mega_millions", "2025-12-23", "2026-10-23", [3, 7, 46, 49, 51, 5], "mega_ball"),
])
def test_texas_csv_sample_overlap_and_empty_multiplier_contract(name, slug, old_day, last_day, expected, special_key):
    rows = list(csv.reader(io.StringIO((DATA / (name + ".csv")).read_text(encoding="utf-8-sig"))))
    def day(row): return datetime(int(row[3]), int(row[1]), int(row[2])).date().isoformat()
    latest = max(rows, key=day)
    assert day(latest) == last_day
    assert sorted(map(int, latest[4:9])) + [int(latest[9])] == expected
    old = next(r for r in rows if day(r) == old_day)
    content = previous(slug, old_day)
    assert values(content, "main") == sorted(map(int, old[4:9]))
    assert values(content, special_key) == [int(old[9])]
    if slug == "mega_millions":
        first_new = next(r for r in rows if day(r) == "2025-04-08")
        assert len(latest) == 11 and latest[10] == first_new[10] == ""
    else:
        fixed = next(r for r in rows if day(r) == "2012-01-18")
        restored = next(r for r in rows if day(r) == "2014-01-22")
        assert len(fixed) == 11 and fixed[10] == "" and restored[10] == "3"


def test_fdj_zip_members_encoding_date_identity_and_overlap_are_explicit():
    with zipfile.ZipFile(DATA / "fdj_recent_zip.zip") as archive:
        members = archive.infolist()
        assert len(members) == 1 and members[0].filename == "euromillions_202002.csv"
        assert members[0].file_size < 4 * 1024 * 1024
        rows = list(csv.DictReader(io.StringIO(archive.read(members[0]).decode("cp1252")), delimiter=";"))
    day = lambda r: datetime.strptime(r["date_de_tirage"], "%d/%m/%Y").date()
    latest = max(rows, key=day)
    assert latest["date_de_tirage"] == "23/10/2026" and latest["annee_numero_de_tirage"] == "26085"
    assert sorted(int(latest["boule_" + str(n)]) for n in range(1, 6)) == [24, 33, 35, 44, 47]
    assert sorted(int(latest["etoile_" + str(n)]) for n in (1, 2)) == [7, 11]
    assert latest["rapport_du_rang1_Euro_Millions"] == "0"
    old = next(r for r in rows if r["date_de_tirage"] == "26/12/2025")
    content = previous("euro_millions", "2025-12-26")
    assert values(content, "main") == sorted(int(old["boule_" + str(n)]) for n in range(1, 6))
    assert values(content, "stars") == sorted(int(old["etoile_" + str(n)]) for n in (1, 2))
