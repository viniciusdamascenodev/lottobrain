"""Fixtures SQL de teste, não um importador/repositório de produção."""
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from psycopg import sql
from psycopg.types.json import Jsonb

from app.application.collect_mega_sena import content_hash, semantic_payload
from app.catalog import CATALOG
from app.domain import RawProvenance
from app.ingestion import mega_sena, lotofacil, mais_milionaria, powerball, mega_millions, euro_millions

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 10, 21, tzinfo=timezone.utc)  # Relógio de teste, não instante histórico de captura.
CANON = "legacy-semantic-payload-v1"


def insert(db, table, **fields):
    db.execute(sql.SQL("INSERT INTO lb.{} ({}) VALUES ({})").format(
        sql.Identifier(table), sql.SQL(",").join(map(sql.Identifier, fields)),
        sql.SQL(",").join(sql.Placeholder() for _ in fields)), list(fields.values()))
    return fields.get("id")


def seed_catalog(db):
    ids = {}
    for entry in CATALOG.entries:
        game = entry.lottery
        lid = insert(db, "lottery", id=uuid4(), slug=game.slug, display_name=game.display_name,
                     origin_jurisdiction=game.jurisdiction_code, status=game.status.value,
                     default_timezone=game.default_timezone, default_currency=game.default_currency)
        scope = insert(db, "lottery_scope", id=uuid4(), lottery_id=lid,
                       key="provider_pt_or_es" if game.slug == "euro_millions" else "common_result",
                       kind="provider_context" if game.slug == "euro_millions" else "common_result", label="Escopo de teste")
        item = ids[game.slug] = dict(lottery=lid, scope=scope, rules={}, sources={})
        for rule in game.rules:
            rid = insert(db, "rule_version", id=uuid4(), lottery_id=lid, version_label=rule.version_label,
                         valid_from=rule.valid_from, valid_to=rule.valid_to, status=rule.status.value,
                         evidence_reference=rule.source_reference or "contrato existente", evidence_level="existing_contract")
            definitions = item["rules"][rule.version_label] = dict(id=rid, series={}, tiers={})
            for series in rule.series:
                sid = insert(db, "series_definition", id=uuid4(), rule_version_id=rid, key=series.key,
                             label=series.label, role=series.role.value, required=series.required)
                mapping = definitions["series"][series.key] = dict(id=sid, components={})
                for c in series.components:
                    mapping["components"][c.key] = insert(db, "component_definition", id=uuid4(), series_definition_id=sid,
                        key=c.key, value_type=c.value_type.value, min_count=c.min_count, max_count=c.max_count,
                        min_value=c.min_value, max_value=c.max_value, unique_values=c.unique_values,
                        order_semantics=c.order_semantics.value, position=c.position)
        for source in entry.sources:
            item["sources"][source.key] = insert(db, "data_source", id=uuid4(), lottery_id=lid, key=source.key,
                authority=source.authority.value, readiness=source.readiness.value, base_url=source.url,
                data_format=source.data_format, purposes=list(source.purposes))
    return ids


def real_fixture(slug, index=0):
    module = {m.__name__.split(".")[-1]: m for m in
              (mega_sena, lotofacil, mais_milionaria, powerball, mega_millions, euro_millions)}[slug]
    body = (ROOT / "tests/fixtures" / f"{slug}_rows.json").read_bytes()
    rows = json.loads(body, parse_float=Decimal)
    row = rows[index]
    if slug in ("powerball", "mega_millions"):
        cls = powerball.RawPowerballRow if slug == "powerball" else mega_millions.RawMegaMillionsRow
        row = cls(**{k: tuple(v) if isinstance(v, list) else v for k, v in row.items()})
    elif slug == "euro_millions":
        row = euro_millions.RawEuroMillionsRow(row["date"], row["draw_id"], row["has_winner"], row["id"],
                                             row["numbers"], row["prize"], row["stars"])
    provenance = RawProvenance(module.SOURCE_KEY, hashlib.sha256(body).hexdigest(), NOW, "fixture-test")
    result = module.normalize_row(row, provenance)
    assert result.is_valid, result.issues
    return result.candidate, body


class Graph:
    """Monta um agregado em construção usando conteúdo real. Sem commit implícito."""
    def __init__(self, db, catalog, slug="mega_sena", index=0, draw=None, revision_no=1):
        self.db = db
        candidate, body = real_fixture(slug, index)
        self.candidate = candidate
        self.catalog = cat = catalog[slug]
        self.lottery = cat["lottery"]
        self.scope = cat["scope"]
        self.rule = rule = cat["rules"][candidate.rule_version_label]
        self.source = cat["sources"][candidate.provenance.source_key]
        self.hash = content_hash(semantic_payload(candidate))
        existing = db.execute("SELECT id FROM lb.raw_artifact WHERE sha256=%s", (hashlib.sha256(body).hexdigest(),)).fetchone()
        self.raw = existing[0] if existing else insert(db, "raw_artifact", id=uuid4(), sha256=hashlib.sha256(body).hexdigest(), byte_count=len(body),
                          object_key=str(uuid4()), storage_state="available", registered_at=NOW)
        self.receipt = insert(db, "capture_receipt", id=uuid4(), lottery_id=self.lottery, source_id=self.source,
                         artifact_id=self.raw, capture_kind="legacy_import", captured_at=NOW,
                         effective_url=(ROOT / "tests/fixtures" / f"{slug}_rows.json").as_uri(),
                         content_type="application/json", byte_count=len(body), legacy_reference="test_fixture_not_original_wire")
        self.processing = insert(db, "processing_run", id=uuid4(), receipt_id=self.receipt, lottery_id=self.lottery,
            adapter_version="fixture-test", code_version="spec0024-test", canonicalization_version=CANON,
            validation_policy_version="existing-domain", catalog_fingerprint=content_hash({"slug":slug,"rules":[r.version_label for r in CATALOG.get(slug).lottery.rules]}),
            status="running", started_at=NOW)
        self.draw = draw or insert(db, "draw", id=uuid4(), lottery_id=self.lottery, created_at=NOW)
        self.revision = insert(db, "draw_revision", id=uuid4(), draw_id=self.draw, lottery_id=self.lottery,
            revision_no=revision_no, draw_date_local=candidate.draw_date, rule_version_id=rule["id"], content_hash=self.hash,
            canonicalization_version=CANON, seal_state="building", created_at=NOW)
        self.series = {}
        for series in candidate.series:
            definition = rule["series"][series.key]
            sid = insert(db, "result_series", id=uuid4(), revision_id=self.revision, rule_version_id=rule["id"],
                         lottery_id=self.lottery, series_definition_id=definition["id"])
            self.series[series.key] = sid
            for component in series.components:
                for ordinal, value in enumerate(component.values, 1):
                    insert(db, "component_value", result_series_id=sid, revision_id=self.revision,
                        series_definition_id=definition["id"], component_definition_id=definition["components"][component.key],
                        ordinal=ordinal, integer_value=value if type(value) is int else None,
                        text_value=value if type(value) is str else None)
            for attr in series.attributes:
                value_type = "boolean" if type(attr.value) is bool else "integer" if type(attr.value) is int else "text" if type(attr.value) is str else "decimal"
                insert(db, "result_attribute", result_series_id=sid, revision_id=self.revision, key=attr.key,
                       value_type=value_type, **{f"{value_type}_value": attr.value})
        # Não inserir definição de faixa após revisão já referenciada: seed_tiers roda antes.
        for tier in candidate.prize_tiers:
            tid = insert(db, "prize_tier_result", id=uuid4(), revision_id=self.revision, rule_version_id=rule["id"],
                lottery_id=self.lottery, tier_definition_id=rule["tiers"][tier.tier_key], scope_id=self.scope,
                winners_status=tier.status.value, winners=tier.winners)
            if tier.prize_per_winner:
                self.money(tier.prize_per_winner, tier_result_id=tid)
        for amount in candidate.monetary_amounts:
            self.money(amount)

    def money(self, fact=None, **overrides):
        values = dict(id=uuid4(), revision_id=self.revision, lottery_id=self.lottery, rule_version_id=self.rule["id"],
                      scope_id=self.scope, kind="test_measure", payout_form="unspecified", status="unknown")
        if fact:
            values.update(kind=fact.kind,status=fact.status.value,amount=fact.amount,currency=fact.currency,source_text=fact.source_text)
        values.update(overrides)
        return insert(self.db, "monetary_fact", **values)

    def support(self):
        self.observation = insert(self.db, "candidate_observation", id=uuid4(), processing_run_id=self.processing,
            row_locator=str(uuid4()), lottery_id=self.lottery, draw_id=self.draw, revision_id=self.revision,
            decision="new", semantic_hash=self.hash, completed_at=NOW)
        return self.observation

    def alias(self):
        self.identity = insert(self.db, "draw_identity", id=uuid4(), lottery_id=self.lottery, draw_id=self.draw,
            namespace="official_draw_number" if self.candidate.official_draw_number else "drawing_date",
            value=self.candidate.official_draw_number or self.candidate.draw_date.isoformat(),
            assurance="official" if self.candidate.official_draw_number else "provisional", active=True,
            evidence_observation_id=self.observation)

    def seal(self):
        self.db.execute("UPDATE lb.draw_revision SET seal_state='sealed',sealed_at=%s WHERE id=%s", (NOW,self.revision))


def seed_tiers(db, catalog):
    for slug in ("mega_sena","lotofacil","mais_milionaria"):
        candidate, _ = real_fixture(slug)
        rule = catalog[slug]["rules"][candidate.rule_version_label]
        for pos, tier in enumerate(candidate.prize_tiers):
            rule["tiers"][tier.tier_key] = insert(db,"prize_tier_definition",id=uuid4(),rule_version_id=rule["id"],
                key=tier.tier_key,label=tier.tier_key,criterion_key=tier.tier_key,
                criterion_description="Chave do contrato de normalização existente",position=pos)
