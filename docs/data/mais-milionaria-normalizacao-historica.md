# +Milionária — diagnóstico da normalização histórica

## Fonte e método

Arquivo: `data/raw/mais_milionaria/mais_milionaria_resultados.xlsx`, primeira planilha XLSX, lida somente em memória. Fonte conhecida pelo inventário: download Caixa. URL efetiva e horário original da captura não foram certificados junto ao arquivo. Nenhuma coleta ou pesquisa externa foi realizada.

Hash antes/depois: `69e9050a3528c7e8d8b944ca904044013e00a66648372183ce4dc5e4531a41fa`.

Leitor read-only redefine dimensões, exige campos de concurso, data, bolas, trevos e vinte campos das faixas. Colisões de cabeçalhos e largura incompatível interrompem a leitura. Valores inválidos produzem diagnóstico com campo e posição; colunas adicionais de bolas/trevos são problemas, não descartes silenciosos. Outras informações opcionais ausentes permanecem desconhecidas.

## Resultado

| Métrica | Resultado |
| --- | --- |
| Linhas, candidatos válidos e chaves únicas | 314 |
| Concursos | 1–314 |
| Período | 2022-05-28 a 2025-12-24 |
| Inválidos, duplicados, identidade ausente e lacunas | 0 |
| Números principais | 1.884 valores, entre 1 e 50 |
| Trevos | 628 valores, entre 1 e 6 |
| Cidade de ganhadores ausente | 312 |
| Observação ausente | 314 |
| Comparações da baseline | 8/8 coincidentes |

Todos os concursos têm seis números distintos e ordenados e dois trevos distintos. A ordem dos trevos é preservada como recebida, sem exigir ordenação. Igualdade de um valor entre grupos é legítima e não é duplicidade dentro do grupo.

## Campos e interpretação

| Origem | Destino e semântica |
| --- | --- |
| Concurso / Data Sorteio | Identidade oficial e data civil |
| Bola1–6 | `primary.main` |
| Trevo1–2 | `primary.clovers`, grupo separado |
| Ganhadores / Rateio | Dez faixas, contagem e valor individual BRL |
| Arrecadacao Total | `sales_total` |
| Estimativa Prêmio | `next_estimated_jackpot`, não prêmio pago |
| Acumulado 6 acertos + 2 Trevos | Atributo `rolled_over`; texto original em metadados |
| Cidade / UF | Texto de localização de ganhadores, não local do sorteio |
| Observação | Texto original opcional |

As dez faixas são: 6+2; 6+(0 ou 1); 5+2; 5+(0 ou 1); 4+2; 4+(0 ou 1); 3+2; 3+1; 2+2; 2+1. Cada combinação tem chave explícita `hits_N_clovers_M` ou `hits_N_clovers_0_or_1`. Não inferir rateios separados para faixas agregadas pela fonte.

“Sim” vira booleano verdadeiro e “Não” falso, mantendo o texto original. Ausência não vira falso. Categoria desconhecida é diagnosticada e conservada como evidência. Não existe `rollover_amount` derivado dessa coluna: ela não informa montante.

## Dinheiro e evidências

As doze finalidades monetárias (dez rateios, arrecadação e estimativa) têm 314 valores conhecidos/parseáveis cada. Decimal e BRL são preservados; `known` não equivale a certificação externa.

- Rateio de 6+2: zero em 312 concursos.
- Rateio de 6+(0 ou 1): zero em 293 concursos.
- Rateio de 5+2: zero em 89 concursos.
- Demais rateios, arrecadação e estimativa: nenhum zero neste snapshot.
- Categoria de acumulação: 312 “Sim”, 2 “Não”. O total de ganhadores da faixa 6+2 é 3, distribuídos por dois concursos; não confundir concursos premiados com pessoas únicas.

Evidência de interpretação: concurso 1 contém “Sim” no acumulado, arrecadação R$20.704.332,00 e estimativa R$10.000.000,00. Concurso 158 preserva estimativa R$232.000.000,00. Esses valores não permitem inventar o montante acumulado ou o prêmio principal total.

## Dados ausentes e pesquisa futura

Não estão disponíveis horário, local do sorteio, valor monetário acumulado, prêmio principal total explicitamente identificado e proveniência original completa. A moeda é contextualizada pelo R$ da exportação, e o fuso é metadado da loteria, não horário observado.

Calendário e versões históricas oficiais de regras/faixas precisam de pesquisa. Foram contados 183 sábados, 123 quartas, quatro quintas e quatro sextas; exceções não são rejeitadas por uma agenda semanal presumida. Ausência de cidades coincide em quantidade com concursos sem ganhadores principais, mas não deve virar regra universal sem confirmação.

Concursos com ganhadores de 6+2: 166 (2024-07-24, um ganhador) e 293 (2025-10-11, dois ganhadores), observados diretamente na fonte. Esses registros complementam as evidências das três fixtures de controle.

## Reprodutibilidade

```powershell
python -m app.ingestion.mais_milionaria_history
python -m unittest discover -s tests -p 'test_mais_milionaria_ingestion.py' -v
```

CLI emite apenas diagnóstico no stdout; retorna 0 somente com baseline coincidente, fonte intacta e todas as linhas elegíveis. Candidatos não são gravados. Posição de diagnóstico conta registros não vazios, não número físico da linha Excel. Contadores de números/dinheiro/ganhadores observam candidatos, inclusive problemáticos se existirem, não um dataset publicado.

Diagnóstico [JSON](mais-milionaria-normalizacao-historica.json); hash da interpretação: `c4b0ef8afb0cd20eb76ff0d398176d7abebb1010f2970d07e9661987ad3d9c7b`. Captura local representa reprocessamento, não horário original do download, e seu relógio é excluído do hash.

## Próxima tarefa

SPEC-0008 — Contrato de extração e normalização da Powerball com amostras históricas reais, separando bolas, multiplicador Power Play e Double Play antes de uma auditoria completa.
