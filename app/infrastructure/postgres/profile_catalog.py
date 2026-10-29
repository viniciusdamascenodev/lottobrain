"""Bootstrap operacional e qualificação dos perfis existentes; sem rede ou fixtures."""

from dataclasses import asdict
from datetime import date
from enum import Enum
from uuid import uuid4

from psycopg import sql

from app.application.historical_content import PROFILES, digest
from app.application.persistence import CatalogBinding, PersistenceError
from app.catalog import CATALOG
from app.infrastructure.postgres.common import advisory_command, insert

# Fontes atuais qualificadas na etapa 2. Cadastro não implementa aquisição/parsing.
# Chaves novas preservam os contratos/URLs das capturas históricas.
CURRENT_SOURCES = {
    "mega_sena": (
        "caixa_mega_sena_current",
        "https://servicebus3.caixa.gov.br/portaldeloterias/api/megasena",
    ),
    "lotofacil": (
        "caixa_lotofacil_current",
        "https://servicebus3.caixa.gov.br/portaldeloterias/api/lotofacil",
    ),
    "mais_milionaria": (
        "caixa_mais_milionaria_current",
        "https://servicebus3.caixa.gov.br/portaldeloterias/api/maismilionaria",
    ),
    "powerball": ("ny_powerball_current", "https://data.ny.gov/resource/d6yy-54nr.json"),
    "mega_millions": ("ny_mega_millions_current", "https://data.ny.gov/resource/5xaw-6ayf.json"),
    "euro_millions": (
        "selae_euro_millions_current",
        "https://www.loteriasyapuestas.es/servicios/fechav3?game_id=EMIL",
    ),
}


def _plain(value):
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(v) for v in value]
    return value


def policy_catalog_hash(lottery, sources):
    """Sela as regras e a semântica dos perfis autorizados por uma política."""
    entry = CATALOG.get(lottery)
    profiles = []
    for source in sources:
        p = PROFILES[source]
        definition = next(s for s in entry.sources if s.key == source)
        profiles.append(
            {
                "key": source,
                "money": sorted(p.money),
                "tiers": sorted(p.tiers),
                "attributes": [(key, kind.__name__) for key, kind in p.attributes],
                "metadata": sorted(p.metadata),
                "scope": p.scope,
                "currency": p.currency,
                "source": _plain(asdict(definition)),
            }
        )
    return digest({"lottery": _plain(asdict(entry.lottery)), "profiles": profiles})


def _ensure(db, table, keys, **values):
    where = sql.SQL(" AND ").join(sql.SQL("{}=%s").format(sql.Identifier(k)) for k in keys)
    row = db.execute(
        sql.SQL("SELECT * FROM lb.{} WHERE {}").format(sql.Identifier(table), where),
        tuple(values[k] for k in keys),
    ).fetchone()
    if row is not None:
        if any(row[k] != v for k, v in values.items()):
            raise PersistenceError("catalog_drift")
        return row["id"]
    return insert(db, table, id=uuid4(), **values)


def bootstrap_catalog(db):
    """Adição idempotente; divergência interrompe a transação, nunca reescreve."""
    advisory_command(db, "catalog-bootstrap", "existing-six-v1")
    for entry in CATALOG.entries:
        game = entry.lottery
        lid = _ensure(
            db,
            "lottery",
            ("slug",),
            slug=game.slug,
            display_name=game.display_name,
            origin_jurisdiction=game.jurisdiction_code,
            status=game.status.value,
            default_timezone=game.default_timezone,
            default_currency=game.default_currency,
        )
        profiles = [p for p in PROFILES.values() if p.lottery == game.slug]
        for scope in {p.scope for p in profiles}:
            _ensure(
                db,
                "lottery_scope",
                ("lottery_id", "key"),
                lottery_id=lid,
                key=scope,
                kind="provider_context" if scope == "provider_pt_or_es" else "common_result",
                label="Contexto preservado da fonte"
                if scope == "provider_pt_or_es"
                else "Resultado comum",
            )
        tiers = sorted(set().union(*(p.tiers for p in profiles)))
        for rule in game.rules:
            rid = _ensure(
                db,
                "rule_version",
                ("lottery_id", "version_label"),
                lottery_id=lid,
                version_label=rule.version_label,
                valid_from=rule.valid_from,
                valid_to=rule.valid_to,
                status=rule.status.value,
                evidence_reference=rule.source_reference or "contrato existente",
                evidence_level="existing_contract",
            )
            for series in rule.series:
                sid = _ensure(
                    db,
                    "series_definition",
                    ("rule_version_id", "key"),
                    rule_version_id=rid,
                    key=series.key,
                    label=series.label,
                    role=series.role.value,
                    required=series.required,
                )
                for component in series.components:
                    fields = asdict(component)
                    fields.pop("label")
                    fields["value_type"] = component.value_type.value
                    fields["order_semantics"] = component.order_semantics.value
                    _ensure(
                        db,
                        "component_definition",
                        ("series_definition_id", "key"),
                        series_definition_id=sid,
                        **fields,
                    )
            for position, tier in enumerate(tiers):
                _ensure(
                    db,
                    "prize_tier_definition",
                    ("rule_version_id", "key"),
                    rule_version_id=rid,
                    key=tier,
                    label=tier,
                    criterion_key=tier,
                    criterion_description="Chave do contrato de normalização existente",
                    position=position,
                )
        for source in entry.sources:
            _ensure(
                db,
                "data_source",
                ("lottery_id", "key"),
                lottery_id=lid,
                key=source.key,
                authority=source.authority.value,
                readiness=source.readiness.value,
                base_url=source.url,
                data_format=source.data_format,
                purposes=list(source.purposes),
            )
        key, url = CURRENT_SOURCES[game.slug]
        _ensure(
            db,
            "data_source",
            ("lottery_id", "key"),
            lottery_id=lid,
            key=key,
            authority="official",
            readiness="contract_observed",
            base_url=url,
            data_format="json",
            purposes=["current_result"],
            policy_reference="docs/data/encerramento-etapa-2.md; aquisição fora da etapa 6",
        )
    return {
        "lotteries": len(CATALOG.entries),
        "rules": sum(len(e.lottery.rules) for e in CATALOG.entries),
    }


class PgCatalogAdministration:
    def __init__(self, db):
        self.db = db

    def bootstrap(self):
        return bootstrap_catalog(self.db)

    def inspect(self):
        result = self.db.execute("""SELECT current_setting('server_version_num')::integer AS server_version_num,
            (SELECT rolsuper FROM pg_roles WHERE rolname=current_user) AS superuser,
            coalesce((SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()),false) AS tls,
            to_regclass('lb.lottery') IS NOT NULL AS catalog_schema,
            to_regclass('lb.approved_dataset') IS NOT NULL AS datasets_schema""").fetchone()
        ledger = self.db.execute("SELECT to_regclass('public.alembic_version') AS name").fetchone()[
            "name"
        ]
        result["migration"] = None
        if (
            ledger
            and self.db.execute(
                "SELECT has_table_privilege('public.alembic_version','SELECT') AS allowed"
            ).fetchone()["allowed"]
        ):
            result["migration"] = self.db.execute(
                "SELECT version_num FROM public.alembic_version"
            ).fetchone()["version_num"]
        return dict(result)


class PgProfileCatalogRepository:
    def __init__(self, db):
        self.db = db

    def qualify(self, source_key, rule_label):
        profile = PROFILES.get(source_key)
        if profile is None:
            raise PersistenceError("unsupported_persistence_profile")
        entry = CATALOG.get(profile.lottery)
        expected_source = next(s for s in entry.sources if s.key == source_key)
        expected_rule = next(
            (r for r in entry.lottery.rules if r.version_label == rule_label), None
        )
        if expected_rule is None:
            raise PersistenceError("catalog_not_qualified")
        source = self.db.execute(
            """SELECT s.*,l.status AS lottery_status FROM lb.data_source s
            JOIN lb.lottery l ON l.id=s.lottery_id WHERE l.slug=%s AND s.key=%s""",
            (profile.lottery, source_key),
        ).fetchone()
        if (
            source is None
            or source["lottery_status"] != "active"
            or source["base_url"] != expected_source.url
            or source["authority"] != expected_source.authority.value
            or source["data_format"] != expected_source.data_format
            or source["readiness"] not in {"contract_observed", "approved"}
        ):
            raise PersistenceError("catalog_not_qualified")
        rule = self.db.execute(
            "SELECT * FROM lb.rule_version WHERE lottery_id=%s AND version_label=%s",
            (source["lottery_id"], rule_label),
        ).fetchone()
        if (
            rule is None
            or rule["status"] != "validated"
            or (rule["valid_from"], rule["valid_to"])
            != (expected_rule.valid_from, expected_rule.valid_to)
        ):
            raise PersistenceError("catalog_not_qualified")
        series = self.db.execute(
            "SELECT * FROM lb.series_definition WHERE rule_version_id=%s ORDER BY key",
            (rule["id"],),
        ).fetchall()
        if {s["key"] for s in series} != {s.key for s in expected_rule.series}:
            raise PersistenceError("catalog_not_qualified")
        for definition in expected_rule.series:
            row = next(s for s in series if s["key"] == definition.key)
            components = self.db.execute(
                "SELECT * FROM lb.component_definition WHERE series_definition_id=%s ORDER BY key",
                (row["id"],),
            ).fetchall()
            if (row["role"], row["required"]) != (definition.role.value, definition.required):
                raise PersistenceError("catalog_not_qualified")
            actual = [
                {k: c[k] for k in asdict(definition.components[0]) if k != "label"}
                for c in components
            ]
            expected = [
                {k: v for k, v in _plain(asdict(c)).items() if k != "label"}
                for c in sorted(definition.components, key=lambda c: c.key)
            ]
            if actual != expected:
                raise PersistenceError("catalog_not_qualified")
        tiers = self.db.execute(
            "SELECT id,key FROM lb.prize_tier_definition WHERE rule_version_id=%s ORDER BY key",
            (rule["id"],),
        ).fetchall()
        if not profile.tiers <= {t["key"] for t in tiers}:
            raise PersistenceError("catalog_not_qualified")
        scope = self.db.execute(
            "SELECT id FROM lb.lottery_scope WHERE lottery_id=%s AND key=%s",
            (source["lottery_id"], profile.scope),
        ).fetchone()
        if scope is None:
            raise PersistenceError("catalog_not_qualified")
        snapshot = {
            "schema_version": 1,
            "authority": source["authority"],
            "readiness": source["readiness"],
            "base_url": source["base_url"],
            "policy_reference": source["policy_reference"],
            "configuration_origin": "captured",
        }
        fingerprint = digest(
            {
                "rule": _plain(asdict(expected_rule)),
                "profile": source_key,
                "scope": profile.scope,
                "source": snapshot,
                "tiers": [t["key"] for t in tiers],
            }
        )
        primary = next(s for s in series if s["role"] == "primary")
        component = self.db.execute(
            "SELECT id FROM lb.component_definition WHERE series_definition_id=%s ORDER BY position LIMIT 1",
            (primary["id"],),
        ).fetchone()
        return CatalogBinding(
            source["lottery_id"],
            source["id"],
            scope["id"],
            rule["id"],
            primary["id"],
            component["id"],
            tuple((t["key"], t["id"]) for t in tiers),
            fingerprint,
            snapshot,
        )
