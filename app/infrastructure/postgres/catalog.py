"""Qualifica o catálogo SQL contra o contrato que o normalizador realmente suporta."""
from dataclasses import asdict

from app.application.mega_sena_content import digest
from app.application.persistence import CatalogBinding, PersistenceError
from app.ingestion.mega_sena import MEGA_SENA
from app.ingestion.mega_sena_api import SOURCE_KEY

ENDPOINT = "https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena"


class PgCatalogRepository:
    def __init__(self, db):
        self.db = db

    def qualify(self, source_key=SOURCE_KEY) -> CatalogBinding:
        profiles = {
            SOURCE_KEY: ("json", ENDPOINT),
            "caixa_mega_sena_xlsx": ("xlsx", "https://servicebus3.caixa.gov.br/portaldeloterias/api/resultados/download?modalidade=Mega-Sena"),
        }
        if source_key not in profiles:
            raise PersistenceError("catalog_not_qualified")
        data_format, endpoint = profiles[source_key]
        source = self.db.execute("""SELECT l.id AS lottery_id,s.id AS source_id,s.authority,s.readiness,s.base_url,s.policy_reference
            FROM lb.lottery l JOIN lb.data_source s ON s.lottery_id=l.id
            WHERE l.slug='mega_sena' AND l.status='active' AND s.key=%s AND s.data_format=%s""", (source_key,data_format)).fetchone()
        if not source or source["authority"] != "official" or source["readiness"] not in ("contract_observed", "approved") or source["base_url"] != endpoint:
            raise PersistenceError("catalog_not_qualified")
        rule = self.db.execute("""SELECT id,version_label,valid_from,valid_to,status FROM lb.rule_version
            WHERE lottery_id=%s AND version_label=%s""", (source["lottery_id"], MEGA_SENA.rules[0].version_label)).fetchone()
        expected = MEGA_SENA.rules[0]
        if not rule or (rule["valid_from"],rule["valid_to"],rule["status"]) != (expected.valid_from,expected.valid_to,"validated"):
            raise PersistenceError("catalog_not_qualified")
        series = self.db.execute("SELECT id,key,role,required FROM lb.series_definition WHERE rule_version_id=%s ORDER BY key", (rule["id"],)).fetchall()
        if len(series) != 1 or (series[0]["key"],series[0]["role"],series[0]["required"]) != ("primary","primary",True):
            raise PersistenceError("catalog_not_qualified")
        components = self.db.execute("""SELECT id,key,value_type,min_count,max_count,min_value,max_value,unique_values,order_semantics,position
            FROM lb.component_definition WHERE series_definition_id=%s ORDER BY position""", (series[0]["id"],)).fetchall()
        expected_component = asdict(expected.series[0].components[0])
        expected_component.pop("label")
        expected_component["value_type"] = expected_component["value_type"].value
        expected_component["order_semantics"] = expected_component["order_semantics"].value
        if len(components) != 1 or {k:v for k,v in components[0].items() if k != "id"} != expected_component:
            raise PersistenceError("catalog_not_qualified")
        tiers = self.db.execute("SELECT id,key,criterion_key FROM lb.prize_tier_definition WHERE rule_version_id=%s ORDER BY key", (rule["id"],)).fetchall()
        if {(t["key"],t["criterion_key"]) for t in tiers} != {(k,k) for k in ("sena","quina","quadra")}:
            raise PersistenceError("catalog_not_qualified")
        scope = self.db.execute("SELECT id,kind FROM lb.lottery_scope WHERE lottery_id=%s AND key='common_result'", (source["lottery_id"],)).fetchone()
        if not scope or scope["kind"] != "common_result":
            raise PersistenceError("catalog_not_qualified")
        snapshot = {"schema_version":1,"authority":source["authority"],"readiness":source["readiness"],
                    "base_url":source["base_url"],"policy_reference":source["policy_reference"],"configuration_origin":"captured"}
        fingerprint = digest({"rule":rule["version_label"],"valid_from":rule["valid_from"].isoformat(),
            "valid_to":rule["valid_to"].isoformat() if rule["valid_to"] else None,
            "components":expected_component,"tiers":[t["key"] for t in tiers],"scope":"common_result","source":snapshot})
        return CatalogBinding(source["lottery_id"],source["source_id"],scope["id"],rule["id"],series[0]["id"],
                              components[0]["id"],tuple((t["key"],t["id"]) for t in tiers),fingerprint,snapshot)
