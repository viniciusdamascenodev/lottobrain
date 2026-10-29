"""Fronteiras da CLI/configuração; não usam rede nem simulam dados operacionais."""

from pathlib import Path

import pytest

from app.application.datasets import DatasetService
from app.application.persistence import PersistenceError
from app.infrastructure.persistence_samples import prepare_sample
from app.infrastructure.raw_storage import LocalRawStorage
from app.interfaces.persistence import _factory, main


@pytest.mark.parametrize(
    "dsn,code",
    [
        ("not-a-database-url", "invalid_database_configuration"),
        ("sqlite:///local.db", "invalid_database_configuration"),
        (
            "postgresql://operator:redaction-test-only@db.example/lottobrain",
            "database_tls_required",
        ),
    ],
)
def test_cli_rejects_bad_or_insecure_configuration_without_exposing_password(
    monkeypatch, capsys, dsn, code
):
    monkeypatch.setenv("LOTTOBRAIN_DATABASE_URL", dsn)
    assert main(["bootstrap"]) == 1
    output = capsys.readouterr()
    assert code in output.out
    assert "redaction-test-only" not in output.out + output.err
    assert dsn not in output.out + output.err


def test_cli_requires_explicit_configuration(monkeypatch):
    monkeypatch.delenv("LOTTOBRAIN_DATABASE_URL", raising=False)
    with pytest.raises(PersistenceError, match="database_not_configured"):
        _factory()


def test_pagination_and_selection_are_validated_before_opening_database():
    def forbidden():
        pytest.fail("Argumento inválido não deve abrir conexão.")

    service = DatasetService(forbidden)
    for kwargs in (
        {"limit": 0},
        {"limit": 101},
        {"limit": True},
        {"offset": -1},
        {"dataset_id": "not-uuid"},
    ):
        with pytest.raises(ValueError):
            service.read("mega_sena", **kwargs)
    with pytest.raises(ValueError):
        service.approve("not-uuid", [], "operator", "test")
    with pytest.raises(ValueError):
        service.policy("mega_sena", "v1", ["source", "source"], "operator")


def test_sample_rejects_unsupported_profile_and_wrong_format(tmp_path):
    path = tmp_path / "file.txt"
    path.write_text("not-a-result", encoding="utf-8")
    before = path.read_bytes()
    for slug, ordinal in (("unknown", 1), ("mega_sena", 1), ("mega_sena", 0)):
        with pytest.raises(ValueError):
            prepare_sample(slug, path, ordinal)
    assert path.read_bytes() == before


def test_storage_limits_are_explicit_and_existing_default_remains_small(tmp_path):
    small = LocalRawStorage(tmp_path / "small")
    assert small.max_bytes == 262144
    with pytest.raises(PersistenceError):
        small.put(b"x" * 262145)
    bigger = LocalRawStorage(tmp_path / "offline-sample", max_bytes=8 * 1024 * 1024)
    body = b"x" * 262145
    digest, key = bigger.put(body)
    assert bigger.read(key, digest, len(body)) == body
    assert (Path(tmp_path) / "small").exists() is False


@pytest.mark.parametrize("folder", [".git", "data/raw", "docs", "app", "frontend"])
def test_cli_protects_repository_directories_before_parsing(monkeypatch, capsys, folder):
    monkeypatch.setenv(
        "LOTTOBRAIN_DATABASE_URL", "postgresql://operator:local-test-only@127.0.0.1/local"
    )

    def forbidden(*args):
        pytest.fail("Diretório protegido deve ser recusado antes de ler o arquivo.")

    monkeypatch.setattr("app.infrastructure.persistence_samples.prepare_sample", forbidden)
    root = Path(__file__).resolve().parents[1]
    assert (
        main(
            [
                "sample",
                "--lottery",
                "mega_sena",
                "--file",
                "unused.xlsx",
                "--ordinal",
                "1",
                "--object-root",
                str(root / folder),
                "--command-key",
                "test",
            ]
        )
        == 1
    )
    assert "invalid_arguments_or_local_file" in capsys.readouterr().out
