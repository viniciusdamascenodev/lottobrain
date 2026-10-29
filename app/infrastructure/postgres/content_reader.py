"""Reconstrução relacional Mega-Sena em lote; hashes não vêm de snapshots JSON."""
from collections import defaultdict

from app.application.historical_content import VERSION as HISTORICAL
from app.application.mega_sena_content import VERSION, decimal_text, digest
from app.application.persistence import PersistenceError


def read_contents(db, revision_ids, *, allowed_versions=(VERSION,HISTORICAL)):
    ids = list(dict.fromkeys(revision_ids))
    if len(ids) > 6000 or not set(allowed_versions) <= {VERSION,HISTORICAL}:
        raise PersistenceError("canonicalization_conflict")
    if not ids:
        return {}
    revisions = db.execute("""SELECT r.*,v.version_label,l.slug FROM lb.draw_revision r
        JOIN lb.rule_version v ON v.id=r.rule_version_id JOIN lb.lottery l ON l.id=r.lottery_id
        WHERE r.id=ANY(%s)""",(ids,)).fetchall()
    if len(revisions) != len(ids) or any(r["canonicalization_version"] not in allowed_versions or r["slug"] != "mega_sena" for r in revisions):
        raise PersistenceError("canonicalization_conflict")
    series_rows = db.execute("""SELECT rs.id,rs.revision_id,sd.key FROM lb.result_series rs
        JOIN lb.series_definition sd ON sd.id=rs.series_definition_id
        WHERE rs.revision_id=ANY(%s) ORDER BY sd.key""",(ids,)).fetchall()
    values = db.execute("""SELECT rs.id AS series_id,c.id AS component_id,c.key,c.position,
        v.ordinal,v.integer_value,v.text_value,v.extraction_ordinal FROM lb.result_series rs
        JOIN lb.component_definition c ON c.series_definition_id=rs.series_definition_id
        LEFT JOIN lb.component_value v ON v.result_series_id=rs.id AND v.component_definition_id=c.id
        WHERE rs.revision_id=ANY(%s) ORDER BY c.position,v.ordinal""",(ids,)).fetchall()
    if db.execute("SELECT 1 FROM lb.result_attribute WHERE revision_id=ANY(%s) LIMIT 1",(ids,)).fetchone():
        raise PersistenceError("invalid_revision")
    money_rows = db.execute("""SELECT m.*,s.key AS scope FROM lb.monetary_fact m
        JOIN lb.lottery_scope s ON s.id=m.scope_id WHERE m.revision_id=ANY(%s) ORDER BY m.kind""",(ids,)).fetchall()
    tiers = db.execute("""SELECT t.*,d.key,s.key AS scope FROM lb.prize_tier_result t
        JOIN lb.prize_tier_definition d ON d.id=t.tier_definition_id JOIN lb.lottery_scope s ON s.id=t.scope_id
        WHERE t.revision_id=ANY(%s) ORDER BY d.key""",(ids,)).fetchall()
    by_revision,components,money_by_revision,tiers_by_revision = defaultdict(list),defaultdict(dict),defaultdict(list),defaultdict(list)
    for s in series_rows: by_revision[s["revision_id"]].append(s)
    for v in values:
        component = components[v["series_id"]].setdefault(v["component_id"],{"key":v["key"],"values":[]})
        if v["ordinal"] is not None:
            component["values"].append({k:v[k] for k in ("ordinal","integer_value","text_value","extraction_ordinal")})
    for m in money_rows: money_by_revision[m["revision_id"]].append(m)
    for t in tiers: tiers_by_revision[t["revision_id"]].append(t)

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
            series.append({"key":s["key"],"components":normalized,**({"attributes":[]} if version == HISTORICAL else {})})
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
