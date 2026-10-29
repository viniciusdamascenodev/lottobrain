# SPEC-0004 — Fixtures brutas e normalizador da Mega-Sena

## Estado

Implementada em 2026-09-14.

## Objetivo

Validar o primeiro fluxo vertical de ingestão: ler uma amostra controlada da planilha histórica da Mega-Sena e transformar cada linha em um `DrawCandidate` da SPEC-0003, sem banco de dados e sem modificar a fonte.

## Escopo implementado

- leitor XLSX em modo somente leitura;
- cálculo SHA-256 da fonte;
- fixture com os concursos 1, 2 e 2954;
- normalização de concurso, data e seis números;
- normalização das três faixas de prêmio;
- normalização de acumulado, arrecadação, estimativa e acumulado especial;
- preservação de cidade e observação quando presentes;
- proveniência raw em cada candidato;
- chave canônica determinística por concurso oficial;
- problemas estruturados para valores inválidos;
- testes unitários e teste de contrato com o XLSX real.

## Contrato da fonte

Arquivo atual: `data/raw/mega_sena/mega_sena_resultados.xlsx`.

SHA-256 esperado na implementação desta especificação:

`0e1936e3ac94a35a89c13ef31d705d3fb363239779ad6224b5e41171a3238686`

O leitor:

- abre a primeira planilha com `read_only=True` e `data_only=True`;
- exige cabeçalho `Concurso` após normalização textual;
- não salva nem reexporta o workbook;
- ignora linhas totalmente vazias;
- permite limitar a quantidade lida para testes controlados;
- fecha o workbook mesmo quando ocorre falha.
- ignora a dimensão incorreta `A1:T1` declarada pelo arquivo e recalcula o
  intervalo durante a leitura; sem isso, o modo somente leitura enxerga apenas
  o cabeçalho.

`openpyxl` passa a ser dependência direta porque `pandas.read_excel` também depende de um mecanismo XLSX e o projeto precisa declarar explicitamente o leitor utilizado.

## Mapeamento

| Origem | Destino canônico |
|---|---|
| `Concurso` | `official_draw_number` e referência externa |
| `Data do Sorteio` | `draw_date` |
| `Bola1` a `Bola6` | série `primary`, componente `main` |
| `Ganhadores N acertos` | `PrizeTierResult.winners` |
| `Rateio N acertos` | `paid_per_winner`, BRL |
| `Acumulado 6 acertos` | `rollover_amount`, BRL |
| `Arrecadação Total` | `sales_total`, BRL |
| `Estimativa prêmio` | `next_estimated_jackpot`, BRL |
| `Acumulado Sorteio Especial Mega da Virada` | `special_draw_rollover`, BRL |
| `Cidade / UF` | metadado original, quando informado |
| `Observação` | metadado original, quando informado |

Os cabeçalhos são comparados por uma chave ASCII normalizada. Isso tolera diferenças de acentuação observadas no arquivo sem depender da posição da coluna.

## Identidade e idempotência

A chave desta fonte é:

`mega_sena:official_draw_number:<concurso>`

Normalizar a mesma linha com a mesma proveniência produz o mesmo candidato, os mesmos problemas e a mesma chave. A especificação não persiste nem reconcilia registros; apenas prova a identidade determinística que uma camada futura poderá utilizar.

## Política de ausência e erro

- Concurso ou data ausente/inválida impede a criação do candidato.
- Bola ausente é omitida do componente e produz problema; a validação também acusa cardinalidade.
- Bola fora do intervalo permanece no candidato e produz `component.out_of_range`.
- Valor financeiro vazio vira `UNKNOWN`, não zero.
- Valor financeiro inválido preserva `source_text`, vira `UNKNOWN` e produz `source.invalid_money`.
- Zero válido permanece `KNOWN` com `Decimal("0.00")`.
- Cidade vazia não é erro, pois pode ser não aplicável quando não há ganhador principal.
- Nenhum fallback ou correção automática é aplicado.

## Regra utilizada

Foi criada uma definição `baseline_1996`, válida a partir de 1996-03-11, com seis números distintos e ordenados de 1 a 60. Ela descreve o que foi comprovado pelo arquivo da SPEC-0001 e não substitui pesquisa documental oficial.

## Fora do escopo

- leitura ou normalização das outras cinco loterias;
- importação completa para banco;
- escrita de Parquet ou JSON processado;
- atualização dos relatórios atuais;
- download de dados;
- reconciliação entre múltiplas fontes;
- calendário e detecção de concursos ausentes;
- API, interface ou scheduler.

## Critérios de aceitação

- [x] O XLSX real é aberto somente para leitura.
- [x] Hash antes e depois da leitura permanece igual.
- [x] Três linhas reais estão disponíveis como fixture estável.
- [x] Concurso, data e números são normalizados.
- [x] Prêmios usam `Decimal` e BRL.
- [x] Zero e ausência são distintos.
- [x] Erros geram `ValidationIssue` sem alterar a entrada.
- [x] A mesma entrada produz a mesma chave e resultado.
- [x] O candidato aponta para proveniência raw.
- [x] Nenhum banco, coletor ou relatório foi alterado.

## Próxima tarefa recomendada

**SPEC-0005 — Normalização histórica completa da Mega-Sena em memória.**

Ela deverá percorrer as 2.954 linhas, produzir um relatório reproduzível de válidos e problemas, verificar unicidade das chaves e comparar totais com a linha de base da SPEC-0001. Ainda não deverá criar banco de dados. Esse passo comprova o normalizador em toda a série antes de reutilizar padrões nas outras fontes.
