"""python -m app.interfaces.audit_mega_sena [--output relatório-novo.json]"""
from __future__ import annotations

import argparse
from pathlib import Path

from app.application.audit_mega_sena import AuditMegaSena
from app.application.collect_mega_sena import canonical_json
from app.infrastructure.local_audit import LocalAuditReader

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Auditoria offline e somente leitura da ingestão Mega-Sena")
    parser.add_argument("--workspace", type=Path, default=Path("data/collections/mega_sena"))
    parser.add_argument("--output", type=Path, help="salvar relatório novo fora do workspace; não sobrescreve arquivo")
    args = parser.parse_args(argv)
    if args.output and args.output.resolve().is_relative_to(args.workspace.resolve()):
        parser.error("--output deve ficar fora do workspace auditado")
    if args.output and args.output.exists():
        parser.error("--output já existe; escolha outro nome para preservar o relatório anterior")
    reader = LocalAuditReader(args.workspace, PROJECT_ROOT / "data/raw/mega_sena/mega_sena_resultados.xlsx")
    try:
        report = AuditMegaSena(reader).execute()
        serialized = canonical_json(report) + "\n"
        if args.output:
            with args.output.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(serialized)
        print(serialized, end="")
        return 2 if report["status"] == "failed" else 0
    except OSError:
        print(canonical_json({"status": "failed", "code": "audit_io_failure"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
