"""Diagnóstico determinístico de cobertura a partir de um snapshot SQL verificado."""
from collections import Counter, defaultdict

from app.application.historical_content import digest, compare_shared
from app.application.mega_sena_bridge import project, POLICY_VERSION
from app.application.historical_import import CODE_VERSION


def coverage_report(plan, registration, run_status, observations, attempts, aliases, contents, continuity):
    expected = {row.locator:row for row in plan.rows}
    by_locator, by_draw = defaultdict(list),defaultdict(list)
    for item in observations: by_locator[item["row_locator"]].append(item)
    for alias in aliases: by_draw[alias["draw_id"]].append(alias)
    ledger = {a["command_key"]:a for a in attempts}
    missing = sorted(set(expected)-set(by_locator),key=lambda key:int(key.split(":")[1]))
    unexpected = sorted(set(by_locator)-set(expected))
    duplicates = sorted(k for k,v in by_locator.items() if len(v) != 1)
    problems, records, outcomes, versions, head_versions = [],[],Counter(),Counter(),Counter()
    verified, quarantined = 0,0
    expected_commands = set()
    for locator,row in expected.items():
        command = "historical-row:" + digest({"run":str(registration["run_id"]),"locator":locator})
        expected_commands.add(command)
        items = by_locator.get(locator,())
        if len(items) != 1: continue
        o = items[0]; errors = []
        outcomes[o["decision"]] += 1
        if o["decision"] not in {"new","unchanged","correction_candidate","replayed"}:
            quarantined += 1; errors.append("observation_not_accepted")
        attempt = ledger.get(command)
        if (not attempt or attempt["processing_run_id"] != o["processing_run_id"]
                or attempt["outcome"] != o["decision"]
                or attempt["request_hash"] != digest({"plan_request":registration["request_hash"],"locator":locator})):
            errors.append("command_ledger_mismatch")
        if (o["code_version"] != CODE_VERSION or o["adapter_version"] != plan.adapter_version
                or o["catalog_fingerprint"] != registration["catalog_fingerprint"]
                or o["validation_policy_version"] != f"{POLICY_VERSION}:{plan.fingerprint}"):
            errors.append("recipe_mismatch")
        if not any(a["namespace"] == "official_draw_number" and a["value"] == row.contest
                   and a["active"] and a["assurance"] == "official" for a in by_draw[o["draw_id"]]):
            errors.append("identity_mismatch")
        try:
            payload = o["diagnostic_payload"]
            input_hash,evidence_hash = digest(payload["input_content"]),digest(payload["source_evidence"])
            if (payload["schema_version"] != "historical-import-observation-v1" or payload["plan_hash"] != plan.fingerprint
                    or payload["policy_version"] != POLICY_VERSION or payload["input_contract"] != row.content["schema_version"]
                    or payload["input_hash"] != input_hash or input_hash != digest(row.content)
                    or payload["evidence_hash"] != evidence_hash or evidence_hash != digest(row.evidence)):
                errors.append("input_or_evidence_mismatch")
            records.append({"locator":locator,"contest":row.contest,"content_hash":input_hash,"evidence_hash":evidence_hash})
        except (KeyError,TypeError,ValueError):
            errors.append("invalid_observation_payload")
        supported = contents.get(o["revision_id"])
        if not supported or o["seal_state"] != "sealed":
            errors.append("missing_or_unsealed_revision")
        else:
            versions[supported["schema_version"]] += 1
            if o["semantic_hash"] != digest(supported) or o["canonicalization_version"] != supported["schema_version"]:
                errors.append("support_hash_or_version_mismatch")
            comparison = compare_shared(project(row.content),project(supported))
            if comparison["different"] or comparison["only_left"]:
                errors.append("relational_content_mismatch")
        head = contents.get(o["latest_candidate_revision_id"])
        if not head:
            errors.append("missing_head")
        else: head_versions[head["schema_version"]] += 1
        if o["published_revision_id"] is not None: errors.append("unexpected_publication")
        if errors: problems.append({"locator":locator,"codes":errors})
        else: verified += 1
    actual_manifest = digest(records)
    extras = sorted(set(ledger)-expected_commands)
    qualified = (verified == len(plan.rows) and not missing and not unexpected and not duplicates
                 and not problems and not extras and actual_manifest == plan.manifest["records_manifest_sha256"])
    return {"report_version":"mega-sena-historical-coverage-v1","mode":"controlled_import_no_publication",
        "plan_hash":plan.fingerprint,"raw_sha256":plan.sha256,"expected_records":len(plan.rows),
        "first_contest":1,"last_contest":len(plan.rows),"first_date":plan.manifest["first_date"],"last_date":plan.manifest["last_date"],
        "observed_records":len(observations),"verified_records":verified,"quarantined_records":quarantined,
        "missing":missing,"unexpected":unexpected,"duplicates":duplicates,"problems":problems,
        "unexpected_commands":extras,"observed_records_manifest_sha256":actual_manifest,
        "expected_records_manifest_sha256":plan.manifest["records_manifest_sha256"],
        "outcome_counts":dict(sorted(outcomes.items())),"supported_contracts":dict(sorted(versions.items())),
        "head_contracts":dict(sorted(head_versions.items())),"continuity":continuity,
        "run_status":run_status,"qualified":qualified}
