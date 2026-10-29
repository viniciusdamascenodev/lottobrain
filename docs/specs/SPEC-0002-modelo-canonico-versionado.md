# SPEC-0002 — Modelo canônico versionado para loterias e concursos

## Estado

Concluída em 2026-09-14 como especificação de domínio. A implementação permanece fora do escopo.

## Contexto

A SPEC-0001 demonstrou que o LottoBrain precisa representar concursos com estruturas diferentes:

- Mega-Sena: 6 números;
- Lotofácil: 15 números;
- +Milionária: 6 números e 2 trevos;
- Powerball: 5 números e 1 Powerball, com multiplicador e Double Play em parte do histórico;
- Mega Millions: 5 números e 1 Mega Ball, com multiplicador em parte do histórico;
- EuroMillions: 5 números e 2 estrelas.

Ela também mostrou que os limites mudam ao longo do tempo, os identificadores externos não são uniformes e o significado dos valores financeiros depende da fonte.

## Objetivo

Definir um contrato conceitual único, extensível e versionado para representar loterias, regras, concursos, resultados, premiações e proveniência sem reduzir todas as modalidades a seis números.

## Fora do escopo

- criar tabelas, migrations ou banco de dados;
- escolher ORM ou biblioteca de validação;
- implementar parsers, coletores ou importadores;
- pesquisar e preencher todas as regras históricas;
- definir telas de cadastro e administração;
- alterar o pipeline atual;
- criar API, autenticação, estatísticas ou modelos preditivos.

## Decisões

### D-001 — Identidade interna independente da fonte

Toda entidade persistente terá identificador interno opaco. Identificadores vindos das fontes serão preservados como referências externas, nunca usados isoladamente como identidade universal.

**Motivo:** `id` e `draw_id` do EuroMillions não têm semântica confirmada, e os HTMLs americanos não possuem número de concurso estruturado.

### D-002 — Regras com período de vigência

Cada loteria terá uma ou mais versões de regra com início inclusivo e fim exclusivo. Um concurso publicado deverá apontar para exatamente uma versão compatível com sua data.

**Motivo:** limites atuais classificariam parte do histórico americano como inválido.

### D-003 — Resultado composto por grupos tipados

Uma versão de regra define grupos como `main`, `stars`, `trevos`, `powerball` ou `mega_ball`. Cada grupo informa tipo do valor, quantidade, limites, unicidade e significado da ordem.

**Motivo:** números principais e especiais não são intercambiáveis e precisam permanecer semanticamente separados.

### D-004 — Sorteios adicionais são resultados relacionados

Double Play ou outro sorteio adicional não será anexado à lista do resultado principal. Será representado como uma série de resultado distinta, ligada ao mesmo evento/concurso quando aplicável.

### D-005 — Multiplicadores não são bolas

Power Play, Megaplier e propriedades semelhantes serão atributos tipados do resultado ou do concurso, nunca valores de um grupo de bolas.

### D-006 — Dinheiro sempre possui moeda e finalidade

Todo montante normalizado terá valor decimal, código ISO 4217 e tipo semântico, por exemplo `advertised_jackpot`, `paid_per_winner`, `sales_total`, `rollover_amount` ou `next_estimated_jackpot`.

### D-007 — Raw é evidência; canonical é interpretação

O registro canônico deve apontar para o artefato bruto e para a execução que produziu a interpretação. Correções não podem sobrescrever a evidência bruta.

### D-008 — Ausência possui semântica

O domínio deverá distinguir ao menos:

- valor conhecido, incluindo zero;
- desconhecido/não informado;
- não aplicável;
- rejeitado por validação.

Não será criado número ou prêmio fictício para preencher ausência.

## Modelo conceitual

O detalhamento de entidades, campos e relações está em [`docs/data/modelo-canonico.md`](../data/modelo-canonico.md).

```text
Lottery
 ├── LotteryRuleVersion
 │    ├── ResultSeriesDefinition
 │    │    └── ComponentDefinition
 │    └── PrizeTierDefinition
 ├── ScheduleVersion
 ├── DataSource
 │    └── ExternalReference
 └── Draw
      ├── DrawRevision
      │    ├── ResultSeries
      │    │    ├── ComponentValue
      │    │    └── ResultAttribute
      │    ├── PrizeTierResult
      │    ├── MonetaryAmount
      │    └── ValidationIssue
      └── IngestionRun ── RawArtifact
```

## Identidade e idempotência

### Chaves internas

Identificadores internos não carregam significado de negócio e não mudam quando uma fonte corrige seus próprios IDs.

### Reconciliação de concursos

A normalização deverá procurar correspondência nesta ordem:

1. referência externa já conhecida para a mesma fonte;
2. número oficial do concurso dentro da loteria, quando a semântica estiver confirmada;
3. chave provisória formada por loteria, data local, série principal e origem;
4. ausência de correspondência: criar candidato em validação, sem publicação automática.

Uma chave provisória não deverá ser promovida silenciosamente a identificador oficial.

### Revisões

Quando uma fonte alterar um resultado já conhecido:

- o artefato novo será preservado;
- uma nova revisão será criada;
- a diferença será registrada;
- a revisão anterior continuará auditável;
- publicação automática dependerá das regras de confiança e validação futuras.

## Invariantes

### Loteria e regra

1. O `slug` da loteria é único e estável.
2. Períodos de versões de regra da mesma loteria não podem se sobrepor.
3. Toda regra possui ao menos uma série de resultado e um componente.
4. Quantidade mínima não pode ser maior que a máxima.
5. Limite inferior não pode ser maior que o superior.
6. Uma loteria arquivada mantém seu histórico consultável.

### Concurso

1. A data local é obrigatória; horário e timezone podem estar desconhecidos até confirmação.
2. Um concurso publicado aponta para regra vigente na data.
3. Zero é valor válido e não equivale a ausência.
4. Um resultado principal validado possui exatamente a cardinalidade definida em sua regra.
5. Valores respeitam tipo, limites e unicidade do componente.
6. A ordenação capturada da fonte pode ser preservada; a ordenação para exibição ou análise é derivada.
7. Componentes especiais não entram na coleção de números principais.
8. Um concurso rejeitado ou em quarentena não alimenta análises públicas.

### Proveniência

1. Todo dado normalizado aponta para uma execução e um artefato bruto.
2. Todo artefato possui hash, tamanho, formato e instante de captura.
3. Uma mesma execução pode interpretar vários concursos, mas não alterar o raw.
4. Toda referência externa é única dentro da combinação fonte, namespace e valor.
5. Falha de parsing ou validação deve ser explícita e consultável.

### Financeiro

1. Montante publicado requer moeda conhecida.
2. Valores são decimais, não ponto flutuante.
3. Tipo financeiro é obrigatório.
4. Valor por ganhador, total da faixa e jackpot são conceitos diferentes.

## Estados mínimos

### Loteria

`draft → validating → active → suspended → archived`

- `draft`: configuração incompleta;
- `validating`: fonte e regras em homologação;
- `active`: habilitada para coleta/publicação;
- `suspended`: preserva histórico, mas interrompe operação;
- `archived`: encerrada para operação e mantida para consulta.

### Concurso/revisão

`candidate → validated → published`

Saídas excepcionais: `quarantined`, `rejected` e `superseded`.

Estados operacionais completos serão especificados junto à ingestão; estes são apenas os necessários ao domínio.

## Mapeamento das seis loterias

| Loteria | Série | Componentes | Atributos conhecidos | Observação |
|---|---|---|---|---|
| Mega-Sena | principal | `main`: 6 inteiros | acumulado, arrecadação, estimativa | Sem componente especial |
| Lotofácil | principal | `main`: 15 inteiros | acumulado, arrecadação, estimativa | Cinco faixas observadas |
| +Milionária | principal | `main`: 6; `trevos`: 2 | acumulou, arrecadação, estimativa | Faixas combinam números e trevos |
| Powerball | principal | `main`: 5; `powerball`: 1 | jackpot, Power Play | Double Play vira série adicional |
| Mega Millions | principal | `main`: 5; `mega_ball`: 1 | jackpot, Megaplier | Limites variam historicamente |
| EuroMillions | principal | `main`: 5; `stars`: 2 | prêmio, houve ganhador | Moeda e IDs ainda não confirmados |

Os limites numéricos exatos por período não são declarados nesta especificação porque exigem pesquisa externa e validação documental.

## Cadastro futuro de loterias: fronteira do domínio

O modelo permite cadastrar metadados, estados, regras, componentes, calendário e fontes. Contudo, cadastrar uma loteria não implica que qualquer fonte arbitrária possa ser compreendida sem código.

Itens potencialmente configuráveis:

- nome, slug, jurisdição, timezone e moeda padrão;
- período de vigência e grupos do sorteio;
- cardinalidades, tipos, limites e unicidade;
- calendário esperado;
- fonte, formato e credenciais referenciadas;
- estados de homologação e operação.

Itens que podem exigir adaptador testado:

- autenticação específica da fonte;
- paginação não padronizada;
- scraping de HTML;
- mapeamento de planilhas instáveis;
- interpretação de regras ou premiações próprias;
- tratamento de correções e indisponibilidade.

Uma nova loteria somente poderá ser ativada após possuir regra vigente, fonte homologada, amostra bruta, normalização validada e critérios mínimos de qualidade. O fluxo administrativo detalhado fica para uma especificação futura.

## Casos de aceitação conceituais

1. Representar um concurso da Lotofácil com 15 números sem criar colunas `n1...n15` no conceito central.
2. Representar +Milionária mantendo trevos separados dos seis números.
3. Representar Powerball principal e Double Play sem concatenar suas bolas.
4. Representar multiplicador sem tratá-lo como número sorteado.
5. Associar dois concursos históricos da mesma loteria a versões diferentes de regra.
6. Preservar `0` ganhadores como valor conhecido.
7. Preservar um prêmio sem moeda como pendência e impedir sua publicação financeira.
8. Conciliar um novo registro por referência externa sem duplicar o concurso.
9. Registrar correção de uma fonte como nova revisão, mantendo a anterior.
10. Colocar em quarentena um resultado que não atende à regra vigente.
11. Manter consultável o histórico de uma loteria arquivada.
12. Cadastrar uma loteria em rascunho sem permitir coleta ou publicação.

## Critérios de conclusão

- [x] As seis loterias cabem no modelo sem estrutura fixa de seis números.
- [x] Números principais e elementos especiais permanecem separados.
- [x] Mudanças históricas de regras são representáveis.
- [x] Identificadores internos e externos têm papéis distintos.
- [x] Raw, execução, revisão e validação são rastreáveis.
- [x] Prêmios incluem moeda e tipo semântico.
- [x] Zero, ausência e não aplicabilidade são distintos.
- [x] Cadastro não equivale a ativação automática.
- [x] Limites entre configuração e código foram registrados.
- [x] Nenhum código de produção, banco ou parser foi criado.

## Questões abertas

1. Qual biblioteca representará o contrato em Python: dataclasses, Pydantic ou outra?
2. UUIDv7 será adotado para IDs internos ou a escolha ficará com a camada de persistência?
3. Resultados financeiros incompletos serão armazenados em estado pendente ou somente no raw?
4. Qual granularidade de revisão será necessária para concursos e premiações?
5. Como expressar regras complexas de faixas sem criar uma linguagem excessivamente genérica?
6. Quais fontes serão consideradas autoritativas em caso de divergência?
7. Quais regras históricas serão pesquisadas antes da primeira importação?

## Próxima tarefa recomendada

**SPEC-0003 — Contratos tipados e validação do domínio em Python.**

Ela deverá implementar somente os modelos de domínio e validadores necessários para materializar esta especificação, acompanhados de fixtures representativas das seis loterias e testes unitários. Banco, ORM, coleta e importação completa deverão continuar fora do escopo dessa tarefa.

