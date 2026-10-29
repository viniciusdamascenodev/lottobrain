"""Auditoria local da Lotofácil em memória; stdout contém somente diagnóstico."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.domain import RawProvenance
from app.ingestion.lotofacil import SOURCE_KEY, file_sha256, iter_xlsx_rows, normalize_rows
from app.ingestion.mega_sena_history import build_history_report as _build_report, report_json


@dataclass(frozen=True, slots=True)
class HistoryBaseline:
    source_sha256: str = "0ab2c742f0ae6e3b567af2f99744b6d4071c08427c08941a94087e6bde36918e"
    total_rows: int = 3571
    first_contest: int = 1
    last_contest: int = 3571
    first_date: str = "2003-09-29"
    last_date: str = "2025-12-24"
    missing_winner_locations: int = 426
    missing_observations: int = 2791


def build_history_report(results, *, source_sha256_before, source_sha256_after, baseline=HistoryBaseline()):
    # A agregação da SPEC-0005 já usa componentes, faixas e finalidades nomeadas.
    # Reutilização limitada, sem impor a definição da Mega-Sena à Lotofácil.
    report = _build_report(results, source_sha256_before=source_sha256_before,
                           source_sha256_after=source_sha256_after, baseline=baseline)
    report["normalizer_version"] = "spec-0006"
    report["lottery_slug"] = "lotofacil"
    return report


def audit_history(path: Path, *, observed_at: datetime, baseline=HistoryBaseline()):
    before = file_sha256(path)
    provenance = RawProvenance(SOURCE_KEY, before, observed_at, "spec-0006")
    results = normalize_rows(iter_xlsx_rows(path), provenance)
    return build_history_report(results, source_sha256_before=before,
                                source_sha256_after=file_sha256(path), baseline=baseline)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Diagnóstico local da Lotofácil, sem escrita de candidatos")
    parser.add_argument("source", nargs="?", type=Path,
                        default=Path(__file__).resolve().parents[2] / "data/raw/lotofacil/lotofacil_resultados.xlsx")
    report = audit_history(parser.parse_args(argv).source, observed_at=datetime.now(timezone.utc))
    print(report_json(report), end="")
    return 0 if (report["source_unchanged"] and report["baseline_matches"]
                 and report["summary"]["valid_rows"] == report["summary"]["total_rows"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
