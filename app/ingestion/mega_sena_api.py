"""Interpretação pura do contrato JSON observado na CAIXA, SPEC-0020."""
from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal

from app.domain import (
    ComponentResult, DrawCandidate, ExternalReference, MonetaryAmount,
    PrizeTierResult, RawProvenance, ResultSeries, ValidationIssue,
    ValueStatus, validate_draw,
)
from app.ingestion.mega_sena import MEGA_SENA, NormalizationResult

SOURCE_KEY = "caixa_mega_sena_json"
ADAPTER_VERSION = "spec-0020-v1"
EXPECTED_FIELDS = frozenset({
    "acumulado", "dataApuracao", "dataProximoConcurso",
    "dezenasSorteadasOrdemSorteio", "exibirDetalhamentoPorCidade", "id",
    "indicadorConcursoEspecial", "listaDezenas", "listaDezenasSegundoSorteio",
    "listaMunicipioUFGanhadores", "listaRateioPremio", "listaResultadoEquipeEsportiva",
    "localSorteio", "nomeMunicipioUFSorteio", "nomeTimeCoracaoMesSorte", "numero",
    "numeroConcursoAnterior", "numeroConcursoFinal_0_5", "numeroConcursoProximo",
    "numeroJogo", "observacao", "premiacaoContingencia", "tipoJogo", "tipoPublicacao",
    "ultimoConcurso", "valorArrecadado", "valorAcumuladoConcurso_0_5",
    "valorAcumuladoConcursoEspecial", "valorAcumuladoProximoConcurso",
    "valorEstimadoProximoConcurso", "valorSaldoReservaGarantidora",
    "valorTotalPremioFaixaUm",
})
MONEY_FIELDS = {
    "valorArrecadado": "sales_total",
    "valorAcumuladoProximoConcurso": "rollover_amount",
    "valorEstimadoProximoConcurso": "next_estimated_jackpot",
    "valorAcumuladoConcursoEspecial": "special_draw_rollover",
    "valorAcumuladoConcurso_0_5": "ending_zero_five_rollover",
}


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"chave JSON duplicada: {key}")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError(f"constante JSON inválida: {value}")


def normalize_response(
    body: bytes, provenance: RawProvenance, *, expected_contest: int | None = None,
) -> NormalizationResult:
    issues = []

    def problem(code, path, message):
        issues.append(ValidationIssue(code, path, message))

    try:
        payload = json.loads(
            body, parse_float=Decimal, parse_constant=_reject_constant,
            object_pairs_hook=_unique_object,
        )
    except (ValueError, UnicodeError, RecursionError):
        problem("source.invalid_json", "response", "JSON inválido ou ambíguo")
        return NormalizationResult(None, tuple(issues), None)
    if not isinstance(payload, dict):
        problem("source.invalid_structure", "response", "resposta deve ser objeto JSON")
        return NormalizationResult(None, tuple(issues), None)
    if set(payload) != EXPECTED_FIELDS:
        problem("source.schema_changed", "response", "campos diferem do contrato observado")
    if payload.get("tipoJogo") != "MEGA_SENA":
        problem("source.wrong_game", "tipoJogo", "modalidade incompatível")
    # Código observado em respostas completas; não se presume semântica dos demais.
    if type(payload.get("tipoPublicacao")) is not int or payload["tipoPublicacao"] != 3:
        problem("source.unverified_publication", "tipoPublicacao", "perfil de publicação ainda não qualificado")
    if payload.get("premiacaoContingencia") is not None:
        problem("source.unverified_contingency", "premiacaoContingencia", "premiação de contingência exige pesquisa")
    if not isinstance(payload.get("listaMunicipioUFGanhadores"), list):
        problem("source.invalid_structure", "listaMunicipioUFGanhadores", "esperada lista de localidades")
    contest = payload.get("numero")
    if type(contest) is not int or contest <= 0:
        problem("source.invalid_identity", "numero", "concurso deve ser inteiro positivo")
        contest = None
    elif expected_contest is not None and contest != expected_contest:
        problem("source.identity_mismatch", "numero", "resposta não corresponde ao concurso solicitado")
    try:
        date_text = payload.get("dataApuracao")
        if not isinstance(date_text, str):
            raise ValueError
        draw_date = datetime.strptime(date_text, "%d/%m/%Y").date()
        if draw_date.strftime("%d/%m/%Y") != date_text:
            raise ValueError
    except ValueError:
        problem("source.invalid_date", "dataApuracao", "data civil inválida")
        draw_date = None
    if draw_date and draw_date > provenance.captured_at.date():
        problem("source.future_result", "dataApuracao", "resultado posterior à captura")

    def numbers(field):
        values = payload.get(field)
        if not isinstance(values, list) or len(values) != 6 or any(
            not isinstance(v, str) or len(v) != 2 or not v.isascii() or not v.isdigit()
            for v in values
        ):
            problem("source.invalid_numbers", field, "esperadas seis dezenas textuais de dois dígitos")
            return ()
        return tuple(int(v) for v in values)

    main = numbers("listaDezenas")
    draw_order = numbers("dezenasSorteadasOrdemSorteio")
    if sorted(main) != sorted(draw_order):
        problem("source.number_mismatch", "dezenasSorteadasOrdemSorteio", "ordem de extração diverge da combinação")
    if payload.get("listaDezenasSegundoSorteio") not in (None, []):
        problem("source.unexpected_series", "listaDezenasSegundoSorteio", "segunda série não prevista")

    def money(value, kind, path):
        if value is None:
            return MonetaryAmount(kind, ValueStatus.UNKNOWN)
        if type(value) not in (int, Decimal):
            problem("source.invalid_money", path, "esperado número decimal não negativo")
            return MonetaryAmount(kind, ValueStatus.UNKNOWN)
        amount = Decimal(value)
        if not amount.is_finite() or amount < 0 or amount > Decimal("1e18") or amount.as_tuple().exponent < -2:
            problem("source.invalid_money", path, "valor fora do envelope decimal operacional seguro")
            return MonetaryAmount(kind, ValueStatus.UNKNOWN)
        return MonetaryAmount(kind, ValueStatus.KNOWN, amount, "BRL", str(value))

    amounts = tuple(money(payload.get(field), kind, field) for field, kind in MONEY_FIELDS.items())
    tiers = []
    raw_tiers = payload.get("listaRateioPremio")
    seen = set()
    if not isinstance(raw_tiers, list):
        raw_tiers = []
    for item in raw_tiers:
        if not isinstance(item, dict) or set(item) != {"faixa", "descricaoFaixa", "numeroDeGanhadores", "valorPremio"}:
            problem("source.invalid_tier", "listaRateioPremio", "estrutura de faixa inválida")
            continue
        number = item["faixa"]
        if type(number) is not int or number not in (1, 2, 3) or number in seen:
            problem("source.invalid_tier", "listaRateioPremio", "faixa desconhecida ou duplicada")
            continue
        seen.add(number)
        if item["descricaoFaixa"] != f"{7-number} acertos":
            problem("source.invalid_tier", "listaRateioPremio", "descrição de faixa incompatível")
        winners = item["numeroDeGanhadores"]
        if type(winners) is not int or winners < 0:
            problem("source.invalid_winners", "listaRateioPremio", "ganhadores devem ser inteiros não negativos")
            winners = None
        prize = money(item["valorPremio"], "paid_per_winner", f"listaRateioPremio.{number}")
        if prize.status is not ValueStatus.KNOWN:
            problem("source.incomplete_tier", "listaRateioPremio", "rateio ainda não disponível")
        tiers.append(PrizeTierResult(
            ("sena", "quina", "quadra")[number-1],
            ValueStatus.KNOWN if winners is not None else ValueStatus.UNKNOWN,
            winners, prize,
        ))
    if seen != {1, 2, 3}:
        problem("source.incomplete_tiers", "listaRateioPremio", "três faixas obrigatórias ainda não disponíveis")
    metadata = []
    for source, target in (
        ("localSorteio", "draw_location"), ("nomeMunicipioUFSorteio", "draw_city"),
        ("observacao", "observation_source_text"),
    ):
        value = payload.get(source)
        if value is not None and not isinstance(value, str):
            problem("source.invalid_text", source, "esperado texto ou null")
        elif value:
            metadata.append((target, " ".join(value.split())))
    if type(payload.get("acumulado")) is not bool:
        problem("source.invalid_rollover", "acumulado", "esperado booleano")
    else:
        metadata.append(("rollover", str(payload["acumulado"]).lower()))
    # Ordem de extração é evidência própria; não se confunde com ordem crescente.
    metadata.append(("draw_order", ",".join(str(v) for v in draw_order)))
    if contest is None or draw_date is None:
        return NormalizationResult(None, tuple(issues), None)
    rule = MEGA_SENA.rule_for(draw_date)
    if rule is None:
        problem("draw.rule_not_found", "dataApuracao", "sem regra para a data")
        return NormalizationResult(None, tuple(issues), None)
    candidate = DrawCandidate(
        lottery_slug="mega_sena", draw_date=draw_date,
        rule_version_label=rule.version_label, official_draw_number=str(contest),
        series=(ResultSeries("primary", (ComponentResult("main", main),)),),
        external_references=(ExternalReference(SOURCE_KEY, "official_draw_number", str(contest)),),
        monetary_amounts=amounts, prize_tiers=tuple(sorted(tiers, key=lambda t: t.tier_key)),
        provenance=provenance, metadata=tuple(metadata),
    )
    issues.extend(validate_draw(candidate, MEGA_SENA))
    return NormalizationResult(candidate, tuple(issues), f"mega_sena:official_draw_number:{contest}")
