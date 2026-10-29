"""Coleta SQL manual de um concurso, ou replay de receipt SQL já arquivado."""
import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
from uuid import UUID

from app.application.collect_mega_sena import CollectionError
from app.application.persistence import PersistenceError, command_key


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--contest",type=int)
    mode.add_argument("--replay",type=UUID)
    parser.add_argument("--command-key",required=True)
    parser.add_argument("--object-root",type=Path,required=True)
    args = parser.parse_args(argv)
    try:
        command_key(args.command_key)
        if args.contest is not None and args.contest < 1:
            raise ValueError("concurso inválido")
        root = args.object_root.resolve()
        repository = Path(__file__).resolve().parents[2]
        if root == repository or any(root == protected or root.is_relative_to(protected)
                                      for protected in (repository / "data/raw",repository / "data/collections")):
            raise ValueError("raiz de objetos protegida")
    except ValueError:
        print(json.dumps({"error":"invalid_arguments"}))
        return 1
    dsn = os.environ.get("LOTTOBRAIN_PG_DSN")
    if not dsn:
        print(json.dumps({"error":"database_not_configured"}))
        return 1
    from app.application.persist_mega_sena import CollectMegaSenaPostgres, ProcessMegaSena
    from app.infrastructure.postgres.uow import PgUnitOfWorkFactory
    from app.infrastructure.raw_storage import LocalRawStorage
    from app.infrastructure.caixa_http import CaixaMegaSenaHttp
    units = PgUnitOfWorkFactory(dsn=dsn)
    storage = LocalRawStorage(root)
    try:
        if args.replay:
            result = ProcessMegaSena(units,storage).execute(args.replay,args.command_key)
        else:
            result = CollectMegaSenaPostgres(units,storage,CaixaMegaSenaHttp()).execute(args.contest,args.command_key)
        print(json.dumps(asdict(result),default=str,sort_keys=True))
        return 2 if result.outcome == "quarantined" else 0
    except (PersistenceError,CollectionError) as error:
        print(json.dumps({"error":str(error)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
