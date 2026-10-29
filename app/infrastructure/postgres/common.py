"""SQL parametrizado e tradução restrita de erros; sem commits de repositório."""
import psycopg
from psycopg import sql

from app.application.persistence import PersistenceError


def insert(db, table, **values):
    db.execute(sql.SQL("INSERT INTO lb.{} ({}) VALUES ({})").format(
        sql.Identifier(table), sql.SQL(",").join(map(sql.Identifier, values)),
        sql.SQL(",").join(sql.Placeholder() for _ in values)), list(values.values()))
    return values.get("id")


def advisory_command(db, namespace: str, key: str):
    import hashlib
    token = int.from_bytes(hashlib.sha256(f"{namespace}:{key}".encode()).digest()[:8], "big", signed=True)
    db.execute("SELECT pg_advisory_xact_lock(%s)", (token,))


def translate(error: psycopg.Error) -> PersistenceError:
    state = error.sqlstate
    if state in ("40001", "40P01", "55P03"):
        return PersistenceError("transaction_conflict", retryable=True)
    primary = getattr(error.diag, "message_primary", "") or ""
    if state == "23514" and "lease" in primary:
        return PersistenceError("lease_lost")
    if state in ("23503", "23514", "23502", "22003"):
        return PersistenceError("invalid_revision")
    if state == "23505":
        return PersistenceError("identity_conflict")
    if state == "23P01":
        return PersistenceError("rule_period_conflict")
    return PersistenceError("database_unavailable")
