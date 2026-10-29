# Powerball — diagnóstico da normalização histórica

## Fonte e método

Arquivo: `data/raw/powerball/powerball_resultados.html`, lido somente em memória. Fonte secundária conhecida: USA Mega. O arquivo não contém instante original de captura nem resposta HTTP preservada.

Hash antes/depois: `12b1197b080bdf06cd8c944a66167732bb73850e8591b163faf985a3744b4238`.

O normalizador seleciona uma das sete matrizes da SPEC-0009 pela data de sorteio. Números principais, Powerball, Power Play e Double Play permanecem separados. Datas fora das vigências documentadas não recebem regra por aproximação.

## Resultado

| Métrica | Resultado |
| --- | ---: |
| Linhas, candidatos válidos e chaves únicas | 3.742 |
| Período | 1992-04-22 a 2025-12-24 |
| Inválidos, duplicados e identidade ausente | 0 |
| Números principais | 18.710 valores, entre 1 e 69 |
| Powerballs principais | 3.742 valores, entre 1 e 45 conforme a época |
| Double Play | 680 sorteios, 3.400 números principais |
| Jackpot anunciado conhecido | 3.742 |
| Comparações da baseline | 8/8 coincidentes |

O HTML não contém número oficial de concurso. A identidade canônica provisória continua sendo a data, e o caminho original permanece como referência externa. Não foi criada uma numeração artificial.

## Distribuição por regra

| Versão | Sorteios |
| --- | ---: |
| `pb_1992_45x45` | 578 |
| `pb_1997_49x42` | 514 |
| `pb_2002_53x42` | 302 |
| `pb_2005_55x42` | 350 |
| `pb_2009_59x39` | 316 |
| `pb_2012_59x35` | 388 |
| `pb_2015_69x26` | 1.294 |

Nenhuma linha excede os limites da versão aplicável. As lacunas de dias entre matrizes não são preenchidas: nelas não há sorteios no snapshot e o domínio deliberadamente não escolhe uma regra.

## Power Play

| Estado semântico | Sorteios |
| --- | ---: |
| Não aplicável, antes do lançamento | 926 |
| Prêmios fixos, sem multiplicador sorteado | 210 |
| Multiplicador observado | 2.606 |

Multiplicadores observados: 1x em 30 linhas, 2x em 1.077, 3x em 717, 4x em 353, 5x em 407 e 10x em 22. O diagnóstico conserva esses valores, mas não certifica ainda a composição histórica do conjunto de multiplicadores ou os valores das faixas.

A ausência é validada pela vigência: antes de 2001 é `not_applicable`; de 2012-01-18 a 2014-01-18 é `fixed_prize_no_multiplier`; nos demais períodos pesquisados o multiplicador é obrigatório. Uma ausência inesperada ou presença fora de vigência gera problema explícito.

## Double Play e jackpot

Os 680 Double Plays começam em 2021-08-23. Cada um contém cinco números de 1–69 e uma Powerball de 1–26 em série adicional. O normalizador exige a série a partir do lançamento e a rejeita antes dele.

Todos os jackpots são parseáveis como `advertised_jackpot`, Decimal e USD. Isso significa valor anunciado, não arrecadação, pagamento efetivo ou `cash_value`. Os 3.742 valores conhecidos não foram verificados individualmente contra a fonte oficial.

## Dados ausentes e limites

O snapshot não fornece número oficial estruturado, horário, local, faixas, ganhadores, arrecadação, cash value ou observações. A localização de ganhadores e observação aparecem ausentes nas 3.742 linhas porque esses campos não existem nessa fonte, não porque tenham sido consultados e retornado vazios.

As regras numéricas possuem evidência oficial majoritária, mas a primeira matriz 45×45 permanece com confiança média. O resultado demonstra consistência interna com as regras pesquisadas; não transforma a fonte secundária em certificação oficial.

## Reprodutibilidade

```powershell
python -m app.ingestion.powerball_history
python -m unittest discover -s tests -p 'test_powerball*.py' -v
```

A CLI emite somente o diagnóstico e retorna zero apenas quando a fonte permanece intacta, a baseline coincide e todas as linhas são elegíveis. Duas capturas locais diferentes geram conteúdo idêntico porque o relógio de processamento não entra no hash.

Diagnóstico [JSON](powerball-normalizacao-historica.json); hash da interpretação: `41afe9224564a803fdd624c07fb65eed4514528f7b8a2ba0701982960520fd83`.

## Próxima tarefa

SPEC-0011 — Definir e testar o contrato de extração da Mega Millions com fixtures históricas reais, antes de pesquisar regras e auditar o histórico completo.
