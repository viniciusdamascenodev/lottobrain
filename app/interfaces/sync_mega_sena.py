"""python -m app.interfaces.sync_mega_sena --bootstrap-history"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from app.application.collect_mega_sena import CollectMegaSena, CollectionError, canonical_json
from app.application.sync_mega_sena import SyncMegaSena, SyncPolicy
from app.infrastructure.caixa_http import CaixaMegaSenaHttp
from app.infrastructure.local_collection import LocalCollectionWorkspace
from app.infrastructure.mega_sena_baseline import verified_history_anchor

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Sincronização manual limitada da Mega-Sena")
    parser.add_argument("--workspace", type=Path, default=Path("data/collections/mega_sena"))
    parser.add_argument("--bootstrap-history", action="store_true", help="inicializar pelo XLSX auditado até 2954")
    parser.add_argument("--max-requests", type=int, default=4, help="máximo de GETs, incluindo descoberta (1–10)")
    parser.add_argument("--review-window", type=int, default=3, help="concursos incrementais recentes a revisar (0–20)")
    parser.add_argument("--interval", type=float, default=2, help="intervalo mínimo entre consultas, em segundos (2–30)")
    args = parser.parse_args(argv)
    try:
        policy = SyncPolicy(args.max_requests, args.review_window, args.interval)
    except ValueError as exc:
        parser.error(str(exc))
    workspace = LocalCollectionWorkspace(args.workspace)
    try:
        with workspace.exclusive():
            anchor = verified_history_anchor(
                PROJECT_ROOT / "data/raw/mega_sena/mega_sena_resultados.xlsx"
            ) if args.bootstrap_history else None
            collector = CollectMegaSena(CaixaMegaSenaHttp(), workspace, workspace)
            service = SyncMegaSena(collector, workspace, wait=time.sleep)
            report = service.execute(policy, anchor=anchor)
        print(canonical_json(report))
        if report["stop_reason"] in {"collection_stopped", "source_behind_cursor"}:
            return 2
        return 0
    except CollectionError as exc:
        print(canonical_json({"outcome": "failed", "code": str(exc)}))
        return 1
    except (OSError, ValueError, KeyError, TypeError):
        print(canonical_json({"outcome": "failed", "code": "local_workspace_failure"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
