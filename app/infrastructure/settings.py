"""Configuração do processo HTTP; independente do catálogo/coletores legados."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal, cast
from urllib.parse import parse_qs, urlsplit

Environment = Literal["local", "test", "preview", "staging", "production"]
ENVIRONMENTS = ("local", "test", "preview", "staging", "production")


@dataclass(frozen=True)
class Settings:
    environment: Environment = "local"
    web_origin: str = "http://127.0.0.1:3000"
    database_url: str | None = field(default=None, repr=False)

    @classmethod
    def from_environment(cls, values: Mapping[str, str]) -> Settings:
        environment = values.get("LOTTOBRAIN_ENV", "local")
        if environment not in ENVIRONMENTS:
            raise ValueError("LOTTOBRAIN_ENV inválido.")
        local = environment in ("local", "test")
        origin = values.get("LOTTOBRAIN_WEB_ORIGIN", "http://127.0.0.1:3000" if local else "")
        parsed = urlsplit(origin)
        if (
            parsed.scheme not in ("http", "https")
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
            or (not local and parsed.scheme != "https")
            or (
                parsed.scheme == "http" and parsed.hostname not in ("localhost", "127.0.0.1", "::1")
            )
        ):
            raise ValueError(
                "LOTTOBRAIN_WEB_ORIGIN deve ser uma origem HTTPS; HTTP só em loopback local."
            )
        database_url = values.get("LOTTOBRAIN_DATABASE_URL") or None
        if database_url:
            database = urlsplit(database_url)
            if database.scheme != "postgresql+psycopg" or not database.hostname:
                raise ValueError("LOTTOBRAIN_DATABASE_URL exige PostgreSQL com psycopg.")
            if not local and parse_qs(database.query).get("sslmode", [""])[0] not in (
                "require",
                "verify-ca",
                "verify-full",
            ):
                raise ValueError("Conexão PostgreSQL não local exige TLS.")
        return cls(cast(Environment, environment), origin.rstrip("/"), database_url)
