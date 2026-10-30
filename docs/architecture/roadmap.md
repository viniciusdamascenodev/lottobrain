# Mapa de evolução arquitetural

## Posição atual em 29/10/2026

**Etapa 5 concluída e integrada à `main`:** [ambientes, dependências resolvidas, testes e CI](../engineering/etapa-5-desenvolvimento-ci.md), como fundação da SPEC-0033. CI real aprovado com 401 testes Python, 137 PostgreSQL, frontend e auditorias; `main` protegida por PR/Quality gate. [PR #1](https://github.com/viniciusdamascenodev/lottobrain/pull/1) integrada em 29/10/2026, commit `fd2088e`; [CI após o merge aprovado](https://github.com/viniciusdamascenodev/lottobrain/actions/runs/40964245312). Fechamento documental registrado, sem pendência de aceite desta etapa. Não houve deploy. A fundação HTTP recusa os dados e o frontend é somente um shell, preservando o protótipo visual da etapa 4.

**Etapa 6 em execução:** [persistência das seis loterias](../engineering/etapa-6-persistencia.md), com bootstrap operacional, gravação/leitura comum, conjuntos aprovados e papéis separados. Nova migration 0033_01; [CI aprovado](https://github.com/viniciusdamascenodev/lottobrain/actions/runs/40975784677) com 413 testes comuns e 162 PostgreSQL, incluindo 25 novos casos e 45 vetores reais/20 regras. A instalação em Supabase depende do projeto ainda não disponibilizado; a etapa não recebe aceite integral por testes em cluster descartável. Carga histórica integral, autenticação e atualização automática não foram iniciadas neste recorte.

**Etapa 4 concluída:** [experiência visual](../design/etapa-4-experiencia-visual.md), [sistema visual](../design/sistema-visual.md) e [protótipo navegável](../design/prototipo/index.html) para computador/celular, seis loterias e administração. A [validação](../design/validacao-etapa-4.md) registra dados reais do recorte, comportamento, estados, teclado e limites. São 180 registros de referência; autenticação, permissões e operações administrativas são demonstrações locais, sem implantação ou ativação operacional.

Próxima capacidade funcional continua a **SPEC-0033**, com acesso privado e consulta real das seis; sua fundação da etapa 5 está validada e integrada à `main`. O recorte atual da etapa 6 completa a persistência dessa capacidade; os próximos incrementos permanecem fora da execução autorizada. Reaproveitar o desenho, os textos e os cenários; implementar os componentes e serviços previstos na arquitetura. SPECs 0034–0036 permanecem planejadas. As fotografias datadas abaixo conservam seu contexto histórico.

## Decisão vigente em 27/10/2026

Etapas 2 e 3 encerradas em seus escopos de dados e arquitetura. [Arquitetura consolidada](visao-geral.md), [contratos do produto](contratos-produto.md) e [ADR-0004](decisions/ADR-0004-produto-privado-seis-loterias.md) incorporam conteúdo privado, cadastro aprovado pelo proprietário e atualização +1h/D+1 ou modo diário declarado. A primeira entrega funcional planejada passa a consultar as seis loterias; etapas seguintes completam atualização, análises e operação. As seções datadas abaixo conservam evidência histórica, sem substituir essas decisões.

## Ordem das próximas fases

| Etapa | Objetivo | Saída verificável |
|---|---|---|
| SPEC-0020–0022 | primeiro fluxo incremental Mega-Sena | coleta idempotente, raw e reconciliação |
| SPEC-0023–0026 | base de persistência e qualificação | modelo, migrations, writer JSON Mega-Sena e mapeamentos históricos, sem carga integral |
| SPEC-0027 | piloto histórico Mega-Sena | ponte XLSX/JSON, roundtrip SQL, idempotência e retomada com poucas linhas |
| SPEC-0028 | interoperabilidade da ingestão Mega-Sena | ponte integrada explicitamente ao fluxo incremental, preservando revisões e continuidade |
| SPEC-0029 | carga Mega-Sena em ambiente controlado | concluída: 2.954 registros importados/auditados em PostgreSQL descartável, com retomada e sobreposição JSON preservada |
| SPEC-0030 | baseline auditada e início seguro da sincronização Mega-Sena | concluída: baseline XLSX loaded e checkpoint JSON por aprovação explícita, em banco descartável |
| SPEC-0031 | orquestração SQL da sincronização limitada Mega-Sena | concluída: descoberta, avanço contíguo/revisão, orçamento e recuperação sobre checkpoint aprovado em banco descartável |
| SPEC-0032 | auditoria somente leitura da sincronização PostgreSQL Mega-Sena | concluída: snapshot consistente, diagnóstico relacional/bytes e recomendações sem reparo automático |
| SPEC-0033 (em execução: fundação validada) | plataforma privada e consulta das seis | acesso, conjuntos históricos reais aprovados, perfis SQL/leitura, API/páginas e CI |
| SPEC-0034 (planejada) | seis loterias atualizadas e agendamento | perfis adicionais, carga/cobertura atual, jobs recorrentes e diagnóstico de atualidade na interface |
| SPEC-0035 (planejada) | painel analítico, previsões e catálogo | seis abas, gráficos/explicações, métodos iniciais avaliados e cadastro administrativo funcional |
| SPEC-0036 (planejada) | validação operacional e publicação | jornadas, regressão, acesso, alertas, restauração/rollback e release online comprovados |
| Após a primeira versão | ampliação por evidência de uso | laboratório maior de modelos, refinamentos, novas integrações e otimizações justificadas |

O planejamento foi reorganizado após a SPEC-0032 para uma meta de quatro dias, até 30/10/2026, sem tratar qualificação como carga realizada nem reduzir garantias essenciais. Cada SPEC passa a encerrar uma capacidade funcional completa, com tamanho proporcional ao risco, em vez de fracionar separadamente cada camada. CI, segurança e implantação começam na SPEC-0033. A SPEC-0033 está em execução na fundação de engenharia; sua capacidade funcional ainda não foi aceita. As SPECs 0034–0036 permanecem planejadas.

O [plano de entrega em quatro dias](../engineering/plano-entrega-quatro-dias.md) é a referência única para prazo, escopo obrigatório, decisões de hospedagem, dependências, redução de retrabalho e método de execução. A meta depende de acesso aos serviços e às seis fontes; bloqueio essencial impede declarar a versão completa.

Na revisão arquitetural de 27/10, o usuário manteve acesso inteiramente privado, aprovação pessoal e custo inicial zero e alterou a preferência de atualização para uma hora ou um dia após o sorteio. A composição escolhida é Vercel, Supabase e Actions, com Google/Supabase Auth e sem SMTP próprio. Não há implantação comprovada; a meta original de 30/10 não foi reiniciada, e a ampliação da primeira entrega aumenta seu risco.

## Posição em 26/10/2026

SPECs 0020–0022: coleta incremental e auditoria local Mega-Sena. SPEC-0023: modelo lógico/contrato. SPEC-0024: primeiras migrations e integridade PostgreSQL. SPEC-0025: escrita transacional JSON Mega-Sena opt-in, com repositórios, UoW, idempotência e concorrência comprovadas; sem banco operacional/carga histórica/publicação.

A SPEC-0026 qualificou **15.471 registros, seis históricos e 20 regras**, com 45 vetores reais e comparação Mega-Sena XLSX/JSON. Nenhuma carga SQL foi feita. O writer atual permanece específico do JSON Mega-Sena; contratos diferentes não são reconciliados comparando hashes diretamente.

A SPEC-0027 comprovou a ponte em PostgreSQL descartável: linhas XLSX 1/2/2954, JSON 2954, apoio sem perda de enriquecimento, nova revisão quando apropriado, quarentena de divergência e retomada por manifesto/bytes persistidos. Nenhuma carga integral, baseline materializada ou publicação. [Operação/evidências do piloto](../engineering/piloto-importacao-mega-sena.md).

A SPEC-0028 integra explicitamente a ponte ao fluxo incremental: JSON pode enriquecer head histórico; divergência entre contratos fica em quarentena sem avanço; correções JSON e replay legado permanecem. Locks, leases e cursor atômico foram incluídos na prova, sem carga integral ou banco operacional. [Política e evidências](../engineering/ponte-ingestao-incremental.md).

A SPEC-0029 comprovou a carga integral dos **2.954 concursos Mega-Sena (1–2954, até 20/12/2025)** em PostgreSQL descartável. Interrupção após 100 commits, retomada, replay, cobertura relacional e JSON preexistente foram verificados. A revisão separou auditoria histórica da autorização atual da fonte e estado terminal de qualidade atual. São 312 testes distintos aprovados, arquivos protegidos intactos e clusters desligados. [Operação e evidências](../engineering/importacao-completa-mega-sena.md). Não há banco operacional, atualização até hoje, baseline promovida ou publicação.

A SPEC-0030 registrou a aprovação como conceito explícito: nova baseline histórica loaded, referência anterior preservada, vínculo auditado entre fontes e checkpoint JSON iniciado em 2954. Concorrência, commit ambíguo, rollback e passagem real a 2955 foram comprovados sem GET novo, com papel separado de bootstrap e 334 testes distintos aprovados. [Operação/evidências](../engineering/baseline-sincronizacao-mega-sena.md). Nenhum ambiente operacional foi ativado.

A SPEC-0031 comprovou lotes SQL limitados de descoberta, avanço contíguo e revisão usando a baseline aprovada. Receipts são reutilizados, operações têm evidência transacional e confirmações perdidas não justificam repetir HTTP. Orçamento, espaçamento, cooldown, concorrência e fencing no COMMIT foram verificados, com 375 testes distintos aprovados e os 76 arquivos anteriores protegidos intactos. [Operação/evidências](../engineering/sincronizacao-sql-mega-sena.md). Sem GET externo, agendamento ou banco operacional.

A SPEC-0032 entregou auditoria somente leitura com snapshot consistente, confronto do ledger/steps e verificação de conteúdo relacional/bytes. Captura inconclusiva, receipt desacoplado, execução interrompida, cooldown e inconsistência são diferenciados sem reparo automático. Passaram 292 testes comuns e 19 do recorte novo (13 PostgreSQL reais e seis dublês); os 79 arquivos anteriores protegidos ficaram intactos. [Operação/evidências](../engineering/auditoria-sincronizacao-sql-mega-sena.md). A aprovação histórica é referenciada/verificada, sem alegar reauditoria integral pelo novo auditor. Sem coleta externa ou ativação operacional.

**Próxima entrega de implementação: [SPEC-0033 — Plataforma privada e consulta das seis](../specs/SPEC-0033-primeiro-fluxo-online-mega-sena.md).** A arquitetura foi consolidada e as fontes foram qualificadas; a etapa 4 prepara a experiência visual antes da implementação das telas. Provar infraestrutura/cotas e implementar os perfis necessários, sem repetir o inventário. Conclusões 0001–0032 são preservadas como histórico; a primeira entrega funcional agora exige seis modalidades, não somente Mega-Sena.

## Verificação atual de fontes em 27/10/2026

A descoberta/qualificação técnica básica da etapa 2 foi encerrada para o resultado principal das seis loterias: JSON CAIXA, CSV Texas e ZIP/CSV FDJ responderam e tiveram amostras recentes e de sobreposição conferidas. Foram 62 verificações exploratórias e 20 testes offline, sem mudança em coletores, raws anteriores, catálogo ou cobertura operacional. [Contratos, fronteiras, evidência e condições](../data/verificacao-fontes-atuais-2026-10-27.md). Calendário extraordinário, transporte Double Play, financeiros adicionais e ativação recorrente continuam pendências delimitadas; não são certificados pela existência de uma resposta atual. A descoberta inicial da SPEC-0033 aproveita esta entrega, sem repetir o inventário.

## Fechamento complementar da etapa 2

Em 27/10/2026 foi concluída a descoberta/qualificação das seis loterias, com [relatório único de fechamento](../data/fechamento-etapa-2.md), matriz de campos, exceções oficiais de calendário, continuidade recente e políticas publicadas das fontes. São 756 registros posteriores às fronteiras dos arquivos originais nos snapshots, sem importação operacional. Passaram 43 testes offline do recorte de fontes. O relatório anterior permanece preservado como fotografia da primeira verificação.

Esse fechamento é a fotografia complementar anterior. As decisões vigentes de fontes estão no encerramento da etapa 2 e as de produto/implantação na etapa 3: consulta básica das seis na 0033, atualização recorrente na 0034. O contrato JSON novo exige adaptação; a restrição concreta Double Play/Colorado continua explícita. Não há nova SPEC de inventário nem bloqueio genérico CAIXA para reabrir.

## Gates de qualidade

### Antes do banco

- primeiro fluxo incremental comprovado;
- identidade e revisão definidas;
- raw imutável e hash verificável.

### Antes da API

- migrações reproduzíveis;
- repositórios testados;
- conjunto efetivamente exposto reconciliado/aprovado e identificado, com fronteira e atualidade visíveis;
- contratos de erro e paginação.

### Antes do frontend autenticado

- modelo de ameaças;
- sessões, CSRF e autorização testados;
- auditoria administrativa.

### Antes de publicar previsões

- snapshot temporal versionado;
- baseline aleatório;
- backtest walk-forward;
- métricas e limitações documentadas;
- previsão emitida antes do sorteio preservada sem alteração.

### Antes de produção

- CI obrigatório;
- staging e smoke tests;
- TLS e segredos gerenciados;
- backup restaurado em teste;
- alertas e runbooks;
- acessibilidade das jornadas principais;
- política de privacidade e jogo responsável.

## O que não será antecipado

- microsserviços;
- Kubernetes;
- broker distribuído;
- cache Redis;
- streaming de eventos;
- lakehouse;
- GPU sempre ligada;
- múltiplos bancos por módulo.

Essas tecnologias poderão ser adotadas quando uma métrica, requisito ou falha concreta justificar o custo.
