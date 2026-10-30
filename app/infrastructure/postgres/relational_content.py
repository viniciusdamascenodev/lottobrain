"""Escrita dos componentes canônicos, compartilhada pelos perfis SQL."""

from uuid import uuid4

from app.application.persistence import PersistenceError
from app.infrastructure.postgres.common import insert


def append_series(db, binding, revision, content):
    definitions = {
        row["key"]: row["id"]
        for row in db.execute(
            "SELECT id,key FROM lb.series_definition WHERE rule_version_id=%s",
            (binding.rule_id,),
        ).fetchall()
    }
    for series in content["series"]:
        if series["key"] not in definitions:
            raise PersistenceError("catalog_not_qualified")
        definition = definitions[series["key"]]
        result = insert(
            db,
            "result_series",
            id=uuid4(),
            revision_id=revision,
            rule_version_id=binding.rule_id,
            lottery_id=binding.lottery_id,
            series_definition_id=definition,
        )
        components = {
            row["key"]: row["id"]
            for row in db.execute(
                "SELECT id,key FROM lb.component_definition WHERE series_definition_id=%s",
                (definition,),
            ).fetchall()
        }
        if set(components) != {c["key"] for c in series["components"]}:
            raise PersistenceError("catalog_not_qualified")
        for component in series["components"]:
            for value in component["values"]:
                insert(
                    db,
                    "component_value",
                    result_series_id=result,
                    revision_id=revision,
                    series_definition_id=definition,
                    component_definition_id=components[component["key"]],
                    **value,
                )
        for attribute in series.get("attributes", ()):
            field = attribute["value_type"] + "_value"
            if field not in {"integer_value", "decimal_value", "text_value", "boolean_value"}:
                raise PersistenceError("invalid_revision")
            insert(
                db,
                "result_attribute",
                result_series_id=result,
                revision_id=revision,
                key=attribute["key"],
                value_type=attribute["value_type"],
                **{field: attribute["value"]},
            )
