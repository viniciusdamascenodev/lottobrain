"""Auditoria local do EuroMillions em memória; stdout contém somente diagnóstico."""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.domain import RawProvenance, ValueStatus
from app.ingestion.euro_millions import (
    NORMALIZER_VERSION, SOURCE_KEY, file_sha256, normalize_rows, read_json_rows,
)
from app.ingestion.mega_sena_history import build_history_report as _build_report, report_json


@dataclass(frozen=True, slots=True)
class HistoryBaseline:
    source_sha256: str = "e4e7f97102c868569e33d54e34e258671cfca98f6872cf21fc0f86b171e57914"
    total_rows: int = 1906
    first_contest: None = None
    last_contest: None = None
    first_date: str = "2004-02-13"
    last_date: str = "2025-12-26"
    missing_winner_locations: int = 1906
    missing_observations: int = 1906


def build_history_report(results, *, source_sha256_before, source_sha256_after,
                         baseline=HistoryBaseline()):
    results = tuple(results)
    report = _build_report(
        results, source_sha256_before=source_sha256_before,
        source_sha256_after=source_sha256_after, baseline=baseline,
    )
    report["normalizer_version"] = NORMALIZER_VERSION
    report["lottery_slug"] = "euro_millions"
    versions = Counter()
    winner_flags = Counter()
    stars = []
    source_ids = []
    draw_ids = []
    zero_prize_rows = 0
    for result in results:
        if result.candidate is None:
            continue
        candidate = result.candidate
        versions[candidate.rule_version_label] += 1
        for reference in candidate.external_references:
            if reference.namespace == "source_id":
                source_ids.append(int(reference.value))
            elif reference.namespace == "draw_id":
                draw_ids.append(int(reference.value))
        for amount in candidate.monetary_amounts:
            if amount.kind == "top_tier_prize_per_winner" and amount.status is ValueStatus.UNKNOWN and amount.source_text in ("0", "0.0"):
                zero_prize_rows += 1
        primary = next((series for series in candidate.series if series.key == "primary"), None)
        if primary is None:
            continue
        for component in primary.components:
            if component.key == "stars":
                stars.extend(component.values)
        value = next((attribute.value for attribute in primary.attributes if attribute.key == "has_jackpot_winner"), None)
        if type(value) is bool:
            winner_flags[str(value).lower()] += 1
    source_id_set = set(source_ids)
    report["rule_version_counts"] = dict(sorted(versions.items()))
    report["jackpot_winner_flag_counts"] = dict(sorted(winner_flags.items()))
    report["special_components"] = {
        "stars": {"values_count": len(stars), "min": min(stars, default=None), "max": max(stars, default=None)},
    }
    report["external_reference_diagnostics"] = {
        "source_id": {
            "count": len(source_ids), "min": min(source_ids, default=None), "max": max(source_ids, default=None),
            "gaps_between_min_and_max": (max(source_ids) - min(source_ids) + 1 - len(source_id_set)) if source_ids else 0,
        },
        "draw_id": {"count": len(draw_ids), "unique": len(set(draw_ids))},
    }
    report["unknown_zero_top_tier_prize_rows"] = zero_prize_rows
    return report


def audit_history(path: Path, *, observed_at: datetime, baseline=HistoryBaseline()):
    before = file_sha256(path)
    provenance = RawProvenance(SOURCE_KEY, before, observed_at, NORMALIZER_VERSION)
    results = normalize_rows(read_json_rows(path), provenance)
    return build_history_report(
        results, source_sha256_before=before,
        source_sha256_after=file_sha256(path), baseline=baseline,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description="Diagnóstico local do EuroMillions, sem escrita de candidatos")
    parser.add_argument(
        "source", nargs="?", type=Path,
        default=Path(__file__).resolve().parents[2] / "data/raw/euro_millions/euro_millions_resultados.json",
    )
    report = audit_history(parser.parse_args(argv).source, observed_at=datetime.now(timezone.utc))
    print(report_json(report), end="")
    return 0 if (report["source_unchanged"] and report["baseline_matches"]
                 and report["summary"]["valid_rows"] == report["summary"]["total_rows"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
