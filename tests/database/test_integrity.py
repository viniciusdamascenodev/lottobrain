"""Integração obrigatória explícita: executar pelo cluster isolado, nunca SQLite."""
from contextlib import contextmanager
from datetime import date
import os
from pathlib import Path
import unittest
from uuid import uuid4

from alembic import command
from alembic.config import Config
import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from support import CANON, Graph, NOW, ROOT, insert, seed_catalog, seed_tiers


def migration_config(url):
    config = Config(str(ROOT / "alembic.ini"))
    engine = create_engine(url, hide_parameters=True)
    return config, engine


def migrate(url, target="head", down=False):
    config, engine = migration_config(url)
    try:
        with engine.connect() as connection:
            config.attributes["connection"] = connection
            (command.downgrade if down else command.upgrade)(config, target)
    finally:
        engine.dispose()


class PostgreSQLIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.url = os.environ.get("LOTTOBRAIN_DATABASE_URL")
        expected_dir = os.environ.get("LOTTOBRAIN_TEST_ISOLATED")
        if not cls.url or not expected_dir or not os.environ.get("LOTTOBRAIN_TEST_ADMIN_DSN"):
            raise RuntimeError("Use scripts/database/run_integration.py; integração não pode ser aprovada por skip.")
        parsed = make_url(cls.url)
        cls.kwargs = dict(host=parsed.host,port=parsed.port,user=parsed.username,password=parsed.password,dbname=parsed.database)
        with psycopg.connect(os.environ["LOTTOBRAIN_TEST_ADMIN_DSN"], autocommit=True) as admin:
            actual = Path(admin.execute("SHOW data_directory").fetchone()[0]).resolve()
            safe_root = (ROOT / ".local-postgres/runs").resolve()
            if actual != Path(expected_dir).resolve() or not actual.is_relative_to(safe_root):
                raise RuntimeError("Testes recusados fora do cluster dedicado.")
        migrate(cls.url)
        migrate(cls.url)  # Reaplicação controlada: não recria schema/tabelas.
        with psycopg.connect(os.environ["LOTTOBRAIN_TEST_ADMIN_DSN"], autocommit=True) as admin:
            admin.execute((ROOT / "scripts/database/roles.sql").read_text(encoding="utf-8"))
            admin.execute("GRANT lottobrain_ingest,lottobrain_audit TO lb_migrator")
        with psycopg.connect(**cls.kwargs) as db:
            cls.catalog = seed_catalog(db)
            seed_tiers(db, cls.catalog)

    def setUp(self):
        self.db = psycopg.connect(**self.kwargs)

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def flush(self):
        self.db.execute("SET CONSTRAINTS ALL IMMEDIATE")
        self.db.execute("SET CONSTRAINTS ALL DEFERRED")

    @contextmanager
    def rejected(self, *states):
        with self.assertRaises(psycopg.Error) as raised:
            with self.db.transaction():
                yield
                self.flush()
        self.assertIn(raised.exception.sqlstate, states or ("23514",))

    def graph(self, **kwargs):
        g = Graph(self.db,self.catalog,**kwargs)
        g.support()
        return g

    def checkpoint(self, g):
        baseline = insert(self.db,"ingestion_baseline",id=uuid4(),lottery_id=g.lottery,source_id=g.source,
            artifact_id=g.raw,first_sequence=1,last_sequence=2953,manifest_hash=g.hash,
            audit_reference="TEST_ONLY: fronteira para provar transição com fixture real 2954; não é baseline operacional",audited_at=NOW,
            materialization_status="referenced")
        cp = insert(self.db,"sync_checkpoint",id=uuid4(),lottery_id=g.lottery,source_id=g.source,stream_key="test_sequence",
            strategy="official_numeric_sequence",baseline_id=baseline,cursor_sequence=2953,review_next=2954)
        self.db.execute("UPDATE lb.sync_checkpoint SET lease_token=1,lease_until=clock_timestamp()+interval '5 minutes',row_version=1 WHERE id=%s",(cp,))
        return cp

    def step(self, cp, g, token=1, sequence=2954):
        insert(self.db,"sync_step",checkpoint_id=cp,sequence_no=sequence,observation_id=g.observation,lease_token=token,completed_at=NOW)

    def test_01_migrations_version_and_non_superuser_owner(self):
        self.assertEqual("0033_01",self.db.execute("SELECT version_num FROM alembic_version").fetchone()[0])
        self.assertEqual(6,self.db.execute("SELECT count(*) FROM lb.lottery").fetchone()[0])
        self.assertEqual(20,self.db.execute("SELECT count(*) FROM lb.rule_version").fetchone()[0])
        self.assertEqual((False,False,False),self.db.execute("SELECT rolsuper,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user").fetchone())
        self.assertEqual("17.11",self.db.execute("SHOW server_version").fetchone()[0].split()[0])

    def test_02_six_real_lotteries_have_complete_sealed_results(self):
        for slug in self.catalog:
            with self.subTest(slug=slug):
                g = self.graph(slug=slug)
                g.alias()
                g.seal()
                self.flush()
                self.assertIsNone(self.db.execute("SELECT published_revision_id FROM lb.draw WHERE id=%s",(g.draw,)).fetchone()[0])
        self.assertEqual(6,self.db.execute("SELECT count(*) FROM lb.draw_revision").fetchone()[0])

    def test_03_slug_alias_and_provider_scope_uniqueness(self):
        with self.rejected("23505"):
            insert(self.db,"lottery",id=uuid4(),slug="mega_sena",display_name="Duplicata de teste",origin_jurisdiction="BR",status="draft")
        g = self.graph(); g.alias(); g.seal()
        with self.rejected("23505"):
            insert(self.db,"draw_identity",id=uuid4(),lottery_id=g.lottery,draw_id=g.draw,namespace="official_draw_number",
                value=g.candidate.official_draw_number,assurance="official",active=False,evidence_observation_id=g.observation)
        sources = list(self.catalog["mega_sena"]["sources"].values())
        for source in sources[:2]:
            insert(self.db,"external_draw_reference",id=uuid4(),lottery_id=g.lottery,source_id=source,draw_id=g.draw,
                namespace="provider_id",value="same-private-id-test",evidence_observation_id=g.observation)
        with self.rejected("23505"):
            insert(self.db,"external_draw_reference",id=uuid4(),lottery_id=g.lottery,source_id=sources[0],draw_id=g.draw,
                namespace="provider_id",value="same-private-id-test",evidence_observation_id=g.observation)
        self.flush()

    def test_04_rules_overlap_adjacency_and_gap(self):
        cat = self.catalog["mega_sena"]
        with self.rejected("23P01"):
            insert(self.db,"rule_version",id=uuid4(),lottery_id=cat["lottery"],version_label="test_overlap",
                valid_from=date(2025,1,1),status="validated",evidence_reference="test",evidence_level="test")
        # Regras reais históricas Powerball/MM/EM, com fronteiras adjacentes, já confirmaram no seed.
        self.assertEqual(7,self.db.execute("SELECT count(*) FROM lb.rule_version WHERE lottery_id=%s",(self.catalog["powerball"]["lottery"],)).fetchone()[0])
        # Remoção exclusivamente de teste abre uma lacuna entre versões reais:
        # não se deve preencher nem proibir períodos historicamente desconhecidos.
        gap_rule = self.db.execute("SELECT id FROM lb.rule_version WHERE lottery_id=%s ORDER BY valid_from OFFSET 2 LIMIT 1",
                                  (self.catalog["powerball"]["lottery"],)).fetchone()[0]
        self.db.execute("DELETE FROM lb.component_definition WHERE series_definition_id IN (SELECT id FROM lb.series_definition WHERE rule_version_id=%s)",(gap_rule,))
        self.db.execute("DELETE FROM lb.series_definition WHERE rule_version_id=%s",(gap_rule,))
        self.db.execute("DELETE FROM lb.rule_version WHERE id=%s",(gap_rule,))
        self.flush()

    def test_05_primary_and_components_required(self):
        rid = self.catalog["mega_sena"]["rules"]["baseline_1996"]["id"]
        for mode in ("none","two","empty_component"):
            with self.subTest(mode=mode), self.rejected():
                if mode == "none":
                    self.db.execute("UPDATE lb.series_definition SET role='additional' WHERE rule_version_id=%s",(rid,))
                elif mode == "two":
                    sid = insert(self.db,"series_definition",id=uuid4(),rule_version_id=rid,key="test_primary",label="Teste",role="primary",required=True)
                    insert(self.db,"component_definition",id=uuid4(),series_definition_id=sid,key="test",value_type="text",min_count=0,max_count=1,unique_values=True,order_semantics="none",position=0)
                else:
                    self.db.execute("DELETE FROM lb.component_definition WHERE series_definition_id IN (SELECT id FROM lb.series_definition WHERE rule_version_id=%s)",(rid,))

    def test_06_referenced_catalog_and_rule_date_guard(self):
        g = self.graph(index=2); g.seal(); self.flush()
        with self.rejected():
            self.db.execute("UPDATE lb.rule_version SET valid_to='2025-12-20' WHERE id=%s",(g.rule["id"],))
        self.db.execute("UPDATE lb.rule_version SET valid_to='2025-12-21' WHERE id=%s",(g.rule["id"],))
        self.flush()
        with self.rejected():
            self.db.execute("UPDATE lb.component_definition SET max_value=99 WHERE id=%s",(g.rule["series"]["primary"]["components"]["main"],))

    def test_07_cross_rule_and_scope_links(self):
        g = self.graph()
        other = self.catalog["lotofacil"]
        with self.rejected("23503"):
            self.db.execute("UPDATE lb.draw_revision SET draw_date_local='2000-01-01' WHERE id=%s",(g.revision,))
            # FK identifica outra loteria, independentemente de datas.
            insert(self.db,"result_series",id=uuid4(),revision_id=g.revision,rule_version_id=other["rules"]["baseline_2003"]["id"],
                lottery_id=other["lottery"],series_definition_id=other["rules"]["baseline_2003"]["series"]["primary"]["id"])
        with self.rejected("23503"):
            g.money(scope_id=other["scope"])
        g.seal(); self.flush()

    def test_08_bad_cardinality_bounds_duplicates_order_and_type(self):
        mutations = [
            "DELETE FROM lb.component_value WHERE ordinal=6 AND revision_id=%s",
            "UPDATE lb.component_value SET integer_value=61 WHERE ordinal=6 AND revision_id=%s",
            "UPDATE lb.component_value SET integer_value=4 WHERE ordinal=2 AND revision_id=%s",
            "UPDATE lb.component_value SET ordinal=7 WHERE ordinal=6 AND revision_id=%s",
            "UPDATE lb.component_value SET integer_value=1 WHERE ordinal=6 AND revision_id=%s",
            "UPDATE lb.component_value SET integer_value=NULL,text_value='4' WHERE ordinal=1 AND revision_id=%s",
            "UPDATE lb.component_value SET extraction_ordinal=1 WHERE ordinal=1 AND revision_id=%s",
        ]
        for statement in mutations:
            with self.subTest(statement=statement), self.rejected():
                g = self.graph(); self.db.execute(statement,(g.revision,)); g.seal()

    def test_09_building_or_missing_support_or_wrong_date_rejected(self):
        with self.rejected():
            g = self.graph()  # Sem selo.
        with self.rejected():
            g = Graph(self.db,self.catalog); g.seal()  # Sem observação.
        with self.rejected():
            g = self.graph()
            self.db.execute("UPDATE lb.draw_revision SET draw_date_local='1996-03-10' WHERE id=%s",(g.revision,))
            g.seal()

    def test_10_immutable_revision_and_every_content_child(self):
        g = self.graph(); g.seal(); self.flush()
        cases = [
            ("UPDATE lb.draw_revision SET content_hash=content_hash WHERE id=%s",(g.revision,)),
            ("UPDATE lb.component_value SET integer_value=5 WHERE revision_id=%s AND ordinal=1",(g.revision,)),
            ("DELETE FROM lb.component_value WHERE revision_id=%s",(g.revision,)),
            ("INSERT INTO lb.result_attribute VALUES (%s,%s,'late','boolean',NULL,NULL,NULL,true)",(g.series["primary"],g.revision)),
        ]
        for statement,params in cases:
            with self.subTest(statement=statement),self.rejected():
                self.db.execute(statement,params)
        with self.rejected():
            g.money(kind="late_payment")
        g.support()  # Nova evidência permitida, sem editar conteúdo.
        self.flush()

    def test_11_money_zero_unknown_and_typed_winners(self):
        g = self.graph()
        g.money(kind="known_zero_test",status="known",amount="0",currency="BRL")
        g.money(kind="missing_test")
        with self.rejected(): g.money(kind="bad_unknown",amount="0")
        with self.rejected(): self.db.execute("UPDATE lb.prize_tier_result SET winners_status='unknown' WHERE revision_id=%s",(g.revision,))
        g.seal(); self.flush()
        self.assertEqual(("known",0,"BRL"),self.db.execute("SELECT status,amount,currency FROM lb.monetary_fact WHERE kind='known_zero_test'").fetchone())

    def test_12_money_special_values_scale_and_envelope(self):
        g = self.graph()
        for value in ("NaN","Infinity","-Infinity","-1","1000000000000000001","0.1234567"):
            with self.subTest(value=value),self.rejected():
                g.money(kind="invalid_test",status="known",amount=value,currency="BRL")
        g.money(kind="valid_scale_test",status="known",amount="0.123456",currency="BRL")
        g.seal(); self.flush()

    def test_13_money_null_uniqueness_scope_and_payout(self):
        g = self.graph(); g.money(kind="missing_test")
        with self.rejected("23505"): g.money(kind="missing_test")
        for form in ("cash","annuity"):
            g.money(kind="payout_test",status="known",amount="0",currency="BRL",payout_form=form)
        other = insert(self.db,"lottery_scope",id=uuid4(),lottery_id=g.lottery,key="test_other_scope",kind="provider_context",label="Teste")
        g.money(kind="missing_test",scope_id=other)
        g.seal(); self.flush()

    def test_14_blob_dedup_keeps_two_captures_and_recipes(self):
        a = self.graph(); a.seal()
        b = self.graph(index=1); b.seal()
        self.assertEqual(a.raw,b.raw)
        self.assertNotEqual(a.receipt,b.receipt)
        self.assertNotEqual(a.processing,b.processing)
        self.flush()

    def test_15_evidence_and_alias_cannot_be_erased_or_rewritten(self):
        g = self.graph(); g.alias(); g.seal(); self.flush()
        for table,key,value in (("raw_artifact","id",g.raw),("capture_receipt","id",g.receipt),
            ("candidate_observation","id",g.observation),("draw_revision","id",g.revision),("draw_identity","id",g.identity)):
            with self.subTest(table=table),self.rejected("23514","23503"):
                self.db.execute(sql.SQL("DELETE FROM lb.{} WHERE {}=%s").format(sql.Identifier(table),sql.Identifier(key)),(value,))
        with self.rejected(): self.db.execute("UPDATE lb.processing_run SET code_version='rewritten' WHERE id=%s",(g.processing,))
        self.db.execute("UPDATE lb.draw_identity SET active=false WHERE id=%s",(g.identity,))
        with self.rejected("23505"): g.alias()

    def test_16_checkpoint_cannot_jump_or_advance_without_step(self):
        g = self.graph(index=2); g.alias(); g.seal(); cp = self.checkpoint(g); self.flush()
        for cursor in (2954,3071):
            with self.subTest(cursor=cursor),self.rejected():
                self.db.execute("UPDATE lb.sync_checkpoint SET cursor_sequence=%s,row_version=row_version+1 WHERE id=%s",(cursor,cp))
        self.assertEqual(2953,self.db.execute("SELECT cursor_sequence FROM lb.sync_checkpoint WHERE id=%s",(cp,)).fetchone()[0])

    def test_17_checkpoint_step_atomicity_and_baseline_not_loaded(self):
        g = self.graph(index=2); g.alias(); g.seal(); cp = self.checkpoint(g); self.flush()
        with self.rejected(): self.step(cp,g)  # Sem avanço correspondente.
        self.assertEqual(0,self.db.execute("SELECT count(*) FROM lb.sync_step").fetchone()[0])
        self.step(cp,g)
        self.db.execute("UPDATE lb.sync_checkpoint SET cursor_sequence=2954,row_version=row_version+1 WHERE id=%s",(cp,))
        self.flush()
        self.assertEqual("referenced",self.db.execute("SELECT materialization_status FROM lb.ingestion_baseline").fetchone()[0])

    def test_18_fencing_rejects_old_token_and_wrong_identity(self):
        g = self.graph(index=2); g.alias(); g.seal(); cp = self.checkpoint(g)
        self.db.execute("UPDATE lb.sync_checkpoint SET lease_token=2,lease_until=clock_timestamp()+interval '5 minutes',row_version=row_version+1 WHERE id=%s",(cp,))
        with self.rejected(): self.step(cp,g,token=1)
        with self.rejected(): self.step(cp,g,token=2,sequence=2955)
        with self.rejected():
            self.db.execute("UPDATE lb.sync_checkpoint SET lease_until=clock_timestamp()-interval '1 second',row_version=row_version+1 WHERE id=%s",(cp,))
            self.step(cp,g,token=2)
        self.flush()

    def test_19_ingest_role_can_write_aggregate_but_not_catalog_ddl_publish_or_delete(self):
        self.db.execute("SET LOCAL ROLE lottobrain_ingest")
        g = self.graph(); g.alias(); g.seal(); self.flush()
        for statement,params in (("DELETE FROM lb.raw_artifact WHERE id=%s",(g.raw,)),
            ("UPDATE lb.draw SET published_revision_id=%s WHERE id=%s",(g.revision,g.draw)),
            ("UPDATE lb.rule_version SET valid_to='2026-12-01' WHERE id=%s",(g.rule["id"],)),
            ("CREATE TABLE lb.not_allowed(id int)",())):
            with self.subTest(statement=statement),self.rejected("42501"):
                self.db.execute(statement,params)

    def test_20_audit_role_is_read_only(self):
        self.db.execute("SET LOCAL ROLE lottobrain_audit")
        self.assertEqual(6,self.db.execute("SELECT count(*) FROM lb.lottery").fetchone()[0])
        with self.rejected("42501"):
            insert(self.db,"lottery",id=uuid4(),slug="test_forbidden",display_name="Teste",origin_jurisdiction="BR",status="draft")

    def test_21_empty_database_upgrade_downgrade_and_reupgrade(self):
        name = "lottobrain_test_migrations_" + uuid4().hex
        with psycopg.connect(os.environ["LOTTOBRAIN_TEST_ADMIN_DSN"],autocommit=True) as admin:
            admin.execute(sql.SQL("CREATE DATABASE {} OWNER lb_migrator").format(sql.Identifier(name)))
        url = make_url(self.url).set(database=name).render_as_string(hide_password=False)
        migrate(url); migrate(url,"base",down=True); migrate(url)
        # Banco dedicado fica no cluster descartável, desligado pelo runner; não apagar dados de usuário.

    def test_22_actual_commit_rejects_partial_revision_and_rolls_back(self):
        g = self.graph()
        with self.assertRaises(psycopg.errors.CheckViolation):
            self.db.commit()
        self.db.rollback()
        self.assertEqual(0,self.db.execute("SELECT count(*) FROM lb.draw_revision WHERE id=%s",(g.revision,)).fetchone()[0])
        self.assertEqual(0,self.db.execute("SELECT count(*) FROM lb.capture_receipt WHERE id=%s",(g.receipt,)).fetchone()[0])

    def test_23_component_tier_and_pointer_foreign_context(self):
        g = self.graph()
        other = self.catalog["lotofacil"]["rules"]["baseline_2003"]
        with self.rejected("23503"):
            self.db.execute("UPDATE lb.component_value SET component_definition_id=%s WHERE revision_id=%s",
                (other["series"]["primary"]["components"]["main"],g.revision))
        with self.rejected("23503"):
            self.db.execute("UPDATE lb.prize_tier_result SET tier_definition_id=%s WHERE id=(SELECT id FROM lb.prize_tier_result WHERE revision_id=%s LIMIT 1)",
                (next(iter(other["tiers"].values())),g.revision))
        second = self.graph(index=1)
        g.seal(); second.seal(); self.flush()
        with self.rejected("23503"):
            self.db.execute("UPDATE lb.draw SET latest_candidate_revision_id=%s WHERE id=%s",(second.revision,g.draw))
        self.flush()

    def test_24_bodyless_transport_failure_and_404_receipt(self):
        cat = self.catalog["mega_sena"]; source = cat["sources"]["caixa_mega_sena_json"]
        from hashlib import sha256
        run = insert(self.db,"ingestion_run",id=uuid4(),lottery_id=cat["lottery"],source_id=source,
            idempotency_key=str(uuid4()),request_hash=sha256(b"explicit-test-request").hexdigest(),
            source_config_snapshot=Jsonb({"schema_version":1,"configuration_origin":"test"}),mode="test",status="running",started_at=NOW,correlation_id=uuid4())
        insert(self.db,"fetch_attempt",id=uuid4(),run_id=run,source_id=source,lottery_id=cat["lottery"],ordinal=1,
            url="https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena",started_at=NOW,finished_at=NOW,
            outcome="transport_error",error_code="TEST_TIMEOUT")
        self.assertEqual(0,self.db.execute("SELECT count(*) FROM lb.raw_artifact").fetchone()[0])
        attempt = insert(self.db,"fetch_attempt",id=uuid4(),run_id=run,source_id=source,lottery_id=cat["lottery"],ordinal=2,
            url="https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena",started_at=NOW,finished_at=NOW,outcome="response",http_status=404)
        # Evidência real disponível, usada apenas para demonstrar metadados SQL de um HTTP 404 simulado.
        # Nenhuma requisição 404 nem novo conteúdo operacional é fabricado por este teste.
        g = self.graph(); g.seal()
        byte_count = self.db.execute("SELECT byte_count FROM lb.raw_artifact WHERE id=%s",(g.raw,)).fetchone()[0]
        receipt = insert(self.db,"capture_receipt",id=uuid4(),lottery_id=cat["lottery"],source_id=source,fetch_attempt_id=attempt,
            artifact_id=g.raw,capture_kind="http",captured_at=NOW,effective_url="https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena",
            http_status=404,content_type="application/json",byte_count=byte_count)
        self.assertIsNotNone(receipt)
        with self.rejected(): self.db.execute("UPDATE lb.fetch_attempt SET http_status=200 WHERE id=%s",(attempt,))
        self.flush()

    def test_25_late_child_insert_and_valid_extraction_order(self):
        g = self.graph()
        self.db.execute("UPDATE lb.component_value SET extraction_ordinal=7-ordinal WHERE revision_id=%s",(g.revision,))
        g.seal(); self.flush()
        for table in ("component_value","result_series","prize_tier_result"):
            with self.subTest(table=table),self.rejected():
                # Clona uma linha real: o guard deve rejeitar antes mesmo de UNIQUE.
                self.db.execute(sql.SQL("INSERT INTO lb.{} SELECT * FROM lb.{} WHERE revision_id=%s LIMIT 1").format(sql.Identifier(table),sql.Identifier(table)),(g.revision,))

    def test_26_old_observation_hash_and_publication_gate(self):
        g = self.graph(); g.seal(); self.flush()
        with self.rejected():
            insert(self.db,"candidate_observation",id=uuid4(),processing_run_id=g.processing,row_locator="test-mismatch",
                lottery_id=g.lottery,draw_id=g.draw,revision_id=g.revision,decision="unchanged",
                semantic_hash="0" * 64,completed_at=NOW)
        with self.rejected():
            self.db.execute("UPDATE lb.draw SET published_revision_id=%s WHERE id=%s",(g.revision,g.draw))

    def test_27_missing_required_series_rejected(self):
        with self.rejected():
            g = self.graph()
            self.db.execute("DELETE FROM lb.component_value WHERE revision_id=%s",(g.revision,))
            self.db.execute("DELETE FROM lb.result_attribute WHERE revision_id=%s",(g.revision,))
            self.db.execute("DELETE FROM lb.result_series WHERE revision_id=%s",(g.revision,))
            g.seal()

    def test_28_recipe_row_locator_and_command_uniqueness(self):
        g = self.graph(); g.seal(); self.flush()
        with self.rejected("23505"):
            self.db.execute("INSERT INTO lb.processing_run SELECT %s,receipt_id,lottery_id,adapter_version,code_version,canonicalization_version,validation_policy_version,catalog_fingerprint,status,started_at,finished_at FROM lb.processing_run WHERE id=%s",(uuid4(),g.processing))
        with self.rejected("23505"):
            self.db.execute("INSERT INTO lb.candidate_observation SELECT %s,processing_run_id,row_locator,lottery_id,draw_id,revision_id,decision,semantic_hash,diagnostic_payload,completed_at FROM lb.candidate_observation WHERE id=%s",(uuid4(),g.observation))
        command_key = str(uuid4())
        insert(self.db,"processing_attempt",id=uuid4(),processing_run_id=g.processing,ordinal=1,
            command_key=command_key,request_hash=g.hash,outcome="test",started_at=NOW)
        with self.rejected("23505"):
            insert(self.db,"processing_attempt",id=uuid4(),processing_run_id=g.processing,ordinal=2,
                command_key=command_key,request_hash=g.hash,outcome="test",started_at=NOW)

    def test_29_duplicate_content_hash_allowed_in_distinct_revisions(self):
        first = self.graph(); first.seal(); self.flush()
        second = self.graph(draw=first.draw,revision_no=2); second.seal(); self.flush()
        self.assertEqual(first.hash,second.hash)
        self.assertEqual(2,self.db.execute("SELECT count(*) FROM lb.draw_revision WHERE draw_id=%s",(first.draw,)).fetchone()[0])
        # Só prova ausência de UNIQUE indevido. Reconciliação A→B→A será testada com repositórios.

    def test_30_populated_downgrade_is_refused_without_erasing_evidence(self):
        from sqlalchemy.exc import DBAPIError
        name = "lottobrain_test_retention_" + uuid4().hex
        with psycopg.connect(os.environ["LOTTOBRAIN_TEST_ADMIN_DSN"],autocommit=True) as admin:
            admin.execute(sql.SQL("CREATE DATABASE {} OWNER lb_migrator").format(sql.Identifier(name)))
        url = make_url(self.url).set(database=name).render_as_string(hide_password=False)
        migrate(url)
        kwargs = dict(self.kwargs,dbname=name)
        with psycopg.connect(**kwargs) as db:
            catalog = seed_catalog(db); seed_tiers(db,catalog)
            graph = Graph(db,catalog); graph.support(); graph.seal()
        with self.assertRaises(DBAPIError) as error:
            migrate(url,"0024_01",down=True)
        self.assertIn("Rollback bloqueado",str(error.exception.orig))
        with psycopg.connect(**kwargs) as db:
            self.assertEqual(1,db.execute("SELECT count(*) FROM lb.draw_revision").fetchone()[0])
            self.assertEqual(1,db.execute("SELECT count(*) FROM lb.capture_receipt").fetchone()[0])
            self.assertEqual("0033_01",db.execute("SELECT version_num FROM alembic_version").fetchone()[0])
            self.assertIsNotNone(db.execute("SELECT to_regclass('lb.sync_checkpoint')").fetchone()[0])
        migrate(url)

    def test_31_cooldown_commit_survives_rejected_cursor_transaction(self):
        name = "lottobrain_test_cooldown_" + uuid4().hex
        with psycopg.connect(os.environ["LOTTOBRAIN_TEST_ADMIN_DSN"],autocommit=True) as admin:
            admin.execute(sql.SQL("CREATE DATABASE {} OWNER lb_migrator").format(sql.Identifier(name)))
        url = make_url(self.url).set(database=name).render_as_string(hide_password=False)
        migrate(url)
        kwargs = dict(self.kwargs,dbname=name)
        with psycopg.connect(**kwargs) as db:
            catalog = seed_catalog(db); seed_tiers(db,catalog)
            graph = Graph(db,catalog,index=2); graph.support(); graph.alias(); graph.seal()
            baseline = insert(db,"ingestion_baseline",id=uuid4(),lottery_id=graph.lottery,source_id=graph.source,
                artifact_id=graph.raw,first_sequence=1,last_sequence=2953,manifest_hash=graph.hash,
                audit_reference="TEST_ONLY: fronteira para fixture 2954, não baseline operacional",audited_at=NOW,
                materialization_status="referenced")
            cp = insert(db,"sync_checkpoint",id=uuid4(),lottery_id=graph.lottery,source_id=graph.source,
                stream_key="test_cooldown",strategy="official_numeric_sequence",baseline_id=baseline,cursor_sequence=2953,review_next=2954)
            db.execute("UPDATE lb.sync_checkpoint SET lease_token=1,lease_until=clock_timestamp()+interval '5 minutes',row_version=1 WHERE id=%s",(cp,))
        with psycopg.connect(**kwargs) as db:
            db.execute("UPDATE lb.sync_checkpoint SET cooldown_until=clock_timestamp()+interval '15 minutes',row_version=row_version+1 WHERE id=%s",(cp,))
        failing = psycopg.connect(**kwargs)
        try:
            with self.assertRaises(psycopg.errors.CheckViolation):
                failing.execute("UPDATE lb.sync_checkpoint SET cursor_sequence=2954,row_version=row_version+1 WHERE id=%s",(cp,))
                failing.commit()
        finally:
            # Na versão qualificada, __exit__ não chega ao close se commit falhar.
            # O futuro UnitOfWork também deverá garantir close em finally.
            failing.close()
        with psycopg.connect(**kwargs) as db:
            self.assertEqual((2953,True),db.execute("SELECT cursor_sequence,cooldown_until IS NOT NULL FROM lb.sync_checkpoint WHERE id=%s",(cp,)).fetchone())


if __name__ == "__main__":
    unittest.main()
