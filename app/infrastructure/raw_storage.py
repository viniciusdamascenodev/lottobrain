"""Bytes por conteúdo, separados dos receipts SQL e do workspace legado."""
import hashlib
import os
from pathlib import Path
import re
import tempfile

from app.application.collect_mega_sena import MAX_RESPONSE_BYTES
from app.application.persistence import PersistenceError


class LocalRawStorage:
    def __init__(self, root: Path, *, max_bytes: int = MAX_RESPONSE_BYTES):
        if type(max_bytes) is not int or not 1 <= max_bytes <= 8 * 1024 * 1024:
            raise ValueError("Limite de artefato entre 1 byte e 8 MiB.")
        self.root = Path(root).resolve()
        self.max_bytes = max_bytes

    def put(self, body: bytes) -> tuple[str, str]:
        if not isinstance(body, bytes) or len(body) > self.max_bytes:
            raise PersistenceError("invalid_artifact")
        sha = hashlib.sha256(body).hexdigest()
        key = f"{sha[:2]}/{sha}.bin"
        target = self.root / key
        temporary = None
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.parent.is_symlink() or target.is_symlink() or target.parent.resolve() != target.parent:
                raise PersistenceError("unsafe_artifact_path")
            with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".pending-", delete=False) as output:
                temporary = Path(output.name)
                output.write(body)
                output.flush()
                os.fsync(output.fileno())
            try:
                os.link(temporary, target)
            except FileExistsError:
                self.read(key, sha, len(body))
            return sha, key
        except OSError:
            raise PersistenceError("storage_unavailable") from None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def read(self, key: str, sha256: str, byte_count: int) -> bytes:
        if not re.fullmatch(r"[0-9a-f]{64}", sha256) or key != f"{sha256[:2]}/{sha256}.bin" or not 0 <= byte_count <= self.max_bytes:
            raise PersistenceError("invalid_artifact")
        target = self.root / key
        if target.is_symlink() or target.parent.is_symlink() or target.parent.resolve() != target.parent:
            raise PersistenceError("unsafe_artifact_path")
        try:
            with target.open("rb") as source:
                body = source.read(self.max_bytes + 1)
        except FileNotFoundError:
            raise PersistenceError("evidence_missing") from None
        except OSError:
            raise PersistenceError("storage_unavailable") from None
        if len(body) != byte_count or hashlib.sha256(body).hexdigest() != sha256:
            raise PersistenceError("artifact_hash_mismatch")
        return body
