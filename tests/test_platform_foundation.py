import socket
from dataclasses import FrozenInstanceError

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.settings import Settings
from app.interfaces.http.main import create_app
from scripts.engineering.check import inspect_files


def test_offline_suite_rejects_unexpected_network():
    with pytest.raises(AssertionError, match="Rede bloqueada"):
        socket.create_connection(("example.invalid", 443))


def test_credentials_check_fails_without_disclosing_token(tmp_path):
    token = "ghp_" + "a" * 36
    file = tmp_path / "accidental.py"
    file.write_text('credential = "' + token + '"', encoding="utf-8")
    findings = inspect_files([file])
    assert findings and all(token not in finding for finding in findings)
    assert inspect_files([tmp_path / "not-present.py"]) == []


def test_environment_typo_fails_closed():
    with pytest.raises(ValueError, match="LOTTOBRAIN_ENV"):
        Settings.from_environment({"LOTTOBRAIN_ENV": "producao"})


@pytest.mark.parametrize("environment", ["preview", "staging", "production"])
def test_remote_environment_requires_secure_origin_and_database_tls(environment):
    with pytest.raises(ValueError):
        Settings.from_environment({"LOTTOBRAIN_ENV": environment})
    values = {"LOTTOBRAIN_ENV": environment, "LOTTOBRAIN_WEB_ORIGIN": "https://web.example.invalid"}
    with pytest.raises(ValueError, match="TLS"):
        Settings.from_environment(
            {**values, "LOTTOBRAIN_DATABASE_URL": "postgresql+psycopg://db.example.invalid/db"}
        )
    assert (
        Settings.from_environment(
            {
                **values,
                "LOTTOBRAIN_DATABASE_URL": "postgresql+psycopg://db.example.invalid/db?sslmode=require",
            }
        ).environment
        == environment
    )


@pytest.mark.parametrize(
    "origin",
    [
        "http://example.invalid",
        "https://user:secret@example.invalid",
        "https://example.invalid/path",
        "https://example.invalid?token=x",
    ],
)
def test_origin_rejects_unsafe_configuration(origin):
    with pytest.raises(ValueError):
        Settings.from_environment({"LOTTOBRAIN_WEB_ORIGIN": origin})


def test_database_configuration_is_not_exposed_in_repr():
    settings = Settings.from_environment(
        {"LOTTOBRAIN_DATABASE_URL": "postgresql+psycopg://private.example.invalid/db"}
    )
    assert "private.example.invalid" not in repr(settings)
    with pytest.raises(FrozenInstanceError):
        settings.environment = "production"


def test_health_is_not_readiness_and_responses_cannot_be_cached():
    client = TestClient(create_app(Settings(environment="test")))
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").status_code == 503
    for path in ["/healthz", "/readyz", "/api/v1/loterias/mega_sena", "/docs", "/openapi.json"]:
        response = client.get(path)
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-content-type-options"] == "nosniff"


@pytest.mark.parametrize("method", ["get", "post", "put", "patch", "delete", "options"])
def test_business_routes_never_expose_data_before_access_is_implemented(method):
    client = TestClient(create_app(Settings(environment="test")))
    response = getattr(client, method)("/api/v1/loterias/mega_sena")
    assert response.status_code == 503
    assert response.json()["code"] == "PLATFORM_NOT_READY"
    assert "3075" not in response.text
