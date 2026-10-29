"""Mesmas verificações locais e de CI; sem acesso ao banco operacional ou às fontes."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NEW_PYTHON = [
    "app/infrastructure/settings.py",
    "app/interfaces/http",
    "scripts/engineering/check.py",
    "tests/test_platform_foundation.py",
    "tests/conftest.py",
    "app/application/datasets.py",
    "app/application/result_persistence.py",
    "app/infrastructure/persistence_samples.py",
    "app/infrastructure/postgres/profile_catalog.py",
    "app/infrastructure/postgres/relational_content.py",
    "app/infrastructure/postgres/results.py",
    "app/infrastructure/postgres/datasets.py",
    "app/interfaces/persistence.py",
    "tests/test_persistence_commands.py",
]
TEXT_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".mjs",
    ".json",
    ".toml",
    ".yml",
    ".yaml",
    ".md",
    ".txt",
    ".ini",
}
SECRET_PATTERNS = {
    "chave privada": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "token GitHub": re.compile(
        rb"\b(?:gh[pousr]_[A-Za-z0-9]{36,255}|github_pat_[A-Za-z0-9_]{70,255})\b"
    ),
}


def inspect_files(paths: list[Path]) -> list[str]:
    """Retorna somente nomes/tipos; nunca imprime o conteúdo da credencial."""
    findings = []
    for path in paths:
        if not path.is_file():
            continue
        if path.name.startswith(".env") and not path.name.endswith(".example"):
            findings.append(f"{path.name}: arquivo de ambiente versionado")
        if path.suffix in TEXT_EXTENSIONS or path.name.startswith(".env"):
            body = path.read_bytes()
            for label, pattern in SECRET_PATTERNS.items():
                if pattern.search(body):
                    findings.append(
                        f"{path.relative_to(ROOT) if path.is_relative_to(ROOT) else path.name}: {label}"
                    )
    return findings


def repository_safety() -> int:
    files = (
        subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT
        )
        .decode("utf-8")
        .split("\0")
    )
    findings = inspect_files([ROOT / name for name in files if name])
    if findings:
        print("Verificação de credenciais falhou:\n" + "\n".join(findings), file=sys.stderr)
        return 1
    print(
        "Verificação básica: nenhum arquivo de ambiente privado/chave/token conhecido encontrado."
    )
    return 0


def run(arguments: list[str]) -> int:
    print("Verificando:", " ".join(arguments), flush=True)
    return subprocess.run(arguments, cwd=ROOT, check=False).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", choices=["quality", "test", "secrets", "all"])
    arguments = parser.parse_args()
    commands = []
    if arguments.target in ("quality", "all"):
        commands += [
            [sys.executable, "-m", "ruff", "check", "app", "tests", "scripts", "migrations"],
            [
                sys.executable,
                "-m",
                "ruff",
                "check",
                "--extend-select",
                "E4,E7,F,I,UP,B",
                *NEW_PYTHON,
            ],
            [sys.executable, "-m", "ruff", "format", "--check", *NEW_PYTHON],
            [sys.executable, "-m", "mypy"],
        ]
    if arguments.target in ("test", "all"):
        commands.append([sys.executable, "-m", "pytest", "--junitxml=test-results/python.xml"])
    for command in commands:
        result = run(command)
        if result:
            return result
    if arguments.target in ("quality", "secrets", "all"):
        return repository_safety()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
