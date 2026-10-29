"""python -m app.interfaces.collect_mega_sena --contest 2954"""
from __future__ import annotations

import argparse
from pathlib import Path

from app.application.collect_mega_sena import CollectMegaSena, CollectionError, canonical_json
from app.infrastructure.caixa_http import CaixaMegaSenaHttp
from app.infrastructure.local_collection import LocalCollectionWorkspace


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Coleta manual limitada a um concurso Mega-Sena")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--contest", type=int, help="número explícito; omitido consulta último publicado")
    mode.add_argument("--replay", help="receipt_id para retomar sem rede")
    parser.add_argument("--workspace", type=Path, default=Path("data/collections/mega_sena"))
    args = parser.parse_args(argv)
    if args.contest is not None and args.contest <= 0:
        parser.error("--contest deve ser positivo")
    workspace = LocalCollectionWorkspace(args.workspace)
    try:
        with workspace.exclusive():
            service = CollectMegaSena(CaixaMegaSenaHttp(), workspace, workspace)
            if args.replay:
                archived = workspace.load(args.replay)
                # Revalida também a identidade implícita em uma URL de concurso.
                suffix = archived.response.url.rsplit("/", 1)[-1]
                expected = int(suffix) if suffix.isascii() and suffix.isdigit() else None
                result = service.replay(archived, expected_contest=expected)
            else:
                result = service.execute(args.contest)
        print(canonical_json(result))
        return 2 if result["outcome"] == "quarantined" else 0
    except CollectionError as exc:
        print(canonical_json({"outcome": "failed", "code": str(exc)}))
        return 1
    except (OSError, ValueError, KeyError, TypeError):
        print(canonical_json({"outcome": "failed", "code": "local_workspace_failure"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
