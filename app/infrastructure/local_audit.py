"""Leitura de evidências sem lock ou escrita no workspace auditado."""
from __future__ import annotations

import os
from pathlib import Path

from app.application.audit_mega_sena import AuditFile, AuditSnapshot, BaselineEvidence
from app.ingestion.mega_sena_history import HistoryBaseline
from app.ingestion.mega_sena import file_sha256

MAX_AUDIT_FILE_BYTES = 8 * 1024 * 1024


class LocalAuditReader:
    def __init__(self, root: Path, baseline_path: Path):
        self.root = root.absolute()
        self.baseline_path = baseline_path

    def capture(self) -> AuditSnapshot:
        baseline = HistoryBaseline()
        try:
            observed = file_sha256(self.baseline_path)
        except OSError:
            observed = None
        evidence = BaselineEvidence(baseline.last_contest, baseline.source_sha256, observed)
        if not self.root.exists():
            return AuditSnapshot(False, (), evidence)
        if not self.root.is_dir() or self.root.is_symlink() or self.root.is_junction():
            return AuditSnapshot(True, (AuditFile(".", None, None, "unsafe_root"),), evidence)
        files = []

        def traversal_error(error):
            path = Path(error.filename).relative_to(self.root).as_posix() if error.filename else "."
            files.append(AuditFile(path, None, None, "unreadable_directory"))

        for directory, directories, names in os.walk(self.root, followlinks=False, onerror=traversal_error):
            current = Path(directory)
            for name in list(directories):
                path = current / name
                if path.is_symlink() or path.is_junction():
                    files.append(AuditFile(path.relative_to(self.root).as_posix(), None, None, "unsafe_link"))
                    directories.remove(name)
            for name in names:
                path = current / name
                relative = path.relative_to(self.root).as_posix()
                if path.is_symlink() or path.is_junction():
                    files.append(AuditFile(relative, None, None, "unsafe_link"))
                    continue
                try:
                    size = path.stat().st_size
                    if size > MAX_AUDIT_FILE_BYTES:
                        files.append(AuditFile(relative, None, size, "too_large"))
                        continue
                    with path.open("rb") as handle:
                        body = handle.read(MAX_AUDIT_FILE_BYTES + 1)
                    if len(body) > MAX_AUDIT_FILE_BYTES:
                        files.append(AuditFile(relative, None, len(body), "too_large"))
                    elif len(body) != size:
                        files.append(AuditFile(relative, body, size, "changed_during_read"))
                    else:
                        files.append(AuditFile(relative, body, size))
                except OSError:
                    files.append(AuditFile(relative, None, None, "unreadable"))
        return AuditSnapshot(True, tuple(sorted(files, key=lambda item: item.path)), evidence)
