"""Auditoria local da Powerball em memória; stdout contém somente diagnóstico."""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.domain import RawProvenance
from app.ingestion.mega_sena_history import build_history_report as _build_report, report_json
from app.ingestion.powerball import (
    NORMALIZER_VERSION,
    SOURCE_KEY,
    file_sha256,
    normalize_rows,
    read_html_rows,
)


@dataclass(frozen=True, slots=True)
class HistoryBaseline:
    source_sha256: str = "12b1197b080bdf06cd8c944a66167732bb73850e8591b163faf985a3744b4238"
    total_rows: int = 3742
    first_contest: None = None
    last_contest: None = None
    first_date: str = "1992-04-22"
    last_date: str = "2025-12-24"
    missing_winner_locations: int = 3742
    missing_observations: int = 3742


def build_history_report(results, *, source_sha256_before, source_sha256_after,
                         baseline=HistoryBaseline()):
    results = tuple(results)
    report = _build_report(
        results,
        source_sha256_before=source_sha256_before,
        source_sha256_after=source_sha256_after,
        baseline=baseline,
    )
    report["normalizer_version"] = NORMALIZER_VERSION
    report["lottery_slug"] = "powerball"
    versions = Counter()
    power_play_states = Counter()
    power_play_values = Counter()
    double_play_rows = 0
    double_play_main = []
    double_play_powerballs = []
    primary_powerballs = []
    for result in results:
        if result.candidate is None:
            continue
        candidate = result.candidate
        versions[candidate.rule_version_label] += 1
        power_play_states[dict(candidate.metadata).get("power_play_state", "unknown")] += 1
        for series in candidate.series:
            components = {component.key: component.values for component in series.components}
            if series.key == "primary":
                primary_powerballs.extend(components.get("powerball", ()))
                power_play = next((a.value for a in series.attributes if a.key == "power_play"), None)
                if power_play is not None:
                    power_play_values[str(power_play)] += 1
            elif series.key == "double_play":
                double_play_rows += 1
                double_play_main.extend(components.get("main", ()))
                double_play_powerballs.extend(components.get("powerball", ()))
    report["rule_version_counts"] = dict(sorted(versions.items()))
    report["power_play_state_counts"] = dict(sorted(power_play_states.items()))
    report["power_play_multiplier_counts"] = dict(sorted(power_play_values.items(), key=lambda item: int(item[0])))
    report["special_components"] = {
        "primary_powerball": {"values_count": len(primary_powerballs), "min": min(primary_powerballs, default=None), "max": max(primary_powerballs, default=None)},
        "double_play": {"rows": double_play_rows, "main_values_count": len(double_play_main), "main_min": min(double_play_main, default=None), "main_max": max(double_play_main, default=None), "powerball_min": min(double_play_powerballs, default=None), "powerball_max": max(double_play_powerballs, default=None)},
    }
    return report


def audit_history(path: Path, *, observed_at: datetime, baseline=HistoryBaseline()):
    before = file_sha256(path)
    provenance = RawProvenance(SOURCE_KEY, before, observed_at, NORMALIZER_VERSION)
    results = normalize_rows(read_html_rows(path), provenance)
    return build_history_report(
        results,
        source_sha256_before=before,
        source_sha256_after=file_sha256(path),
        baseline=baseline,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description="Diagnóstico local da Powerball, sem escrita de candidatos")
    parser.add_argument(
        "source", nargs="?", type=Path,
        default=Path(__file__).resolve().parents[2] / "data/raw/powerball/powerball_resultados.html",
    )
    report = audit_history(parser.parse_args(argv).source, observed_at=datetime.now(timezone.utc))
    print(report_json(report), end="")
    return 0 if (report["source_unchanged"] and report["baseline_matches"]
                 and report["summary"]["valid_rows"] == report["summary"]["total_rows"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
