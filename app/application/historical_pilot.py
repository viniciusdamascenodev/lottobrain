"""Preparação e caso de uso limitados da SPEC-0027; sem SQL, rede ou framework."""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
from pathlib import Path
from typing import Protocol

from app.application.historical_content import canonical_bytes, digest, source_evidence, to_content as historical_content
from app.application.mega_sena_bridge import POLICY_VERSION
from app.application.mega_sena_content import to_content as json_content
from app.application.persistence import PersistenceError, command_key, transact
from app.domain import RawProvenance
from app.ingestion import mega_sena, mega_sena_api
from app.ingestion.mega_sena_history import HistoryBaseline

CODE_VERSION = "spec-0027-v1"
XLSX_SOURCE = mega_sena.SOURCE_KEY
JSON_SOURCE = mega_sena_api.SOURCE_KEY
PILOT_ROWS = (1, 2, 2954)


@dataclass(frozen=True)
class PreparedRow:
    locator: str
    contest: str
    content_bytes: bytes
    evidence_bytes: bytes

    @classmethod
    def from_candidate(cls, candidate, locator, content):
        return cls(locator,candidate.official_draw_number,canonical_bytes(content),canonical_bytes(source_evidence(candidate)))

    @property
    def content(self):
        return json.loads(self.content_bytes)

    @property
    def evidence(self):
        return json.loads(self.evidence_bytes)


@dataclass(frozen=True)
class PreparedPlan:
    body: bytes
    source_key: str
    origin: str
    adapter_version: str
    rows: tuple[PreparedRow, ...]

    def __post_init__(self):
        if self.source_key not in (XLSX_SOURCE, JSON_SOURCE) or not 1 <= len(self.rows) <= 3:
            raise ValueError("plano fora do piloto")
        if len({r.locator for r in self.rows}) != len(self.rows) or any(int(r.contest) not in PILOT_ROWS for r in self.rows):
            raise ValueError("seleção fora do piloto")
        if not self.origin or len(self.origin) > 512:
            raise ValueError("origem legada explícita necessária")

    @property
    def sha256(self):
        return hashlib.sha256(self.body).hexdigest()

    @property
    def manifest(self):
        return {"schema_version":"historical-pilot-plan-v1", "source_key":self.source_key, "origin":self.origin,
            "provenance":"local_legacy_registration_original_download_time_unknown", "raw_sha256":self.sha256,
            "byte_count":len(self.body), "adapter_version":self.adapter_version, "code_version":CODE_VERSION,
            "policy_version":POLICY_VERSION, "rows":[{"locator":r.locator,"contest":r.contest,
                "canonicalization_version":r.content["schema_version"],"content_hash":digest(r.content),
                "evidence_hash":digest(r.evidence)} for r in self.rows]}

    @property
    def fingerprint(self):
        return digest(self.manifest)


def _prepared(candidate, locator, content):
    return PreparedRow.from_candidate(candidate,locator,content)


def _selection(selected):
    selected = tuple(selected)
    if (not selected or len(selected) != len(set(selected)) or
            any(type(n) is not int or n not in PILOT_ROWS for n in selected)):
        raise ValueError("somente linhas 1, 2 e 2954, sem repetições")
    return selected


def prepare_xlsx(path: Path, selected=PILOT_ROWS, *, inspected_at=None) -> PreparedPlan:
    selected = _selection(selected)
    return _prepare_xlsx_bytes(path.read_bytes(),selected,inspected_at=inspected_at)


def _prepare_xlsx_bytes(body: bytes, selected=PILOT_ROWS, *, inspected_at=None) -> PreparedPlan:
    selected = _selection(selected)
    sha = hashlib.sha256(body).hexdigest()
    if sha != HistoryBaseline().source_sha256:
        raise PersistenceError("pilot_input_not_qualified")
    provenance = RawProvenance(XLSX_SOURCE,sha,inspected_at or datetime.now(timezone.utc),"spec-0004")
    rows = []
    # Lê exatamente os bytes que serão arquivados: sem janela de troca do arquivo.
    for ordinal, raw in enumerate(mega_sena.iter_xlsx_rows(BytesIO(body)),1):
        if ordinal in selected:
            result = mega_sena.normalize_row(raw,provenance)
            if not result.is_valid or result.candidate.official_draw_number != str(ordinal):
                raise PersistenceError("pilot_row_not_qualified")
            rows.append(_prepared(result.candidate,f"data_record:{ordinal}",historical_content(result.candidate)))
        if ordinal >= max(selected):
            break
    if len(rows) != len(selected):
        raise PersistenceError("pilot_row_not_found")
    return PreparedPlan(body,XLSX_SOURCE,"repository:data/raw/mega_sena/mega_sena_resultados.xlsx","spec-0004",tuple(rows))


def prepare_json(body: bytes, *, origin: str, inspected_at=None) -> PreparedPlan:
    result = mega_sena_api.normalize_response(body,RawProvenance(JSON_SOURCE,hashlib.sha256(body).hexdigest(),
        inspected_at or datetime.now(timezone.utc),mega_sena_api.ADAPTER_VERSION),expected_contest=2954)
    if not result.is_valid:
        raise PersistenceError("pilot_row_not_qualified")
    return PreparedPlan(body,JSON_SOURCE,origin,mega_sena_api.ADAPTER_VERSION,
                        (_prepared(result.candidate,"/",json_content(result.candidate)),))


def restore_plan(body: bytes, manifest: dict) -> PreparedPlan:
    """Reconstitui a partir de raw + manifesto persistidos, sem confiar em DTO editado."""
    if manifest.get("source_key") == XLSX_SOURCE:
        plan = _prepare_xlsx_bytes(body,tuple(int(r["contest"]) for r in manifest["rows"]))
    elif manifest.get("source_key") == JSON_SOURCE:
        plan = prepare_json(body,origin=manifest["origin"])
    else:
        raise PersistenceError("pilot_input_not_qualified")
    if plan.fingerprint != digest(manifest):
        raise PersistenceError("pilot_manifest_mismatch")
    return plan


class PilotRepository(Protocol):
    def register(self, plan: PreparedPlan, key: str, object_key: str): ...
    def process(self, registration: dict, plan: PreparedPlan, row: PreparedRow): ...
    def finish(self, registration: dict, plan: PreparedPlan): ...
    def describe(self, source_key: str, key: str): ...


class ImportHistoricalPilot:
    def __init__(self, units, storage, observe=lambda stage,row:None):
        self.units, self.storage, self.observe = units, storage, observe

    def execute(self, plan: PreparedPlan, key: str):
        key = command_key(key)
        plan = restore_plan(plan.body,plan.manifest)
        # PUT fora de qualquer transação. Repetição só verifica bytes já existentes.
        sha, object_key = self.storage.put(plan.body)
        if sha != plan.sha256:
            raise PersistenceError("artifact_hash_mismatch")
        registration = transact(self.units,lambda u:u.pilot.register(plan,key,object_key))
        for row in plan.rows:
            self.observe("before_row",row)
            # Confere disponibilidade/corrupção também nas retomadas, fora de SQL.
            self.storage.read(object_key,sha,len(plan.body))
            transact(self.units,lambda u:u.pilot.process(registration,plan,row))
            self.observe("after_row",row)
        return transact(self.units,lambda u:u.pilot.finish(registration,plan))

    def resume(self, source_key: str, key: str):
        key = command_key(key)
        saved = transact(self.units,lambda u:u.pilot.describe(source_key,key))
        body = self.storage.read(saved["object_key"],saved["sha256"],saved["byte_count"])
        return self.execute(restore_plan(body,saved["manifest"]),key)
