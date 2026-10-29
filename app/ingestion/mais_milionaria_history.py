"""Auditoria local da +Milionária em memória; stdout contém somente diagnóstico."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from app.domain import RawProvenance
from app.ingestion.mais_milionaria import SOURCE_KEY, file_sha256, iter_xlsx_rows, normalize_rows
from app.ingestion.mega_sena_history import build_history_report as _build_report, report_json


@dataclass(frozen=True, slots=True)
class HistoryBaseline:
    source_sha256: str = "69e9050a3528c7e8d8b944ca904044013e00a66648372183ce4dc5e4531a41fa"
    total_rows: int = 314
    first_contest: int = 1
    last_contest: int = 314
    first_date: str = "2022-05-28"
    last_date: str = "2025-12-24"
    missing_winner_locations: int = 312
    missing_observations: int = 314


def build_history_report(results, *, source_sha256_before, source_sha256_after, baseline=HistoryBaseline()):
    results = tuple(results)
    # A agregação da SPEC-0005 já usa componentes, faixas e finalidades nomeadas.
    # Reutilização limitada, sem impor a definição da Mega-Sena à +Milionária.
    report = _build_report(results, source_sha256_before=source_sha256_before,
                           source_sha256_after=source_sha256_after, baseline=baseline)
    report["normalizer_version"] = "spec-0007"
    report["lottery_slug"] = "mais_milionaria"
    clovers = []
    flags = Counter()
    for result in results:
        if result.candidate is None:
            flags["missing_candidate"] += 1
            continue
        for series in result.candidate.series:
            if series.key != "primary":
                continue
            for component in series.components:
                if component.key == "clovers":
                    clovers.extend(v for v in component.values if type(v) is int)
            value = next((a.value for a in series.attributes if a.key == "rolled_over"), None)
            flags["unknown" if value is None else ("yes" if value else "no")] += 1
    report["special_components"] = {"clovers": {"values_count": len(clovers),
        "min": min(clovers, default=None), "max": max(clovers, default=None)}}
    report["rollover_flag_counts"] = dict(sorted(flags.items()))
    return report


def audit_history(path: Path, *, observed_at: datetime, baseline=HistoryBaseline()):
    before = file_sha256(path)
    provenance = RawProvenance(SOURCE_KEY, before, observed_at, "spec-0007")
    results = normalize_rows(iter_xlsx_rows(path), provenance)
    return build_history_report(results, source_sha256_before=before,
                                source_sha256_after=file_sha256(path), baseline=baseline)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Diagnóstico local da +Milionária, sem escrita de candidatos")
    parser.add_argument("source", nargs="?", type=Path,
                        default=Path(__file__).resolve().parents[2] / "data/raw/mais_milionaria/mais_milionaria_resultados.xlsx")
    report = audit_history(parser.parse_args(argv).source, observed_at=datetime.now(timezone.utc))
    print(report_json(report), end="")
    return 0 if (report["source_unchanged"] and report["baseline_matches"]
                 and report["summary"]["valid_rows"] == report["summary"]["total_rows"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
