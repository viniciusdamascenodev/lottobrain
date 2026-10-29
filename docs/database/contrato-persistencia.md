# Contrato de persistência e transações

## Escopo do contrato

Complementa o [modelo lógico](modelo-logico.md). Este documento especifica comportamento, não implementa repositório, ORM ou SQL. Domínio continua independente do PostgreSQL; casos de uso controlam transações por portas explícitas.

Implementação posterior: a [SPEC-0025](../specs/SPEC-0025-persistencia-transacional-mega-sena.md) materializa T1–T3/continuidade Mega-Sena em portas e repositórios opt-in. [Operação e limites](../engineering/persistencia-mega-sena.md) e [evidências executadas](verificacao-spec-0025.md). Publicação, importação e demais fontes permanecem contratos futuros.

## 1. Identificação e idempotência

Existem quatro identidades diferentes:

| Identidade | Chave | O que deduplica |
|---|---|---|
| Bytes | SHA-256 do raw | mesmo conteúdo armazenado |
| Captura | receipt_id e tentativa HTTP | o ato de observar a fonte; não deduplicar por hash raw |
| Interpretação | receipt + adapter/code/canonicalization/validation versions + catalog_fingerprint | a mesma receita de processamento, incluindo replays |
| Concurso | draw_id e aliases qualificados | o evento do mundo real, independente de fonte ou interpretação |

Uma quinta chave, `command_key`, deduplica a repetição técnica de um comando. Um operador que faz outra coleta intencional recebe nova chave; uma repetição após timeout de commit reapresenta a mesma chave. A camada de aplicação conserva essa chave ao repetir a transação.

Comandos guardam também fingerprint da entrada (`request_hash`, com formato identificado). Reutilizar uma chave com parâmetros ou receipt diferentes resulta em idempotency_conflict; não devolve sucesso de outro pedido. O hash exclui relógio de execução e segredos, mas inclui os parâmetros que definem a intenção.

Mesmos bytes em duas fontes ou instantes geram receipts distintos. A interpretação do mesmo receipt/receita já concluída reutiliza suas observações e revisões, registrando nova tentativa como replay. Não volta a comparar um resultado antigo contra a revisão mais recente para recriar uma correção.

Mudança de receita cria interpretação nova, identificada como reinterpretação. Uma captura antiga reinterpretada nunca muda a revisão publicada sem decisão de publicação. Dados divergentes de fontes diferentes permanecem candidatos com proveniência explícita; a chegada por último não torna a fonte mais verdadeira.

## 2. Fronteiras de transação

### T1 — iniciar aquisição

Transação curta cria/reutiliza `ingestion_run` pela chave e abre `fetch_attempt`. Commit antes do GET. Timeout de rede não mantém lock ou conexão SQL ocupados.

### Fora da transação — obter e preservar bytes

Buscar resposta limitada e salvar objeto por hash com operação que não sobrescreva conteúdo divergente. Conferir tamanho e hash. O PostgreSQL não participa atomicamente desse PUT.

### T2 — registrar captura

Registrar/reutilizar `raw_artifact`, conferir tamanho e referência, inserir receipt e concluir tentativa HTTP numa transação. Uma resposta HTTP de erro com corpo também pode produzir receipt. Uma falha sem corpo conclui tentativa como failed, sem fabricar artefato.

Crash entre PUT e T2 pode deixar objeto órfão. Será identificado por auditoria e política de retenção; não se apaga automaticamente nem se inventa um receipt retroativo.

### T3 — interpretar e reconciliar um concurso

Parsing e validação custosos acontecem sobre o raw verificado fora de transação longa. A etapa curta de gravação:

1. Reivindicar a interpretação/linha pela chave estável; retornar resultado existente se já concluída.
2. Resolver identidade com UNIQUE; se outro escritor criou o draw, desfazer a criação concorrente por rollback/savepoint, recarregar e continuar sob lock desse draw. Não deixar um draw órfão após ON CONFLICT.
3. Travar o draw e ler a revisão de comparação depois do lock.
4. Comparar hash com sua versão de canonicalização.
5. Reutilizar revisão idêntica ou criar a próxima revision_no e todos os seus filhos.
6. Inserir observação com decisão, vínculo à revisão e diagnósticos.
7. Conferir o agregado e selar a revisão; atualizar somente o ponteiro candidato autorizado pela política de reconciliação.
8. Para avanço contíguo, inserir `sync_step` e mover checkpoint na mesma transação.
9. Gravar auditoria/eventos necessários e commit.

Não executar `MAX(revision_no)+1` sem lock do draw. UNIQUE(draw_id, revision_no) continua sendo a proteção final. Em uma importação XLSX, a transação é por concurso/lote pequeno; falha de uma linha não justifica transação de todo o histórico.

Observações inválidas com identidade ausente são gravadas em quarentena com seus issues, sem draw fictício. Uma correção rejeitada continua rastreável. Quando só há mesma evidência já processada, não se cria revisão duplicada.

### T4 — revisar um concurso antigo

Usa as mesmas garantias de T3, mas atualiza o ponteiro de revisão circular, não o cursor de avanço. Falha preserva o item pendente. Uma revisão candidata pode ser nova mesmo quando não aumenta a cobertura.

### T5 — publicar explicitamente

Travar draw, conferir revisão esperada, validação integral, proveniência e política de autoridade/qualidade. Inserir `revision_decision`, alterar `published_revision_id`, registrar `audit_event` e `outbox_event` na mesma transação.

Uma correção candidata não substitui o que já está publicado. Se for aprovada, a decisão anterior permanece no histórico. Não atualizar o payload da revisão nem apagar a antiga. Ler publicado sempre significa seguir o ponteiro de publicação, nunca ordenar por maior revision_no.

### T6 — concluir lote

Concluir `ingestion_run` com contagens e motivo de parada em transação curta. O resumo não é a autoridade sobre quais passos foram processados: essa prova está em observações e sync_steps já confirmados. Crash antes do resumo permite retomada/auditoria sem perder passos concluídos.

## 3. Concorrência e cursor

Usar READ COMMITTED com locks de linha para gravações curtas, UNIQUE/FKs e atualização condicional por row_version. Leituras consistentes de auditoria podem usar REPEATABLE READ no banco, sem presumir snapshot atômico do object storage. Esses mecanismos e seus limites foram conferidos na [documentação de isolamento](https://www.postgresql.org/docs/17/transaction-iso.html) e de [locks explícitos](https://www.postgresql.org/docs/17/explicit-locking.html).

Para um fluxo de sincronização, adquirir lease curta persistida antes de consultar a rede. `lease_token` é crescente e atua como fencing token: toda gravação de passo/cursor exige o token ainda atual e lease válida. Se expirar durante o GET, o trabalhador antigo pode preservar sua captura, mas não concluir o avanço com token vencido. A duração concreta e renovação serão qualificadas na implementação; não usar lock SQL aberto durante rede ou espera.

Ordem de locks quando houver checkpoint: checkpoint → draw → linhas filhas. Operações de concurso isolado travam somente draw e nunca tentam adquirir checkpoint depois. Importações de múltiplos draws usam ordem estável por ID para reduzir deadlocks.

| Situação | Resultado obrigatório |
|---|---|
| Dois escritores descobrem o mesmo concurso | uma identidade; disputa resolvida por UNIQUE e reload |
| Dois escritores oferecem o mesmo conteúdo | uma nova revisão, observações distintas quando as capturas forem distintas |
| Duas correções diferentes | revisões serializadas como candidatas; nenhuma publicação implícita |
| Worker antigo retorna depois de lease trocada | captura conservada; cursor não avança com token antigo |
| Commit responde timeout após sucesso | nova tentativa com a mesma chave retorna o resultado já confirmado |
| Conflito/deadlock | repetir a transação inteira com a mesma chave e evidência; limite de tentativas na aplicação |
| Fonte devolve concurso futuro/antecipado | pode haver candidato, sem salto do cursor |

O avanço aceita somente `expected_cursor + 1` e o `sync_step` precisa apontar para observação completa da identidade oficial correspondente. Se o cursor mudou, o comando retorna checkpoint_conflict; o chamador recarrega, não sobrescreve.

As chaves numéricas são uma estratégia da Mega-Sena. Datas ou PKs do provedor de outra modalidade não são convertidas automaticamente para sequence_no.

HTTP 429 exige checkpoint/cooldown persistidos em transação curta independente do candidato inválido. Não perder o cooldown porque a transação de reconciliação foi rejeitada. A política atual de 15 minutos será conservada na migração; não é apresentada como limite oficial.

## 4. Onde cada garantia será aplicada

| Invariante | Banco | Aplicação / auditoria |
|---|---|---|
| Slug/alias/chave de comando únicos | PK/UNIQUE | traduzir conflito em erro de domínio |
| Regra, série, componente e faixa da mesma loteria/versão | FKs compostas | resolver definições antes de persistir |
| Revisão do ponteiro pertence ao draw | FK composta | decisão/política antes de mover ponteiro |
| Regras validadas sem sobreposição | EXCLUDE usando daterange e lottery_id, com `btree_gist` | não preencher lacunas artificialmente |
| Tipos exclusivos e estados de ausência | NOT NULL/CHECK da própria linha | validar payload de origem |
| Quantidade de bolas, limites e unicidade por componente | constraint trigger diferível de integridade da revisão | validate_draw antes de T3; testes por versão |
| Regra aplicável à data e exatamente uma série principal | constraint trigger diferível | validar agregados e referências durante ativação |
| Revisão aceita tem observação de suporte concluída, filhos completos e está selada | constraint trigger diferível | persistir agregado inteiro em T3; não exigir fim do lote inteiro para aceitar uma linha |
| Cursor avança exatamente um e tem step concluído | trigger de transição + FK/contexto + row_version | caso de uso contíguo; auditoria do intervalo inteiro |
| Dinheiro decimal finito e sem arredondamento coercitivo | numeric com CHECK da linha | escala e limite específicos do adaptador |
| Conteúdo da revisão não muda depois do commit | permissões + trigger bloqueando alterações da revisão selada e INSERT/UPDATE/DELETE de seus filhos de conteúdo | nova revisão quando a interpretação mudar |
| Hash corresponde a raw/canonicalização | formato/tamanho e referências no banco | verificar bytes e reproduzir manifesto/normalização |

EXCLUDE com intervalos e `btree_gist` é uma estratégia documentada do PostgreSQL; a migration deverá demonstrá-la em instância real com o provedor escolhido. [Range constraints](https://www.postgresql.org/docs/17/rangetypes.html#RANGETYPES-CONSTRAINT), [btree_gist](https://www.postgresql.org/docs/17/btree-gist.html).

CHECK não consultará catálogo ou contagem de filhos. Os poucos constraint triggers acima serão específicos, declarados e testados; não haverá motor genérico de regras em PL/pgSQL. Consistência continua sendo validada no domínio, com o banco protegendo as invariantes estruturais de commit. [Limites de CHECK](https://www.postgresql.org/docs/17/ddl-constraints.html#DDL-CONSTRAINTS-CHECK-CONSTRAINTS).

Os relacionamentos de suporte podem ser inseridos em ordem diferente dentro de T3, mas precisam existir no commit. Planejar FKs/constraint triggers diferíveis apenas onde necessário; PKs e UNIQUEs que servem de alvo de FK permanecem adequados à referência. NOT NULL e CHECK de linha não são adiados por `SET CONSTRAINTS`. [Restrições diferíveis](https://www.postgresql.org/docs/17/sql-set-constraints.html).

## 5. Portas da aplicação

Assinaturas abaixo são contratos de comportamento, ainda não interfaces Python implementadas:

| Porta | Operação | Resultado esperado |
|---|---|---|
| UnitOfWork | begin / commit / rollback | agrupar repositórios da mesma conexão/transação; rollback ao falhar |
| CaptureRepository | register_attempt, finish_failure, register_capture | metadados imutáveis e tentativa rastreável |
| ArtifactStorage | put_if_absent(hash, bytes), verify, open | bytes externos; não faz commit SQL |
| ProcessingRepository | claim_recipe, record_attempt, find_completed_observation | reutilização por receita e linha, sem duplicar interpretação |
| DrawRepository | resolve_identity, lock_draw, find_head, append_revision | nenhuma publicação implícita |
| ObservationRepository | append_decision, append_issues | referência explícita a processing_run, raw e revisão |
| SyncRepository | claim_lease, lock_checkpoint, complete_next_step, mark_review, set_cooldown | compare-and-swap de cursor/token e continuidade |
| PublicationRepository | decide_publication(expected_revision) | ponteiro + decisão + auditoria + outbox em T5 |
| AuditRepository | append_report, read_manifest | relatório/manifesto versionados e dados para reconciliação |

Repositórios não chamam rede, não renderizam HTTP e não fazem commit por conta própria. A unidade de trabalho usa o mesmo conjunto de repositórios em T3/T5. Exceções SQL são traduzidas pelo adaptador em códigos estáveis: identity_conflict, duplicate_command, idempotency_conflict, rule_period_conflict, invalid_revision, checkpoint_conflict, lease_lost, evidence_missing e storage_unavailable. Não expor SQL, DSN ou credenciais nas respostas.

As portas atuais `ArtifactStore`, `RevisionRepository` e `SyncStateStore` permanecerão funcionando até sua substituição vertical. Só trocar `reconcile()` por SQL e continuar gravando cursor separadamente não atenderá a este contrato: T3 precisará de uma operação de aplicação que reúna ambos na mesma UnitOfWork.

## 6. Canonicalização e importação

O hash semântico atual de `semantic_payload()` é preservado como legado com sua versão. O modelo relacional acrescenta escopo, ordinais e vínculos; seu primeiro formato canônico terá identificação própria, vetores de referência e comparação reproduzível antes da carga. Não renomear hashes antigos como se fossem calculados no formato novo.

Os fatos tipados são a autoridade operacional. Um snapshot canônico de intercâmbio, se salvo como artefato, é produzido da mesma representação validada e usado para auditoria; não é uma segunda fonte livremente editável. JSONB não substitui as relações do modelo lógico.

| Arquivo/conceito atual | Destino lógico | Cuidado de importação |
|---|---|---|
| artifacts/hash.json | raw_artifact + object storage | conferir bytes, sem alterar hash |
| receipts/id.json | capture_receipt | preservar instante/URL; classificar legacy_import se não há tentativa HTTP documentada |
| outcomes/receipt-id.json | processing_run/attempt + candidate_observation | conservar múltiplas tentativas; agrupar receita só quando houver evidência suficiente |
| revisions/concurso.json | draw + aliases + draw_revision + filhos | IDs/números de revisão não autorizam publicação |
| sync-state.json | ingestion_baseline + sync_checkpoint | conferir baseline, lease nova e todo o intervalo antes de importar cursor |
| sync-runs/id.json | ingestion_run + auditoria de importação | erro de transporte sem corpo continua sem raw |
| diagnóstico SPEC-0022 | ingestion_audit + artefato | guardar manifesto e versões |

Receipts antigos não registram todas as versões de código/receita. Manter marcador explícito de origem legada e a evidência disponível; não inventar commit, tempo de execução ou normalizador. Quando versões não puderem ser inferidas com confiança, nova interpretação é produzida e registrada separadamente.

A baseline até 2954 pode ser referenciada no banco mesmo antes da carga histórica, com `materialization_status=referenced`. Esse estado não torna consultas aos concursos 1–2954 disponíveis nem permite marcar a carga como completa. Depois da carga auditada, registrar a materialização e seu manifesto.

## 7. Publicação, análises e acesso

O processo de ingestão escreve evidência e candidatos. O processo de leitura pública consulta apenas revisões publicadas. Permissões do banco separarão migração, ingestão, publicação, leitura e auditoria, sem usuário de aplicação superuser.

O outbox evita evento publicado sem commit dos dados. A entrega é pelo menos uma vez; consumidores precisam deduplicar por event_key. Reprocessamento analítico não ocorre dentro da transação de ingestão.

Datasets futuros guardarão IDs exatos de revisões e decisões de publicação disponíveis até o corte temporal. Selecionar apenas a revisão atualmente publicada causaria vazamento de correções posteriores em backtests. Essas relações serão detalhadas com a plataforma analítica.

## 8. Sequência de implementação

1. SPEC-0024: DDL/migrations e infraestrutura de testes PostgreSQL para catálogo, evidências, resultados e checkpoint, com triggers exigidos pelo recorte. [Recorte físico e resultado](verificacao-spec-0024.md). Canonicalização relacional/vetores acompanham o mapper e continuam obrigatórios antes da carga, não foram declarados prontos pelas migrations.
2. Implementar repositórios e UnitOfWork sobre esse recorte, com concorrência e injeção de falhas.
3. Importar workspace/baselines e seis históricos com auditoria antes/depois.
4. Qualificar publicação e servir consultas por contratos de API.

RLS por locatário, tabelas de usuário, pagamentos/apostas, particionamento, event sourcing integral, broker externo e modelos físicos de ML estão adiados. O banco é relacional com eventos de decisão/auditoria, não um event store universal.

## Evolução para as seis loterias — etapa 6

O [contrato comum](persistencia-seis-loterias.md) estende a aplicação dos perfis históricos da SPEC-0026 ao PostgreSQL, reutilizando o núcleo de revisões, conteúdo, transações e armazenamento. O fluxo Mega-Sena anterior conserva seu contrato e a ponte histórica/JSON. Conjuntos aprovados são o caminho privado de leitura, sem remover o bloqueio de publicação individual. Estado e critérios de aceite: [etapa 6](../engineering/etapa-6-persistencia.md).
