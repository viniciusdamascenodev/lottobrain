"""Evidências reais da descoberta: offline, sem escrita SQL nem nova coleta."""
import csv
from datetime import date, datetime, timedelta
import hashlib
import io
import json
from pathlib import Path
import zipfile

import pytest

from app.domain import RawProvenance
from app.ingestion import lotofacil, mais_milionaria, mega_sena
from app.ingestion.mega_sena_api import ADAPTER_VERSION, SOURCE_KEY, normalize_response

ROOT = Path(__file__).resolve().parents[1]
REPORT = json.loads((ROOT / "docs/data/fechamento-etapa-2.json").read_text(encoding="utf-8"))


def sample(name):
    item = next(s for s in REPORT["samples"] if s["name"] == name)
    return ROOT / item["path"], item


def expected_dates(start, end, weekdays):
    dates = set()
    day = start + timedelta(days=1)
    while day <= end:
        if day.weekday() in weekdays:
            dates.add(day.isoformat())
        day += timedelta(days=1)
    return dates


@pytest.mark.parametrize("name", [s["name"] for s in REPORT["samples"]])
def test_preserved_new_source_bytes(name):
    path, evidence = sample(name)
    body = path.read_bytes()
    assert len(body) == evidence["byte_count"]
    assert hashlib.sha256(body).hexdigest() == evidence["sha256"]


@pytest.mark.parametrize("name,module,baseline,total", [
    ("mega_export_current", mega_sena, 2954, 3075),
    ("loto_export_current", lotofacil, 3571, 3814),
    ("mili_export_current", mais_milionaria, 314, 401),
])
def test_official_exports_have_complete_ids_and_recent_rows_pass_existing_normalizers(name, module, baseline, total):
    path, evidence = sample(name)
    rows = list(module.iter_xlsx_rows(path))
    assert len(rows) == total
    assert sorted(int(r["Concurso"]) for r in rows) == list(range(1, total + 1))
    provenance = RawProvenance(module.SOURCE_KEY, evidence["sha256"],
        datetime.fromisoformat(evidence["observed_at_utc"]), "stage2-inspection")
    recent = [module.normalize_row(r, provenance) for r in rows if int(r["Concurso"]) > baseline]
    assert len(recent) == total - baseline
    assert all(r.is_valid for r in recent), [(r.canonical_key, r.issues) for r in recent if not r.is_valid]


def test_same_date_is_not_duplicate_identity_for_official_lotofacil_contests():
    path, evidence = sample("loto_export_current")
    rows = [r for r in lotofacil.iter_xlsx_rows(path) if r["Concurso"] in (3715, 3716)]
    provenance = RawProvenance(lotofacil.SOURCE_KEY, evidence["sha256"],
        datetime.fromisoformat(evidence["observed_at_utc"]), "stage2-inspection")
    normalized = [lotofacil.normalize_row(r, provenance) for r in rows]
    assert len(normalized) == 2 and all(r.is_valid for r in normalized)
    assert {r.candidate.draw_date for r in normalized} == {date(2026, 6, 20)}
    assert len({r.canonical_key for r in normalized}) == 2
    assert normalized[0].candidate.series != normalized[1].candidate.series
    for number in (3715, 3716):
        api = json.loads(sample(f"loto_{number}")[0].read_bytes())
        row = next(r for r in rows if r["Concurso"] == number)
        assert api["numero"] == number and api["dataApuracao"] == row["Data Sorteio"]
        assert sorted(map(int, api["listaDezenas"])) == sorted(row[f"Bola{i}"] for i in range(1, 16))


@pytest.mark.parametrize("name,old_name", [
    ("mega_current_json", "caixa_mega_latest"),
    ("loto_current_json", "caixa_loto_latest"),
    ("mili_current_json", "caixa_mili_latest"),
])
def test_new_host_adds_one_explicit_field_without_changing_previously_observed_facts(name, old_name):
    previous = json.loads((ROOT / f"docs/data/fontes-atuais-2026-10-27/amostras/{old_name}.json").read_bytes())
    current = json.loads(sample(name)[0].read_bytes())
    assert set(current) - set(previous) == {"tituloConcursoEspecial"}
    assert current["tituloConcursoEspecial"] is None
    assert {k: current[k] for k in previous} == previous


def test_current_mega_host_does_not_silently_bypass_existing_schema_guard():
    path, evidence = sample("mega_current_json")
    result = normalize_response(path.read_bytes(), RawProvenance(SOURCE_KEY, evidence["sha256"],
        datetime.fromisoformat(evidence["observed_at_utc"]), ADAPTER_VERSION), expected_contest=3075)
    assert not result.is_valid
    assert {i.code for i in result.issues} == {"source.schema_changed"}
    assert result.candidate is not None  # Diagnóstico não concede aprovação.


@pytest.mark.parametrize("slug,file,baseline,last,weekdays,upper,special_upper", [
    ("powerball", "texas_powerball.csv", "2025-12-24", "2026-10-26", {0, 2, 5}, 69, 26),
    ("mega_millions", "texas_megamillions.csv", "2025-12-23", "2026-10-23", {1, 4}, 70, 24),
])
def test_recent_texas_dates_and_components_match_declared_coverage(slug, file, baseline, last, weekdays, upper, special_upper):
    rows = csv.reader(io.StringIO((ROOT / f"docs/data/fontes-atuais-2026-10-27/amostras/{file}").read_text(encoding="utf-8-sig")))
    recent = [(date(int(r[3]), int(r[1]), int(r[2])), r) for r in rows]
    recent = [(d, r) for d, r in recent if d > date.fromisoformat(baseline)]
    assert {d.isoformat() for d, r in recent} == expected_dates(date.fromisoformat(baseline), date.fromisoformat(last), weekdays)
    assert len(recent) == len({d for d, r in recent})
    observed = next(r for r in REPORT["coverage"]["lotteries"] if r["lottery"] == slug)
    assert len(recent) == observed["recent_records"]
    for day, row in recent:
        main = list(map(int, row[4:9]))
        assert len(row) == 11 and len(set(main)) == 5 and all(1 <= n <= upper for n in main)
        assert 1 <= int(row[9]) <= special_upper


def test_fdj_recent_dates_include_today_and_common_result_matches_independent_operator_observation():
    with zipfile.ZipFile(sample("fdj_current_zip")[0]) as archive:
        assert archive.namelist() == ["euromillions_202002.csv"]
        info = archive.infolist()[0]
        assert info.file_size <= 4 * 1024 * 1024
        rows = list(csv.DictReader(io.StringIO(archive.read(info).decode("cp1252")), delimiter=";"))
    recent = [(datetime.strptime(r["date_de_tirage"], "%d/%m/%Y").date(), r) for r in rows]
    recent = [(d, r) for d, r in recent if d > date(2025, 12, 26)]
    assert len(recent) == 87
    assert {d.isoformat() for d, r in recent} == expected_dates(date(2025, 12, 26), date(2026, 10, 27), {1, 4})
    for day, row in recent:
        main = [int(row[f"boule_{i}"]) for i in range(1, 6)]
        stars = [int(row[f"etoile_{i}"]) for i in range(1, 3)]
        assert len(set(main)) == 5 and all(1 <= n <= 50 for n in main)
        assert len(set(stars)) == 2 and all(1 <= n <= 12 for n in stars)
    latest = next(r for d, r in recent if d == date(2026, 10, 27))
    observation = REPORT["decisions"]["euromillions_2026_10_27_cross_check"]
    assert sorted(int(latest[f"boule_{i}"]) for i in range(1, 6)) == observation["main"]
    assert sorted(int(latest[f"etoile_{i}"]) for i in range(1, 3)) == observation["stars"]
