"""Carga completa e limitada ao recorte qualificado Mega-Sena; sem SQL/rede."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
from pathlib import Path

from app.application.historical_content import VERSION, canonical_bytes, digest, to_content
from app.application.historical_pilot import PreparedRow, XLSX_SOURCE
from app.application.mega_sena_bridge import POLICY_VERSION
from app.application.persistence import PersistenceError, command_key, transact
from app.domain import RawProvenance
from app.ingestion.mega_sena import iter_xlsx_rows, normalize_row
from app.ingestion.mega_sena_history import HistoryBaseline

CODE_VERSION = "spec-0029-v1"
ORIGIN = "repository:data/raw/mega_sena/mega_sena_resultados.xlsx"


@dataclass(frozen=True)
class HistoricalImportPlan:
    body: bytes
    rows: tuple[PreparedRow, ...]
    source_key: str = field(default=XLSX_SOURCE,init=False)
    adapter_version: str = field(default="spec-0004",init=False)
    _manifest_bytes: bytes = field(init=False,repr=False)
    _fingerprint: str = field(init=False,repr=False)
    sha256: str = field(init=False)

    def __post_init__(self):
        baseline = HistoryBaseline()
        sha = hashlib.sha256(self.body).hexdigest()
        if sha != baseline.source_sha256 or len(self.rows) != baseline.total_rows:
            raise PersistenceError("historical_input_not_qualified")
        records = []
        for index,row in enumerate(self.rows,1):
            if row.contest != str(index) or row.locator != f"data_record:{index}" or row.content["schema_version"] != VERSION:
                raise PersistenceError("historical_selection_not_complete")
            records.append({"locator":row.locator,"contest":row.contest,
                            "content_hash":digest(row.content),"evidence_hash":digest(row.evidence)})
        manifest = {"schema_version":"mega-sena-historical-import-plan-v1", "source_key":XLSX_SOURCE,
            "origin":ORIGIN,"provenance":"local_legacy_registration_original_download_time_unknown",
            "raw_sha256":sha,"byte_count":len(self.body),"adapter_version":self.adapter_version,
            "code_version":CODE_VERSION,"policy_version":POLICY_VERSION,"canonicalization_version":VERSION,
            "record_count":baseline.total_rows,"first_contest":baseline.first_contest,"last_contest":baseline.last_contest,
            "first_date":baseline.first_date,"last_date":baseline.last_date,"records_manifest_sha256":digest(records)}
        encoded = canonical_bytes(manifest)
        object.__setattr__(self,"sha256",sha)
        object.__setattr__(self,"_manifest_bytes",encoded)
        object.__setattr__(self,"_fingerprint",hashlib.sha256(encoded).hexdigest())

    @property
    def manifest(self):
        return json.loads(self._manifest_bytes)

    @property
    def fingerprint(self):
        return self._fingerprint


def prepare_history(body: bytes, *, inspected_at=None) -> HistoricalImportPlan:
    baseline = HistoryBaseline()
    sha = hashlib.sha256(body).hexdigest()
    if sha != baseline.source_sha256:
        raise PersistenceError("historical_input_not_qualified")
    provenance = RawProvenance(XLSX_SOURCE,sha,inspected_at or datetime.now(timezone.utc),"spec-0004")
    rows = []
    for index,raw in enumerate(iter_xlsx_rows(BytesIO(body)),1):
        result = normalize_row(raw,provenance)
        if not result.is_valid:
            raise PersistenceError("historical_row_not_qualified")
        rows.append(PreparedRow.from_candidate(result.candidate,f"data_record:{index}",to_content(result.candidate)))
    if not rows or rows[0].content["draw_date"] != baseline.first_date or rows[-1].content["draw_date"] != baseline.last_date:
        raise PersistenceError("historical_period_not_qualified")
    return HistoricalImportPlan(body,tuple(rows))


def prepare_history_file(path: Path) -> HistoricalImportPlan:
    return prepare_history(path.read_bytes())


def restore_history(body: bytes, manifest: dict) -> HistoricalImportPlan:
    plan = prepare_history(body)
    if plan.fingerprint != digest(manifest):
        raise PersistenceError("historical_manifest_mismatch")
    return plan


class ImportMegaSenaHistory:
    def __init__(self, units, storage, observe=lambda stage,row:None, *, verification_block=50):
        if type(verification_block) is not int or not 1 <= verification_block <= 100:
            raise ValueError("bloco de verificação entre 1 e 100 registros")
        self.units,self.storage,self.observe,self.verification_block = units,storage,observe,verification_block

    def execute(self, plan: HistoricalImportPlan, key: str):
        key = command_key(key)
        plan = restore_history(plan.body,plan.manifest)
        sha,object_key = self.storage.put(plan.body)  # I/O fora de SQL.
        if sha != plan.sha256:
            raise PersistenceError("artifact_hash_mismatch")
        registration = transact(self.units,lambda u:u.history.register(plan,key,object_key))
        pending = transact(self.units,lambda u:u.history.pending(registration,plan))
        for index,row in enumerate(pending):
            if index % self.verification_block == 0:
                self.storage.read(object_key,sha,len(plan.body))
            self.observe("before_row",row)
            transact(self.units,lambda u:u.history.process(registration,plan,row))
            self.observe("after_row",row)
        self.storage.read(object_key,sha,len(plan.body))
        return transact(self.units,lambda u:u.history.finish(registration,plan))

    def _saved(self, key):
        saved = transact(self.units,lambda u:u.history.describe(XLSX_SOURCE,key))
        body = self.storage.read(saved["object_key"],saved["sha256"],saved["byte_count"])
        return restore_history(body,saved["manifest"])

    def resume(self, key: str):
        key = command_key(key)
        return self.execute(self._saved(key),key)

    def audit(self, key: str):
        key = command_key(key)
        plan = self._saved(key)
        return transact(self.units,lambda u:u.history.audit(key,plan))
