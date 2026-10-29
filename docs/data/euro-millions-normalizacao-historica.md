# EuroMillions — diagnóstico da normalização histórica

## Fonte e método

Arquivo: `data/raw/euro_millions/euro_millions_resultados.json`, lido somente em memória. A fonte secundária é a API Pedro Mealha, que raspou quadros de `euro-millions.com`.

Hash antes/depois: `e4e7f97102c868569e33d54e34e258671cfca98f6872cf21fc0f86b171e57914`.

O normalizador seleciona uma das três matrizes da SPEC-0015 pela data. Números e estrelas permanecem componentes separados. Dias sem sorteio entre versões não herdam a regra vizinha.

## Resultado

| Métrica | Resultado |
| --- | ---: |
| Linhas, candidatos válidos e chaves únicas | 1.906 |
| Período | 2004-02-13 a 2025-12-26 |
| Inválidos, duplicados e identidade ausente | 0 |
| Números principais | 9.530 valores, entre 1 e 50 |
| Estrelas | 3.812 valores, entre 1 e 12 conforme a época |
| Valores financeiros conhecidos | 1.897 |
| Zeros financeiros preservados como desconhecidos | 9 |
| Comparações da baseline | 8/8 coincidentes |

Não existe número oficial de concurso no JSON. A data continua sendo identidade canônica provisória. `source_id` e `draw_id` permanecem referências externas com namespace; nenhum foi promovido.

## Distribuição por regra

| Versão | Sorteios |
| --- | ---: |
| `em_2004_50x9` | 378 |
| `em_2011_50x11` | 562 |
| `em_2016_50x12` | 966 |

Todas as linhas respeitam os limites da versão aplicável. Testes de mutação demonstram que estrela 10 é rejeitada em 2004, estrela 12 é rejeitada na versão de 2011 e aceita desde 2016.

As lacunas 2011-05-07–2011-05-09 e 2016-09-24–2016-09-26 permanecem sem regra. Elas correspondem a dias entre o último sorteio antigo e o primeiro novo.

## Vencedor e dinheiro

O atributo foi renomeado para `has_jackpot_winner`, refletindo o parser da fonte: verdadeiro somente quando existe ganhador na faixa 5+2. Há 440 valores verdadeiros e 1.466 falsos.

O valor positivo é normalizado como `top_tier_prize_per_winner`, em EUR, com escopo `top_tier_5_plus_2_per_winner` e jurisdição de origem `PT_or_ES`. Isso registra a semântica pesquisada sem apresentá-la como certificação oficial.

Nove linhas possuem zero. Elas ficam com `ValueStatus.UNKNOWN`, valor normalizado ausente e texto de origem preservado. Zero, nesse contexto, significa falha/ausência da informação financeira, não pagamento legítimo de EUR 0.

O relatório não contém faixas completas, quantidade de ganhadores, jackpot anunciado, arrecadação ou dados por país. Esses fatos não podem ser reconstruídos do endpoint legado.

## Identificadores

`draw_id` possui 1.906 valores únicos e segue a convenção privada ordinal anual + ano. `source_id` possui 1.906 valores entre 1 e 4.058, com 2.152 lacunas. A descontinuidade não afeta a identidade por data nem é tratada como ausência de concursos.

## Reprodutibilidade

```powershell
python -m app.ingestion.euro_millions_history
python -m unittest discover -s tests -p 'test_euro_millions*.py' -v
```

A CLI retorna zero apenas quando fonte, baseline e elegibilidade integral coincidem. O instante do reprocessamento não altera o diagnóstico.

Diagnóstico [JSON](euro-millions-normalizacao-historica.json); hash da interpretação: `2b1048a885a12d704be8b6768c1ff9ea4bc6fbe0762785508fe847c0e358358d`.

## Próxima tarefa

SPEC-0017 — Consolidar o estado dos seis históricos e definir o contrato do catálogo configurável de loterias, sem implementar persistência ou cadastro administrativo.
