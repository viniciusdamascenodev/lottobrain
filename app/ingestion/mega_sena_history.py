"""Auditoria histórica em memória; a CLI escreve apenas diagnóstico no stdout."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Iterable

from app.domain import RawProvenance, ValueStatus
from app.ingestion.mega_sena import (
    SOURCE_KEY,
    NormalizationResult,
    file_sha256,
    iter_xlsx_rows,
    normalize_rows,
)


REPORT_VERSION = "1"
NORMALIZER_VERSION = "spec-0004"


@dataclass(frozen=True, slots=True)
class HistoryBaseline:
    source_sha256: str = "0e1936e3ac94a35a89c13ef31d705d3fb363239779ad6224b5e41171a3238686"
    total_rows: int = 2954
    first_contest: int = 1
    last_contest: int = 2954
    first_date: str = "1996-03-11"
    last_date: str = "2025-12-20"
    missing_winner_locations: int = 2331
    missing_observations: int = 2059


def _json_value(value):
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(f"Tipo não serializável no diagnóstico: {type(value).__name__}")


def report_json(report: dict) -> str:
    """Ordenação estável e sem relógio/paths absolutos no diagnóstico."""
    return json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2, default=_json_value) + "\n"


def build_history_report(
    results: Iterable[NormalizationResult],
    *,
    source_sha256_before: str,
    source_sha256_after: str,
    baseline: HistoryBaseline = HistoryBaseline(),
) -> dict:
    results = tuple(results)
    key_counts = Counter(result.canonical_key for result in results if result.canonical_key is not None)
    duplicated_keys = {key for key, count in key_counts.items() if count > 1}
    issues = []
    payloads = []
    dates = []
    contests = []
    metadata_missing = Counter()
    money = {}
    winners = Counter()
    main_numbers = []

    for row_position, result in enumerate(results, start=1):
        for issue in result.issues:
            issues.append({"row_position": row_position, "canonical_key": result.canonical_key, **asdict(issue)})
        if result.canonical_key in duplicated_keys:
            issues.append({
                "row_position": row_position,
                "canonical_key": result.canonical_key,
                "code": "history.duplicate_key",
                "path": "canonical_key",
                "message": "chave repetida; nenhuma cópia é elegível",
                "observed": result.canonical_key,
                "expected": "unique",
            })

        if result.candidate is None:
            payloads.append({"canonical_key": result.canonical_key, "candidate": None, "issues": [asdict(issue) for issue in result.issues]})
            continue

        candidate = result.candidate
        payload = asdict(candidate)
        # O instante da leitura local não altera o conteúdo do concurso.
        # Fonte e hash são vinculados no relatório, fora do hash de conteúdo.
        payload.pop("provenance")
        payloads.append({"canonical_key": result.canonical_key, "candidate": payload, "issues": [asdict(issue) for issue in result.issues]})
        dates.append(candidate.draw_date.isoformat())
        if candidate.official_draw_number is not None:
            contests.append(int(candidate.official_draw_number))
        metadata = dict(candidate.metadata)
        for key in ("winner_locations_source_text", "observation_source_text"):
            if key not in metadata:
                metadata_missing[key] += 1
        for series in candidate.series:
            if series.key == "primary":
                for component in series.components:
                    if component.key == "main":
                        main_numbers.extend(value for value in component.values if type(value) is int)
        amounts = [(amount.kind, amount) for amount in candidate.monetary_amounts]
        for tier in candidate.prize_tiers:
            if tier.winners is not None:
                winners[tier.tier_key] += tier.winners
            if tier.prize_per_winner is not None:
                amounts.append((f"prize_per_winner.{tier.tier_key}", tier.prize_per_winner))
        for key, amount in amounts:
            counter = money.setdefault(key, Counter())
            counter[amount.status.value] += 1
            if amount.status is ValueStatus.KNOWN and amount.amount == Decimal("0"):
                counter["zero"] += 1

    invalid_positions = {issue["row_position"] for issue in issues}
    invalid_positions.update(
        position
        for position, result in enumerate(results, start=1)
        if not result.is_valid or result.canonical_key is None
    )
    missing_identity_rows = sum(result.canonical_key is None for result in results)
    first_contest = min(contests, default=None)
    last_contest = max(contests, default=None)
    missing_contests = (
        sorted(set(range(first_contest, last_contest + 1)) - set(contests))
        if contests else []
    )
    canonical_json = json.dumps(payloads, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=_json_value)
    summary = {
        "total_rows": len(results),
        "candidate_rows": sum(result.candidate is not None for result in results),
        "valid_rows": sum(result.is_valid and result.canonical_key not in duplicated_keys for result in results),
        "invalid_rows": len(invalid_positions),
        "missing_identity_rows": missing_identity_rows,
        "unique_keys": len(key_counts),
        "duplicate_key_rows": sum(key_counts[key] for key in duplicated_keys),
        "first_contest": first_contest,
        "last_contest": last_contest,
        "first_date": min(dates, default=None),
        "last_date": max(dates, default=None),
        "missing_contests": missing_contests,
        "missing_winner_locations": metadata_missing["winner_locations_source_text"],
        "missing_observations": metadata_missing["observation_source_text"],
        "main_values_count": len(main_numbers),
        "main_min": min(main_numbers, default=None),
        "main_max": max(main_numbers, default=None),
    }
    comparisons = []
    for field, expected in asdict(baseline).items():
        observed = source_sha256_before if field == "source_sha256" else summary[field]
        comparisons.append({"field": field, "expected": expected, "observed": observed, "matches": observed == expected})

    return {
        "report_version": REPORT_VERSION,
        "normalizer_version": NORMALIZER_VERSION,
        "source_sha256_before": source_sha256_before,
        "source_sha256_after": source_sha256_after,
        "source_unchanged": source_sha256_before == source_sha256_after,
        "canonical_content_sha256": hashlib.sha256(canonical_json.encode("utf-8")).hexdigest(),
        "summary": summary,
        "duplicate_keys": dict(sorted((key, key_counts[key]) for key in duplicated_keys)),
        "issue_counts": dict(sorted(Counter(issue["code"] for issue in issues).items())),
        "issues": issues,
        "money_counts": dict(sorted((key, dict(sorted(counter.items()))) for key, counter in money.items())),
        "winner_totals": dict(sorted(winners.items())),
        "baseline_comparisons": comparisons,
        "baseline_matches": all(item["matches"] for item in comparisons),
    }


def audit_history(path: Path, *, observed_at: datetime, baseline: HistoryBaseline = HistoryBaseline()) -> dict:
    """Captura um snapshot local em memória; não presume data de download."""
    before = file_sha256(path)
    provenance = RawProvenance(SOURCE_KEY, before, observed_at, NORMALIZER_VERSION)
    results = normalize_rows(iter_xlsx_rows(path), provenance)
    after = file_sha256(path)
    return build_history_report(
        results,
        source_sha256_before=before,
        source_sha256_after=after,
        baseline=baseline,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Diagnóstico da Mega-Sena em memória, sem escrita de dados")
    default_source = Path(__file__).resolve().parents[2] / "data/raw/mega_sena/mega_sena_resultados.xlsx"
    parser.add_argument("source", nargs="?", type=Path, default=default_source)
    args = parser.parse_args(argv)
    report = audit_history(args.source, observed_at=datetime.now(timezone.utc))
    print(report_json(report), end="")
    summary = report["summary"]
    return 0 if report["source_unchanged"] and report["baseline_matches"] and summary["valid_rows"] == summary["total_rows"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
