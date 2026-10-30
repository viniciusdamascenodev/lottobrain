"""Reconstrução relacional verificada; hashes não vêm de snapshots JSON."""
from collections import defaultdict

from app.application.historical_content import VERSION as HISTORICAL
from app.application.mega_sena_content import VERSION, decimal_text, digest
from app.application.persistence import PersistenceError
from app.application.historical_content import PROFILES


def read_contents(db, revision_ids, *, allowed_versions=(VERSION,HISTORICAL), dataset_id=None):
    ids = list(dict.fromkeys(revision_ids))
    if len(ids) > 6000 or not set(allowed_versions) <= {VERSION,HISTORICAL}:
        raise PersistenceError("canonicalization_conflict")
    if not ids:
        return {}
    # Nomes fixos, nunca interpolados a partir de entrada de usuário.
    prefix = "approved_" if dataset_id is not None else ""
    suffix = " AND r.dataset_id=%s" if dataset_id is not None else ""
    params = (ids,dataset_id) if dataset_id is not None else (ids,)
    revisions = db.execute(f"""SELECT r.*,v.version_label,l.slug FROM lb.{prefix}draw_revision r
        JOIN lb.rule_version v ON v.id=r.rule_version_id JOIN lb.lottery l ON l.id=r.lottery_id
        WHERE r.id=ANY(%s){suffix}""",params).fetchall()
    supported = {p.lottery for p in PROFILES.values()}
    if len(revisions) != len(ids) or any(
        r["canonicalization_version"] not in allowed_versions or r["slug"] not in supported
        or r["canonicalization_version"] == VERSION and r["slug"] != "mega_sena"
        for r in revisions
    ):
        raise PersistenceError("canonicalization_conflict")
    series_suffix = " AND rs.dataset_id=%s" if dataset_id is not None else ""
    series_rows = db.execute(f"""SELECT rs.id,rs.revision_id,sd.key FROM lb.{prefix}result_series rs
        JOIN lb.series_definition sd ON sd.id=rs.series_definition_id
        WHERE rs.revision_id=ANY(%s){series_suffix} ORDER BY sd.key""",params).fetchall()
    value_context = " AND v.dataset_id=rs.dataset_id" if dataset_id is not None else ""
    values = db.execute(f"""SELECT rs.id AS series_id,c.id AS component_id,c.key,c.position,
        v.ordinal,v.integer_value,v.text_value,v.extraction_ordinal FROM lb.{prefix}result_series rs
        JOIN lb.component_definition c ON c.series_definition_id=rs.series_definition_id
        LEFT JOIN lb.{prefix}component_value v ON v.result_series_id=rs.id AND v.component_definition_id=c.id{value_context}
        WHERE rs.revision_id=ANY(%s){series_suffix} ORDER BY c.key,v.ordinal""",params).fetchall()
    attr_suffix = " AND dataset_id=%s" if dataset_id is not None else ""
    attributes = db.execute(f"""SELECT * FROM lb.{prefix}result_attribute
        WHERE revision_id=ANY(%s){attr_suffix} ORDER BY key""",params).fetchall()
    money_suffix = " AND m.dataset_id=%s" if dataset_id is not None else ""
    money_rows = db.execute(f"""SELECT m.*,s.key AS scope FROM lb.{prefix}monetary_fact m
        JOIN lb.lottery_scope s ON s.id=m.scope_id WHERE m.revision_id=ANY(%s){money_suffix} ORDER BY m.kind""",params).fetchall()
    tier_suffix = " AND t.dataset_id=%s" if dataset_id is not None else ""
    tiers = db.execute(f"""SELECT t.*,d.key,s.key AS scope FROM lb.{prefix}prize_tier_result t
        JOIN lb.prize_tier_definition d ON d.id=t.tier_definition_id JOIN lb.lottery_scope s ON s.id=t.scope_id
        WHERE t.revision_id=ANY(%s){tier_suffix} ORDER BY d.key""",params).fetchall()
    by_revision,components,money_by_revision,tiers_by_revision = defaultdict(list),defaultdict(dict),defaultdict(list),defaultdict(list)
    for s in series_rows: by_revision[s["revision_id"]].append(s)
    for v in values:
        component = components[v["series_id"]].setdefault(v["component_id"],{"key":v["key"],"values":[]})
        if v["ordinal"] is not None:
            component["values"].append({k:v[k] for k in ("ordinal","integer_value","text_value","extraction_ordinal")})
    for m in money_rows: money_by_revision[m["revision_id"]].append(m)
    for t in tiers: tiers_by_revision[t["revision_id"]].append(t)
    attrs_by_series = defaultdict(list)
    for a in attributes:
        value = a[a["value_type"] + "_value"]
        if a["value_type"] == "decimal":
            value = decimal_text(value)
        attrs_by_series[a["result_series_id"]].append(
            {"key":a["key"],"value_type":a["value_type"],"value":value}
        )

    def money(row):
        return {"kind":row["kind"],"scope":row["scope"],"payout_form":row["payout_form"],"status":row["status"],
            "amount":decimal_text(row["amount"]) if row["amount"] is not None else None,"currency":row["currency"]}

    result = {}
    for r in revisions:
        version = r["canonicalization_version"]
        metadata = dict(r["metadata"]); identity = metadata.pop("_canonical_identity",None)
        series = []
        for s in by_revision[r["id"]]:
            normalized = [{"key":c["key"],"values":[{k:v for k,v in value.items() if version == HISTORICAL or k != "text_value"}
                for value in c["values"]]} for c in components[s["id"]].values()]
            attrs = attrs_by_series[s["id"]]
            if version == VERSION and attrs:
                raise PersistenceError("invalid_revision")
            series.append({"key":s["key"],"components":normalized,**({"attributes":attrs} if version == HISTORICAL else {})})
        financial = money_by_revision[r["id"]]
        tier_content = []
        for tier in tiers_by_revision[r["id"]]:
            prizes = [m for m in financial if m["tier_result_id"] == tier["id"]]
            if len(prizes) > 1: raise PersistenceError("invalid_revision")
            tier_content.append({"key":tier["key"],"scope":tier["scope"],"variant":tier["variant_key"],
                "winners_status":tier["winners_status"],"winners":tier["winners"],"prize":money(prizes[0]) if prizes else None})
        content = {"schema_version":version,"lottery":r["slug"],"identity":identity,"rule_version":r["version_label"],
            "draw_date":r["draw_date_local"].isoformat(),"series":series,"prize_tiers":tier_content,
            "money":[money(m) for m in financial if m["tier_result_id"] is None],"metadata":metadata}
        if digest(content) != r["content_hash"]:
            raise PersistenceError("artifact_hash_mismatch")
        result[r["id"]] = content
    return result
