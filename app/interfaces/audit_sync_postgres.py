"""Diagnóstico PostgreSQL Mega-Sena opt-in, somente leitura, emitido em stdout."""
import argparse
import json
import os
from pathlib import Path
from uuid import UUID

from app.application.audit_sync_postgres import AuditMegaSenaPostgres, SyncAuditRequest
from app.application.persistence import PersistenceError


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=UUID, required=True)
    parser.add_argument("--object-root", type=Path, required=True)
    parser.add_argument("--max-batches", type=int, default=100)
    parser.add_argument("--max-steps", type=int, default=5000)
    args = parser.parse_args(argv)
    try:
        request = SyncAuditRequest(args.checkpoint, args.max_batches, args.max_steps)
    except ValueError:
        print(json.dumps({"error": "invalid_arguments"}))
        return 1
    dsn = os.environ.get("LOTTOBRAIN_PG_AUDIT_DSN")
    if not dsn:
        print(json.dumps({"error": "audit_database_not_configured"}))
        return 1
    from app.infrastructure.postgres.sync_audit import PgSyncAuditReader
    from app.infrastructure.raw_storage import LocalRawStorage
    try:
        report = AuditMegaSenaPostgres(PgSyncAuditReader(dsn=dsn), LocalRawStorage(args.object_root)).execute(request)
        print(json.dumps(report, sort_keys=True, ensure_ascii=False))
        return 0 if report["status"] == "healthy" else 2
    except (PersistenceError, OSError):
        # Não emitir DSN, SQL, caminho ou mensagem arbitrária da infraestrutura.
        print(json.dumps({"error": "audit_unavailable"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
