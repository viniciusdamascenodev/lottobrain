"""Bootstrap explícito a partir do artefato auditado pela SPEC-0005."""
from pathlib import Path

from app.application.collect_mega_sena import CollectionError
from app.application.sync_mega_sena import SyncAnchor
from app.ingestion.mega_sena import file_sha256
from app.ingestion.mega_sena_history import HistoryBaseline


def verified_history_anchor(path: Path) -> SyncAnchor:
    baseline = HistoryBaseline()
    if file_sha256(path) != baseline.source_sha256:
        raise CollectionError("historical_baseline_hash_mismatch")
    return SyncAnchor(baseline.last_contest, baseline.source_sha256)
