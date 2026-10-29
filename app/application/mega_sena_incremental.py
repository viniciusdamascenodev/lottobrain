"""Política incremental explícita; ponte conservadora não substitui correções JSON."""
from app.application.historical_content import VERSION as HISTORICAL, compare_shared
from app.application.mega_sena_bridge import decide, project
from app.application.mega_sena_content import VERSION, digest
from app.application.persistence import PersistenceError

CODE_VERSION = "spec-0028-v1"
POLICY_VERSION = "mega-sena-incremental-bridge-v1"


def decide_incremental(head: dict | None, incoming: dict) -> tuple[str, dict]:
    if incoming.get("schema_version") != VERSION or incoming.get("lottery") != "mega_sena":
        raise PersistenceError("canonicalization_conflict")
    if head is None:
        return "new", {}
    if head.get("schema_version") == VERSION:
        return ("unchanged" if digest(head) == digest(incoming) else "correction"), compare_shared(project(head),project(incoming))
    if head.get("schema_version") == HISTORICAL:
        decision, comparison = decide(head,incoming)
        # Processamento JSON não declara suporte no contrato histórico. Não mudar
        # a versão da receita nem fabricar hash para contornar o trigger SQL.
        return ("enrichment" if decision == "enrichment" else "quarantined"), comparison
    raise PersistenceError("canonicalization_conflict")
