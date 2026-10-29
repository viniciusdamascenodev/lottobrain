from enum import Enum


class StringEnum(str, Enum):
    """Enum textual serializável sem depender de framework."""


class LotteryStatus(StringEnum):
    DRAFT = "draft"
    VALIDATING = "validating"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class RuleStatus(StringEnum):
    DRAFT = "draft"
    VALIDATED = "validated"
    RETIRED = "retired"


class SeriesRole(StringEnum):
    PRIMARY = "primary"
    ADDITIONAL = "additional"


class ValueType(StringEnum):
    INTEGER = "integer"
    TEXT = "text"


class OrderSemantics(StringEnum):
    DRAW_ORDER = "draw_order"
    SORTED = "sorted"
    NONE = "none"


class DrawStatus(StringEnum):
    CANDIDATE = "candidate"
    VALIDATED = "validated"
    PUBLISHED = "published"
    QUARANTINED = "quarantined"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class ValueStatus(StringEnum):
    KNOWN = "known"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"
    REJECTED = "rejected"

