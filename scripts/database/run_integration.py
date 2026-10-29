"""Cluster descartável dedicado. Nunca se conecta a PostgreSQL já instalado/em uso.

Uso: python scripts/database/run_integration.py --pg-bin <pasta PostgreSQL 17/bin>
Gera credenciais aleatórias, não as imprime e preserva somente logs/dados locais
ignorados pelo Git. O cluster é desligado no finally, inclusive após falha de teste.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pg-bin", required=True, type=Path)
    parser.add_argument("--test-pattern", default="test*.py", help="filtro unittest para diagnóstico; a regressão completa usa o padrão")
    args = parser.parse_args()
    suffix = ".exe" if os.name == "nt" else ""
    pg_ctl = args.pg_bin.resolve() / ("pg_ctl" + suffix)
    initdb = args.pg_bin.resolve() / ("initdb" + suffix)
    version = subprocess.check_output([pg_ctl, "--version"], text=True).strip()
    if " 17." not in version:
        parser.error("Este ambiente exige binários PostgreSQL 17.x.")
    run_dir = ROOT / ".local-postgres" / "runs" / uuid4().hex
    run_dir.mkdir(parents=True)
    data_dir = run_dir / "data"
    password = secrets.token_urlsafe(32)
    password_file = run_dir / "password.tmp"
    password_file.write_text(password, encoding="ascii")
    # Escolhe porta local livre; se houver corrida, pg_ctl falha e não conecta a outro servidor.
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    started = False
    start_attempted = False
    try:
        subprocess.run([initdb, "-D", data_dir, "-U", "lb_admin", "--pwfile", password_file,
                        "--auth-host=scram-sha-256", "--auth-local=scram-sha-256",
                        "--encoding=UTF8", "--locale=C"], check=True, capture_output=True)
        password_file.unlink()
        # Arquivo, não PIPE: processos filhos persistentes no Windows podem herdar
        # o pipe e impedir communicate() de retornar mesmo com pg_ctl concluído.
        with (run_dir / "control.log").open("wb") as control_log:
            start_attempted = True
            subprocess.run([pg_ctl, "-D", data_dir, "-l", run_dir / "server.log", "-w", "-t", "30",
                            "-o", f"-h 127.0.0.1 -p {port} -c shared_buffers=32MB -c max_connections=20", "start"], check=True,
                           stdout=control_log, stderr=subprocess.STDOUT, timeout=40)
        started = True
        import psycopg
        from psycopg import sql
        from sqlalchemy import URL

        with psycopg.connect(host="127.0.0.1", port=port, user="lb_admin", password=password,
                             dbname="postgres", autocommit=True, connect_timeout=10) as admin:
            # Confirma a identidade do cluster criado, não apenas host/porta.
            if Path(admin.execute("SHOW data_directory").fetchone()[0]).resolve() != data_dir.resolve():
                raise RuntimeError("Cluster inesperado; interrompido.")
            admin.execute(sql.SQL("CREATE ROLE lb_migrator LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {}")
                          .format(sql.Literal(password)))
            admin.execute("CREATE DATABASE lottobrain_test OWNER lb_migrator")
        env = os.environ.copy()
        env["LOTTOBRAIN_DATABASE_URL"] = URL.create("postgresql+psycopg", username="lb_migrator", password=password,
                      host="127.0.0.1", port=port, database="lottobrain_test").render_as_string(hide_password=False)
        env["LOTTOBRAIN_TEST_ADMIN_DSN"] = psycopg.conninfo.make_conninfo(host="127.0.0.1", port=port,
                      user="lb_admin", password=password, dbname="lottobrain_test")
        env["LOTTOBRAIN_TEST_ISOLATED"] = str(data_dir.resolve())
        print(f"Integração isolada: {version}; log: {run_dir.relative_to(ROOT)}/server.log", flush=True)
        return subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests/database", "-p",args.test_pattern,"-v"],
                              cwd=ROOT, env=env).returncode
    except subprocess.CalledProcessError as exc:
        # Não reproduzir argv/ambiente (podem conter DSNs).
        print(f"Falha no provisionamento isolado (código {exc.returncode}); consulte {run_dir}.", file=sys.stderr)
        details = (exc.stderr or exc.stdout or b"")
        if isinstance(details, bytes):
            details = details.decode("utf-8",errors="replace")
        print(details.replace(password,"<redacted>"), file=sys.stderr)
        return 1
    finally:
        if password_file.exists():
            password_file.unlink()
        if started or (start_attempted and subprocess.run([pg_ctl,"-D",data_dir,"status"],capture_output=True).returncode == 0):
            stopped = subprocess.run([pg_ctl, "-D", data_dir, "-m", "fast", "-w", "-t", "55", "stop"], capture_output=True)
            if stopped.returncode:
                raise RuntimeError(f"Não foi possível desligar o cluster isolado: {run_dir}")


if __name__ == "__main__":
    raise SystemExit(main())
