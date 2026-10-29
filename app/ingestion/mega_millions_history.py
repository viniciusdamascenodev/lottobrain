"""Auditoria local da Mega Millions em memória; stdout contém somente diagnóstico."""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.domain import RawProvenance
from app.ingestion.mega_millions import (
    NORMALIZER_VERSION, SOURCE_KEY, file_sha256, normalize_rows, read_html_rows,
)
from app.ingestion.mega_sena_history import build_history_report as _build_report, report_json


@dataclass(frozen=True, slots=True)
class HistoryBaseline:
    source_sha256: str = "c154cb21ae6381efe53f9735b5704d148156ba9737266de54e8badbf1d92c35c"
    total_rows: int = 2984
    first_contest: None = None
    last_contest: None = None
    first_date: str = "1996-09-06"
    last_date: str = "2025-12-23"
    missing_winner_locations: int = 2984
    missing_observations: int = 2984


def build_history_report(results, *, source_sha256_before, source_sha256_after,
                         baseline=HistoryBaseline()):
    results = tuple(results)
    report = _build_report(
        results, source_sha256_before=source_sha256_before,
        source_sha256_after=source_sha256_after, baseline=baseline,
    )
    report["normalizer_version"] = NORMALIZER_VERSION
    report["lottery_slug"] = "mega_millions"
    versions = Counter()
    states = Counter()
    multipliers = Counter()
    mega_balls = []
    for result in results:
        if result.candidate is None:
            continue
        candidate = result.candidate
        versions[candidate.rule_version_label] += 1
        states[dict(candidate.metadata).get("multiplier_state", "unknown")] += 1
        primary = next((series for series in candidate.series if series.key == "primary"), None)
        if primary is None:
            continue
        for component in primary.components:
            if component.key == "mega_ball":
                mega_balls.extend(component.values)
        value = next((attribute.value for attribute in primary.attributes if attribute.key == "megaplier"), None)
        if value is not None:
            multipliers[str(value)] += 1
    report["rule_version_counts"] = dict(sorted(versions.items()))
    report["multiplier_state_counts"] = dict(sorted(states.items()))
    report["megaplier_counts"] = dict(sorted(multipliers.items(), key=lambda item: int(item[0])))
    report["special_components"] = {
        "mega_ball": {"values_count": len(mega_balls), "min": min(mega_balls, default=None), "max": max(mega_balls, default=None)},
    }
    return report


def audit_history(path: Path, *, observed_at: datetime, baseline=HistoryBaseline()):
    before = file_sha256(path)
    provenance = RawProvenance(SOURCE_KEY, before, observed_at, NORMALIZER_VERSION)
    results = normalize_rows(read_html_rows(path), provenance)
    return build_history_report(
        results, source_sha256_before=before,
        source_sha256_after=file_sha256(path), baseline=baseline,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description="Diagnóstico local da Mega Millions, sem escrita de candidatos")
    parser.add_argument(
        "source", nargs="?", type=Path,
        default=Path(__file__).resolve().parents[2] / "data/raw/mega_millions/mega_millions_resultados.html",
    )
    report = audit_history(parser.parse_args(argv).source, observed_at=datetime.now(timezone.utc))
    print(report_json(report), end="")
    return 0 if (report["source_unchanged"] and report["baseline_matches"]
                 and report["summary"]["valid_rows"] == report["summary"]["total_rows"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
