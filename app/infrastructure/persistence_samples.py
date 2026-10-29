"""Seleção de um registro de arquivo local, usando os leitores já qualificados."""

from datetime import UTC, datetime
from hashlib import sha256
from itertools import islice
from pathlib import Path
from tempfile import TemporaryDirectory

from app.application.result_persistence import MAX_ARTIFACT_BYTES, PreparedResult
from app.domain import RawProvenance
from app.ingestion.historical_qualification import HISTORIES


def prepare_sample(lottery, path, ordinal):
    if type(ordinal) is not int or ordinal < 1:
        raise ValueError("Ordinal positivo necessário.")
    profile = next((p for p in HISTORIES if p[0].__name__.rsplit(".", 1)[-1] == lottery), None)
    if profile is None:
        raise ValueError("Loteria sem perfil de arquivo local.")
    module, _, extension, reader, adapter = profile
    path = Path(path)
    if path.suffix.lower() != "." + extension:
        raise ValueError("Formato não corresponde ao perfil qualificado.")
    with path.open("rb") as source:
        body = source.read(MAX_ARTIFACT_BYTES + 1)
    if len(body) > MAX_ARTIFACT_BYTES:
        raise ValueError("Arquivo acima do limite de 8 MiB.")
    provenance = RawProvenance(
        module.SOURCE_KEY, sha256(body).hexdigest(), datetime.now(UTC), adapter
    )
    # O parser lê um snapshot dos bytes arquivados, não um arquivo que pode mudar.
    with TemporaryDirectory(prefix="lottobrain-sample-") as temporary:
        snapshot = Path(temporary) / ("source." + extension)
        snapshot.write_bytes(body)
        rows = iter(reader(snapshot))
        try:
            row = next(islice(rows, ordinal - 1, ordinal), None)
            if row is None:
                raise ValueError("Ordinal ausente no arquivo.")
            normalized = module.normalize_row(row, provenance)
            if not normalized.is_valid:
                raise ValueError("Registro não aprovado pelo normalizador existente.")
            return PreparedResult.from_candidate(
                normalized.candidate, body, f"data-record:{ordinal}", path.name
            )
        finally:
            if hasattr(rows, "close"):
                rows.close()
