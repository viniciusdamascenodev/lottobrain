"""Persistência limitada de um resultado já normalizado; sem SQL, rede ou lote histórico."""

from dataclasses import dataclass
from hashlib import sha256

from app.application.historical_content import canonical_bytes, digest, to_content
from app.application.historical_pilot import PreparedRow
from app.application.persistence import PersistenceError, command_key, transact

MAX_ARTIFACT_BYTES = 8 * 1024 * 1024


@dataclass(frozen=True)
class PreparedResult:
    body: bytes
    source_key: str
    adapter_version: str
    artifact_name: str
    row: PreparedRow

    @classmethod
    def from_candidate(cls, candidate, body, locator, artifact_name):
        if (
            candidate.provenance is None
            or not isinstance(body, bytes)
            or len(body) > MAX_ARTIFACT_BYTES
            or sha256(body).hexdigest() != candidate.provenance.raw_sha256
        ):
            raise PersistenceError("artifact_hash_mismatch")
        if not isinstance(locator, str) or not 1 <= len(locator) <= 200:
            raise ValueError("Localizador obrigatório, até 200 caracteres.")
        if not isinstance(artifact_name, str) or not 1 <= len(artifact_name) <= 512:
            raise ValueError("Referência de arquivo obrigatória.")
        return cls(
            body,
            candidate.provenance.source_key,
            candidate.provenance.adapter_version,
            artifact_name,
            PreparedRow.from_candidate(candidate, locator, to_content(candidate)),
        )

    @property
    def sha256(self):
        return sha256(self.body).hexdigest()

    def request_hash(self, catalog_hash, allow_correction):
        return digest(
            {
                "artifact": self.sha256,
                "source": self.source_key,
                "adapter": self.adapter_version,
                "origin": self.artifact_name,
                "locator": self.row.locator,
                "content": self.row.content,
                "evidence": self.row.evidence,
                "catalog": catalog_hash,
                "allow_correction": allow_correction,
            }
        )


class PersistQualifiedResult:
    def __init__(self, units, storage):
        self.units, self.storage = units, storage

    def execute(self, prepared, key, *, allow_correction=False):
        command_key(key)
        if type(allow_correction) is not bool:
            raise ValueError("Decisão de correção explícita necessária.")
        if len(canonical_bytes(prepared.row.evidence)) > 24576:
            raise PersistenceError("observation_evidence_too_large")
        sha, object_key = self.storage.put(prepared.body)
        if sha != prepared.sha256:
            raise PersistenceError("artifact_hash_mismatch")
        return transact(
            self.units,
            lambda unit: unit.results.store(
                prepared, key, object_key, allow_correction=allow_correction
            ),
        )
