"""Operação SQL limitada da etapa 6; sem coleta externa, carga integral ou HTTP."""

import argparse
import json
import os
from pathlib import Path
from uuid import UUID

from app.application.datasets import DatasetService
from app.application.persistence import PersistenceError, transact
from app.application.result_persistence import MAX_ARTIFACT_BYTES, PersistQualifiedResult


def _factory():
    from sqlalchemy.engine import make_url

    from app.infrastructure.postgres.uow import PgUnitOfWorkFactory

    value = os.environ.get("LOTTOBRAIN_DATABASE_URL")
    if not value:
        raise PersistenceError("database_not_configured")
    try:
        url = make_url(value)
    except Exception:
        raise PersistenceError("invalid_database_configuration") from None
    if (
        url.drivername not in {"postgresql", "postgresql+psycopg"}
        or not url.host
        or not url.database
    ):
        raise PersistenceError("invalid_database_configuration")
    if url.host not in {"127.0.0.1", "localhost", "::1"} and url.query.get("sslmode") not in {
        "require",
        "verify-ca",
        "verify-full",
    }:
        raise PersistenceError("database_tls_required")
    return PgUnitOfWorkFactory(
        dsn=url.set(drivername="postgresql").render_as_string(hide_password=False)
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    actions.add_parser("bootstrap")
    actions.add_parser("inspect")
    sample = actions.add_parser("sample")
    sample.add_argument("--lottery", required=True)
    sample.add_argument("--file", type=Path, required=True)
    sample.add_argument("--ordinal", type=int, required=True)
    sample.add_argument("--object-root", type=Path, required=True)
    sample.add_argument("--command-key", required=True)
    sample.add_argument("--allow-correction", action="store_true")
    policy = actions.add_parser("policy")
    policy.add_argument("--lottery", required=True)
    policy.add_argument("--version", required=True)
    policy.add_argument("--source", action="append", required=True)
    policy.add_argument("--actor", required=True)
    approve = actions.add_parser("approve")
    approve.add_argument("--policy", type=UUID, required=True)
    approve.add_argument("--revision", type=UUID, action="append", required=True)
    approve.add_argument("--actor", required=True)
    approve.add_argument("--command-key", required=True)
    activate = actions.add_parser("activate")
    activate.add_argument("--dataset", type=UUID, required=True)
    activate.add_argument("--expected-version", type=int, required=True)
    activate.add_argument("--actor", required=True)
    activate.add_argument("--command-key", required=True)
    read = actions.add_parser("read")
    read.add_argument("--lottery", required=True)
    read.add_argument("--dataset", type=UUID)
    read.add_argument("--offset", type=int, default=0)
    read.add_argument("--limit", type=int, default=50)
    args = parser.parse_args(argv)
    try:
        factory = _factory()
        datasets = DatasetService(factory)
        if args.action == "inspect":
            result = transact(factory, lambda unit: unit.admin.inspect())
        elif args.action == "bootstrap":
            result = transact(factory, lambda unit: unit.admin.bootstrap())
        elif args.action == "sample":
            from app.infrastructure.persistence_samples import prepare_sample
            from app.infrastructure.raw_storage import LocalRawStorage

            repository = Path(__file__).resolve().parents[2]
            root = args.object_root.resolve()
            # Objetos apenas em diretório dedicado; nada escreve sobre arquivos existentes.
            if root == repository or any(
                root == p or root.is_relative_to(p)
                for p in (
                    repository / "data",
                    repository / "docs",
                    repository / "tests",
                    repository / "app",
                    repository / "migrations",
                    repository / ".git",
                    repository / ".agents",
                    repository / ".codex",
                    repository / ".github",
                    repository / "frontend",
                    repository / "scripts",
                )
            ):
                raise ValueError("Diretório de objetos protegido.")
            prepared = prepare_sample(args.lottery, args.file, args.ordinal)
            result = PersistQualifiedResult(
                factory, LocalRawStorage(root, max_bytes=MAX_ARTIFACT_BYTES)
            ).execute(prepared, args.command_key, allow_correction=args.allow_correction)
        elif args.action == "policy":
            result = {
                "policy_id": datasets.policy(args.lottery, args.version, args.source, args.actor)
            }
        elif args.action == "approve":
            if len(args.revision) > 100:
                raise ValueError("A CLI da etapa 6 limita a seleção a 100 amostras.")
            result = {
                "dataset_id": datasets.approve(
                    args.policy, args.revision, args.actor, args.command_key
                )
            }
        elif args.action == "activate":
            result = datasets.activate(
                args.dataset, args.expected_version, args.actor, args.command_key
            )
        else:
            result = datasets.read(
                args.lottery, dataset_id=args.dataset, offset=args.offset, limit=args.limit
            )
        print(json.dumps(result, default=str, ensure_ascii=False, sort_keys=True))
        return 2 if isinstance(result, dict) and result.get("outcome") == "quarantined" else 0
    except PersistenceError as error:
        print(json.dumps({"error": error.code}))
        return 1
    except (ValueError, OSError):
        print(json.dumps({"error": "invalid_arguments_or_local_file"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
