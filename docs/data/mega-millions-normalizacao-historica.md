# Mega Millions — diagnóstico da normalização histórica

## Fonte e método

Arquivo: `data/raw/mega_millions/mega_millions_resultados.html`, lido somente em memória. Fonte secundária conhecida: USA Mega. O arquivo não preserva instante original de captura, resposta HTTP ou versão do coletor.

Hash antes/depois: `c154cb21ae6381efe53f9735b5704d148156ba9737266de54e8badbf1d92c35c`.

O normalizador seleciona uma das sete matrizes da SPEC-0012 pela data. Números principais, Mega Ball e Megaplier permanecem semanticamente separados. Datas sem regra não herdam a versão vizinha.

## Resultado

| Métrica | Resultado |
| --- | ---: |
| Linhas, candidatos válidos e chaves únicas | 2.984 |
| Período | 1996-09-06 a 2025-12-23 |
| Inválidos, duplicados e identidade ausente | 0 |
| Números principais | 14.920 valores, entre 1 e 75 conforme a época |
| Mega Balls | 2.984 valores, entre 1 e 52 conforme a época |
| Jackpots anunciados conhecidos | 2.984 |
| Comparações da baseline | 8/8 coincidentes |

Não existe número oficial de concurso no HTML. A data continua sendo identidade canônica provisória, acompanhada do caminho original como referência externa. Nenhuma numeração foi inventada.

## Distribuição por regra

| Versão | Sorteios |
| --- | ---: |
| `mm_1996_50x25` | 172 |
| `mm_1999_50x36` | 348 |
| `mm_2002_52x52` | 324 |
| `mm_2005_56x46` | 869 |
| `mm_2013_75x15` | 420 |
| `mm_2017_70x25` | 776 |
| `mm_2025_70x24` | 75 |

A reconciliação das fronteiras identificou sorteio em 1999-01-12 ainda na matriz 50/25. A matriz 50/36 começa em 1999-01-15. A documentação da SPEC-0012 foi corrigida antes da implementação e a fronteira ganhou teste explícito.

Nenhuma linha excede os limites de sua versão. Lacunas entre o último sorteio antigo e o primeiro novo permanecem sem regra.

## Multiplicadores

| Estado | Sorteios |
| --- | ---: |
| `not_applicable` | 682 |
| `drawn_optional_megaplier` | 2.227 |
| `ticket_assigned_multiplier` | 75 |

No período de Megaplier sorteado há 446 ocorrências de 2x, 745 de 3x, 838 de 4x e 198 de 5x. O atributo é obrigatório somente entre 2003-12-05 e 2025-04-04.

Desde 2025-04-08 o normalizador preserva o estado `ticket_assigned_multiplier`, mas não cria atributo: o fator pertence à aposta individual e não ao resultado. Presença indevida nesse período gera diagnóstico.

## Dinheiro e ausências

Os 2.984 jackpots são parseáveis como `advertised_jackpot`, Decimal e USD. Eles não representam cash value, arrecadação ou pagamento efetivo e ainda não foram conciliados individualmente com fonte oficial.

O snapshot não contém número oficial, horário, local, faixas, ganhadores, arrecadação, cash value ou observações. As contagens de 2.984 ausências de localização/observação indicam campos inexistentes nessa fonte, não consultas oficiais vazias.

## Reprodutibilidade

```powershell
python -m app.ingestion.mega_millions_history
python -m unittest discover -s tests -p 'test_mega_millions*.py' -v
```

A CLI retorna zero apenas com fonte intacta, baseline coincidente e todas as linhas elegíveis. O instante do reprocessamento não altera o diagnóstico.

Diagnóstico [JSON](mega-millions-normalizacao-historica.json); hash da interpretação: `8a22355224a6e54461cbfa267735c57ea3a5dabab7b24fb3cda6e32e8817644c`.

## Próxima tarefa

SPEC-0014 — Definir e testar o contrato de extração do EuroMillions com fixtures históricas reais antes da pesquisa de regras e auditoria completa.
