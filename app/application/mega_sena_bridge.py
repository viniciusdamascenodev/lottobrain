"""Ponte conservadora de dois contratos; não altera conteúdo persistido nem faz merge."""
from copy import deepcopy

from app.application.historical_content import VERSION as HISTORICAL, compare_shared
from app.application.mega_sena_content import VERSION as JSON_V1
from app.application.persistence import PersistenceError

POLICY_VERSION = "mega-sena-historical-bridge-v1"


def project(content: dict) -> dict:
    if content.get("lottery") != "mega_sena" or content.get("schema_version") not in (JSON_V1, HISTORICAL):
        raise PersistenceError("canonicalization_conflict")
    result = deepcopy(content)
    if content["schema_version"] == JSON_V1:
        result["schema_version"] = HISTORICAL
        result["identity"] = {"namespace":"official_draw_number", "value":content["identity"], "assurance":"official"}
        for series in result["series"]:
            series["attributes"] = []
            for component in series["components"]:
                for value in component["values"]:
                    value["text_value"] = None
    return result


def decide(head: dict | None, incoming: dict) -> tuple[str, dict]:
    projected = project(incoming)
    if head is None:
        return "new", {}
    comparison = compare_shared(project(head), projected)
    if comparison["different"] or comparison["only_left"] and comparison["only_right"]:
        return "quarantined", comparison
    if comparison["only_right"]:
        return "enrichment", comparison
    return "support", comparison
