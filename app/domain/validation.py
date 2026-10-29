from app.domain.errors import DomainValidationError, ValidationIssue
from app.domain.models import ComponentDefinition, DrawCandidate, Lottery
from app.domain.types import DrawStatus, OrderSemantics, ValueType


def _issue(
    code: str,
    path: str,
    message: str,
    observed: object | None = None,
    expected: object | None = None,
) -> ValidationIssue:
    return ValidationIssue(code, path, message, observed, expected)


def _validate_values(definition: ComponentDefinition, values: tuple, path: str):
    issues = []
    count = len(values)
    if not definition.min_count <= count <= definition.max_count:
        issues.append(
            _issue(
                "component.invalid_count",
                path,
                "quantidade de valores fora da cardinalidade permitida",
                count,
                f"{definition.min_count}..{definition.max_count}",
            )
        )

    if definition.value_type is ValueType.INTEGER:
        invalid_types = [value for value in values if isinstance(value, bool) or not isinstance(value, int)]
        if invalid_types:
            issues.append(
                _issue(
                    "component.invalid_type",
                    path,
                    "componente requer valores inteiros",
                    invalid_types,
                    "integer",
                )
            )
        else:
            outside = [
                value
                for value in values
                if value < definition.min_value or value > definition.max_value
            ]
            if outside:
                issues.append(
                    _issue(
                        "component.out_of_range",
                        path,
                        "valor fora dos limites da regra",
                        outside,
                        f"{definition.min_value}..{definition.max_value}",
                    )
                )
    elif any(not isinstance(value, str) for value in values):
        issues.append(
            _issue(
                "component.invalid_type",
                path,
                "componente requer valores textuais",
                values,
                "text",
            )
        )

    if definition.unique_values and len(values) != len(set(values)):
        issues.append(
            _issue(
                "component.duplicate_values",
                path,
                "valores do componente devem ser distintos",
                values,
            )
        )

    if definition.order_semantics is OrderSemantics.SORTED:
        try:
            is_sorted = list(values) == sorted(values)
        except TypeError:
            is_sorted = False
        if not is_sorted:
            issues.append(
                _issue(
                    "component.invalid_order",
                    path,
                    "valores devem estar ordenados",
                    values,
                    "ascending",
                )
            )
    return issues


def validate_draw(draw: DrawCandidate, lottery: Lottery) -> tuple[ValidationIssue, ...]:
    issues = []
    if draw.lottery_slug != lottery.slug:
        return (
            _issue(
                "draw.lottery_mismatch",
                "draw.lottery_slug",
                "concurso pertence a outra loteria",
                draw.lottery_slug,
                lottery.slug,
            ),
        )

    rule = lottery.rule_for(draw.draw_date)
    if rule is None:
        return (
            _issue(
                "draw.rule_not_found",
                "draw.draw_date",
                "não existe uma regra validada para a data",
                draw.draw_date.isoformat(),
            ),
        )
    if draw.rule_version_label != rule.version_label:
        issues.append(
            _issue(
                "draw.rule_mismatch",
                "draw.rule_version_label",
                "versão informada não é a vigente na data",
                draw.rule_version_label,
                rule.version_label,
            )
        )

    actual_series = {series.key: series for series in draw.series}
    defined_series = {series.key: series for series in rule.series}
    for key, definition in defined_series.items():
        if definition.required and key not in actual_series:
            issues.append(
                _issue(
                    "series.missing",
                    f"draw.series.{key}",
                    "série obrigatória ausente",
                )
            )
    for key in actual_series.keys() - defined_series.keys():
        issues.append(
            _issue(
                "series.unknown",
                f"draw.series.{key}",
                "série não definida na regra",
            )
        )

    for series_key in actual_series.keys() & defined_series.keys():
        result = actual_series[series_key]
        definition = defined_series[series_key]
        actual_components = {component.key: component for component in result.components}
        defined_components = {component.key: component for component in definition.components}
        for key in defined_components.keys() - actual_components.keys():
            issues.append(
                _issue(
                    "component.missing",
                    f"draw.series.{series_key}.components.{key}",
                    "componente definido está ausente",
                )
            )
        for key in actual_components.keys() - defined_components.keys():
            issues.append(
                _issue(
                    "component.unknown",
                    f"draw.series.{series_key}.components.{key}",
                    "componente não definido na regra",
                )
            )
        for key in actual_components.keys() & defined_components.keys():
            issues.extend(
                _validate_values(
                    defined_components[key],
                    actual_components[key].values,
                    f"draw.series.{series_key}.components.{key}",
                )
            )

    if draw.status is DrawStatus.PUBLISHED and draw.provenance is None:
        issues.append(
            _issue(
                "draw.missing_provenance",
                "draw.provenance",
                "concurso publicado requer proveniência raw",
            )
        )
    return tuple(issues)


def assert_valid_draw(draw: DrawCandidate, lottery: Lottery) -> None:
    issues = validate_draw(draw, lottery)
    if issues:
        raise DomainValidationError(issues)

