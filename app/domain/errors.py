from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str
    path: str
    message: str
    observed: object | None = None
    expected: object | None = None


class DomainValidationError(ValueError):
    def __init__(self, issues: Iterable[ValidationIssue]):
        self.issues = tuple(issues)
        summary = "; ".join(
            f"{issue.code} em {issue.path}: {issue.message}" for issue in self.issues
        )
        super().__init__(summary or "Falha de validação do domínio")

