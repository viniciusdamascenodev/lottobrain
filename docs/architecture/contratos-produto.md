# Contratos de aplicação do LottoBrain

Arquitetura consolidada em 27/10/2026. Contratos de implementação das seis loterias; não são endpoints ou tabelas já implantados. [Visão geral](visao-geral.md) é a referência da etapa 3. A apresentação visual detalhada pertence à etapa 4.

## Interfaces e responsabilidades

| Entrada | Caso de uso | Portas e limite |
|---|---|---|
| Navegador/Next.js | entrar, solicitar acesso, consultar e administrar | HTTP `/api/v1` da mesma origem; sem SQL/fontes externas no navegador |
| FastAPI | verificar sessão/aprovação, validar entrada, executar comando/consulta, traduzir erros | DTOs próprios; nenhuma lógica de loteria ou treino no handler |
| CLI/Actions | selecionar jobs devidos e executar importação/coleta/análise/backup | Mesmo núcleo Python; identidade técnica, parâmetros limitados e evidência durável |
| Adaptador de fonte | adquirir/interpretar um perfil qualificado | HTTP defensivo e normalizador puro; regra numérica do catálogo, sem duplicação |
| Repositórios/storage | gravar/reconstruir agregados e artefatos | SQL e SDK confinados à infraestrutura; raw, revisões e manifestos rastreáveis |

Novos casos de uso compartilham a receita comando→autorização→validação→transação→auditoria. API e worker não chamam scripts legados nem montam SQL a partir do slug. Implementar um registro explícito `(source_key, profile_version) → adaptador` no composition root. Fonte cadastrada sem adaptador suportado permanece rascunho/bloqueada.

## HTTP e autorização

| Grupo / rota planejada | Quem usa | Contrato principal |
|---|---|---|
| `GET /api/v1/auth/start`, `GET /api/v1/auth/callback` | anônimo, durante fluxo de conta | Google/Supabase PKCE, estado de uso único e destino fixo; callback não libera dados |
| `GET /api/v1/me` | autenticado, inclusive pendente | ID/estado próprio, capacidades e situação de MFA; sem catálogo/resultados para pendente |
| `POST /api/v1/auth/logout`, rotas de MFA | sessão de conta | Invalidar sessão/desafio; MFA insuficiente não concede administração |
| `GET /api/v1/lotteries` e `GET /api/v1/lotteries/{slug}` | aprovado | seis modalidades, versões/componentes relevantes e disponibilidade real; campos técnicos internos limitados |
| `GET /api/v1/lotteries/{slug}/draws` e `.../draws/{draw_id}` | aprovado | membros do conjunto aprovado, filtro/data/regra, paginação estável e origem; nunca maior candidato como publicado |
| `GET /api/v1/lotteries/{slug}/freshness` | aprovado | fronteiras confirmada/observada, instante de verificação, atraso, política e próxima tentativa |
| `GET /api/v1/lotteries/{slug}/analyses` e `.../forecasts` | aprovado | resultados calculados vinculados a dataset/receita/modelo; sem treino síncrono ou probabilidade fixa |
| `GET /api/v1/admin/access-requests`; `POST .../{id}/approve` ou `/revoke` | administrador com MFA | versão esperada, motivo e chave idempotente; perfil/sessões/auditoria atômicos |
| `POST /api/v1/admin/datasets/{id}/approve` | administrador com MFA | conjunto validado e versão esperada do ativo; conflito não troca o ponteiro |
| `GET /api/v1/admin/jobs`; `POST /api/v1/admin/jobs` | administrador com MFA | status sanitizado; criação allowlisted retorna `202` e job_id, sem comando shell/SQL ou segredo arbitrário |
| `POST/PATCH /api/v1/admin/lotteries` e `.../{id}/activate` | administrador com MFA | rascunho/configuração versionada; ativação exige regras e perfil qualificados |
| `GET /api/v1/admin/artifacts/{id}/download` | administrador aprovado com MFA | autorização de objeto e transferência privada limitada; sem link público permanente |

Os nomes de rotas são o contrato inicial para geração OpenAPI na implementação. Filtros aceitos: `from`, `to`, `rule_version`, `series`, `dataset_id`, `cursor` e `limit`; aceitar somente combinações aplicáveis. Default de 50 itens, máximo 200; paginação prende dataset/ordem/filtro e não muda de conjunto durante a navegação. Cursor opaco com validação de integridade; dinheiro é string decimal com moeda/território/natureza/estado. Referências de concurso são strings contextualizadas, nunca floats.

Erros: `401` sem sessão válida, `403` acesso/privilégio insuficiente, `404` entidade ausente ou fora do escopo, `409` conflito de versão/idempotência, `422` entrada incompatível, `429` limitação e `503` dependência indisponível. Corpo seguro: `code`, `message`, `correlation_id`, detalhes de campo permitidos e, quando aplicável, `retry_after`. Não enviar stack trace, SQL, token ou resposta externa bruta.

Comando repetido com mesma chave e parâmetros devolve a mesma intenção/resultado; chave reutilizada com parâmetros diferentes gera `409`. POST protegido por CSRF; GET não aprova, ativa nem dispara trabalho. Workflows usam CLI com identidade técnica, não cookie de usuário ou uma rota pública de cron. Rotas administrativas de jobs aceitam tipos configurados, não scripts.

## Resposta de consulta

Envelope mínimo de lista: `lottery`, `dataset_id`, `manifest_hash`, `items`, `next_cursor`, `freshness` e metadados de filtro. Cada concurso informa identidade canônica/referências externas, data local, regra, séries/componentes separados, faixas e fatos financeiros tipados com disponibilidade/origem. Identificadores internos de sessão, papéis SQL e caminhos de credencial nunca entram em DTOs.

`freshness` separa `last_confirmed`, `last_observed`, `verified_at`, `last_attempt_at`, `next_due_at`, `policy_mode` (`hourly` ou `daily`) e estado (`verified`, `awaiting_source`, `late`, `unknown`, `blocked`). Uma fonte recente com série complementar ausente retorna disponibilidade por série; não esconde a lacuna nem faz toda a página parecer atualizada pelo último horário de job.

`quality_state` é independente da atualidade: `validated`, `under_review` ou `superseded`, com referências/motivos seguros e escopo afetado. Divergência relevante pendente marca os dados afetados `under_review`, mantendo consulta histórica com aviso e bloqueando nova previsão/promoção automática que dependa do conflito. Correção aceita cria dataset novo; previsões já emitidas são preservadas e seus vínculos de qualidade podem ser sinalizados. Dado recente não recebe qualidade válida só pela data ou pelo sucesso do job. Esses estados são eventos/projeções, não mutação dos membros/outputs imutáveis.

Sem conjunto aprovado, a modalidade continua navegável com estado `not_ready`/sem dados e explicação; esse estado **não satisfaz** o aceite funcional das seis. Sem análise calculada, devolver estado e motivo de ausência, nunca resultado do protótipo. Dados antigos podem ser consultados com fronteira/atraso visíveis, sem alegação de atualização.

## Frontend e componentes

A etapa 4 foi encerrada em 28/10/2026: [jornadas e contrato de apresentação](../design/etapa-4-experiencia-visual.md), [tokens e componentes](../design/sistema-visual.md), [protótipo local](../design/prototipo/index.html) e [verificação](../design/validacao-etapa-4.md). Esses documentos detalham o desenho abaixo; não mudam os contratos de domínio/segurança nem comprovam a implementação de serviços.

Estrutura: `frontend/src/app` contém rotas/composição; `features/{access,lotteries,analytics,forecasting,admin}` contém comportamento da funcionalidade; `components` contém peças reutilizáveis; `design-system` define tokens/primitivos; `services` contém o cliente HTTP tipado a partir do contrato. Componentes não conhecem ORM, chaves de provedor ou regras numéricas duplicadas.

Rotas de experiência: entrada, solicitação pendente, página autenticada por `/loterias/{slug}`, detalhe de concurso e administração. As seis páginas usam o mesmo layout, com componentes guiados pelo catálogo: `LotteryTabs`, `FreshnessBadge`, `DateRuleFilters`, `DrawTable`, `ComponentNumbers`, `AnalysisCard`, `AnalysisInfo`, `ForecastComparison`, `AccessRequests` e `JobStatus`. Não criar seis dashboards independentes.

Cada componente de dados tem estados de carregamento, vazio, indisponível, erro, atrasado e sucesso. Troca de loteria cancela/ignora resposta obsoleta; URL conserva filtros válidos. `AnalysisInfo` explica finalidade, cálculo, população/período, unidade e limites por teclado/toque, não só hover. Tokens, contrastes, gráficos e composição visual seguem o sistema visual entregue na etapa 4, sem alterar contratos de domínio. SSR privado exige a mesma autorização do fetch e não gera páginas com dados em cache público.

Estado de qualidade `under_review`/`superseded` é mostrado além de atraso e indisponibilidade. A interface não compara como equivalente uma análise atual válida e outra baseada em revisão superada; mantém a identificação de dataset/modelo e o contexto histórico.

## Ciclos de dados, análise e previsão

1. Job devido consulta fonte escolhida, preserva receipt/raw e interpreta com perfil versionado. Validação e reconciliação mantêm idempotência/checkpoint/correções existentes. Aquisição externa não participa de uma transação SQL longa.
2. Revisões elegíveis entram em novo conjunto; conferência, aprovação e ativação seguem a [transação documentada](../database/modelo-logico.md#8-módulos-do-produto-para-a-primeira-versão). Antes disso, o usuário continua vendo o conjunto aprovado anterior e seu estado de atualidade. Baseline e política são aprovadas pelo administrador; a política versionada pode promover acréscimos validados sem conflito. Correção conflitante, perfil/regra não autorizado e falha de cobertura exigem revisão, sem fingir aprovação já concedida. A atualização normal não depende de um clique humano a cada sorteio.
3. Análise usa `dataset_id + parâmetros + versão de cálculo/código/catálogo`. Receita concluída é reaproveitada. Atualizar dataset solicita cálculo novo idempotente e conserva a linhagem do anterior. API apenas consulta resultados preparados; não recalcula todo o histórico por gráfico.
4. Forecasting registra dataset/corte, features, regra, orçamento, método, seed, splits e métricas. Comparar referências aleatória/frequência/janela e modelo supervisionado com validação temporal para cada contrato suportado. Predição deve respeitar quantidades/limites/componentes da modalidade.
5. Previsão emitida conserva horário, horizonte, modelo e entradas imutáveis; avaliação posterior é separada. Backtest histórico com revisões corrigidas não é apresentado como previsão emitida naquela data. Sem horário histórico de publicação qualificado, declarar essa limitação e excluir features que dependam dele; não fabricar disponibilidade passada de financeiros.

O objetivo permanece prever da melhor forma mensurável possível; nenhum método recebe probabilidade/qualidade inventada. Um modelo inferior pode ser mostrado como experimento, com métricas reais; promoção a modelo aprovado tem critério explícito. O núcleo estatístico opera em números principais e especiais separadamente e segmenta mudanças de regras.

## Sequência funcional e prova

| Entrega | Capacidade exigida para as seis loterias |
|---|---|
| SPEC-0033 | conta privada/aprovação e consulta básica real das seis, conjuntos históricos aprovados, perfis SQL/leitura e CI; defasagem mostrada honestamente |
| SPEC-0034 | completar defasagem, adaptar fontes atuais, atualização agendada +1h/D+1 e diagnóstico por modalidade/série |
| SPEC-0035 | gráficos/explicações, métodos preditivos avaliados e catálogo administrativo funcional para as seis |
| SPEC-0036 | jornadas, permissões, operação, backup/restauração e release das seis comprovados |

Cada perfil exige ao menos contrato de fonte real, roundtrip SQL/leitura, regra histórica/fronteira relevante e consulta autorizada. Não encerrar 0033 com uma loteria e cinco abas vazias; não encerrar 0034 só porque seis fontes responderam. Reusar fixtures/manifestos; repetir auditoria integral somente quando alteração/aceite da carga justificar. A etapa 3 entrega estes contratos, não anuncia os testes operacionais futuros como executados.
