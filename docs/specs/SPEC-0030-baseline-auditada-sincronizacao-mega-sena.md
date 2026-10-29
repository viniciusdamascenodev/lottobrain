# SPEC-0030 — Registro de baseline auditada e inicialização segura da sincronização Mega-Sena

## Estado

Concluída em 25/10/2026 (America/Sao_Paulo). Critérios registrados antes da implementação. Aprovação/inicialização comprovadas somente em PostgreSQL descartável; nenhuma ativação operacional.

## Objetivo e limites

Converter uma importação Mega-Sena encerrada como completed e novamente auditada no próprio banco em uma baseline loaded imutável, com vínculo explícito da fonte XLSX para o fluxo JSON. Inicializar checkpoint no concurso 2954, próximo 2955, sem inferir cursor de candidatos adiantados ou de um relatório externo.

Somente implementação e prova em PostgreSQL descartável. Não criar banco operacional, disparar HTTP de loterias, agendamento, publicação, frontend, autenticação de usuários, nova modalidade ou coletor. Preservar raws, contratos canônicos, fixtures, relatórios anteriores, migrations já existentes e mudanças preexistentes.

## Decisões de arquitetura

- Baseline histórica conserva source_id do XLSX e artifact_id original. Checkpoint conserva source_id do JSON. Não atribuir proveniência JSON ao arquivo XLSX para contornar a FK atual.
- Migration nova e reversível introduz vínculo append-only de ativação entre baseline, importação/receipt histórico, aprovação, auditoria e checkpoint JSON. Substituir a FK de mesma fonte por FKs de loteria/fonte e guarda que exige esse vínculo para passagem entre fontes. Caminhos legados de mesma fonte mantêm as garantias anteriores.
- A autorização de inicialização usa papel SQL separado do ingestor. Não conceder INSERT de baseline/checkpoint ao coletor comum nem UPDATE de baselines ou vínculos a qualquer papel da aplicação.
- Raw e manifesto são reconstruídos fora de SQL. Na transação de ativação, reauditar cobertura em snapshot consistente; não confiar em qualified=true enviado pelo chamador ou no JSON da SPEC-0029.
- Inicialização é explícita, idempotente e atômica: baseline + auditoria/vínculo + checkpoint, sem lease nem sync_step. Replay retorna o registro original, não reinicializa cursor/tempos ou reaprova uma configuração nova.
- Só existe um fluxo de inicialização Mega-Sena neste recorte. Rejeitar checkpoint pré-existente da fonte, mesmo em outro stream, para não resetar cursor ou contornar cooldown.

## Critérios de aceitação

1. Pedido fixa chave de comando, importação histórica, hash esperado do plano e referência explícita de aprovação; validar antes de I/O. Sem seleção arbitrária de concurso, loteria, fonte ou cursor.
2. Bytes/manifesto persistidos íntegros; importação presente, completed e cobertura atual 2954/2954 qualificada, com valores/hashes relacionais conferidos. Rejeitar parcial, stopped/failed, raw corrompido/ausente, manifesto divergente e identidade invalidada. Auditoria histórica usa receita original; novas operações requerem catálogo JSON atual qualificado.
3. Baseline nova loaded conserva raw, fonte XLSX, concursos 1–2954 e manifesto de registros. Auditoria/vínculo preserva hash e conteúdo do relatório, receita/política, origem e destino, aprovação e identidade do checkpoint. Nenhuma baseline referenced existente é promovida por UPDATE.
4. Checkpoint JSON nasce exatamente em 2954, review_next 2955, sem lease, step, cooldown artificial ou publicação. Candidato 3071 já existente não faz avançar cursor.
5. Replay da mesma intenção não duplica registros nem altera cursor/finished_at/approval time; chave incompatível ou outro comando para fluxo existente falha explicitamente. Concorrência converge para uma ativação e não deixa baselines órfãs. Erro de commit ambíguo é recuperado pela mesma chave, sem nova aprovação implícita.
6. Falhas antes/depois de cada INSERT revertem baseline/vínculo/checkpoint juntos. Ingestor não pode inicializar; bootstrap não recebe DDL, publicação, DELETE ou UPDATE de baseline/catálogo. Vínculo e baseline permanecem imutáveis; passagem entre fontes sem vínculo é recusada pelo banco.
7. Provar transição 2954→2955 com JSON real já arquivado localmente, sem GET novo. Lease/token/CAS e observação/revisão/step/cursor continuam atômicos; falha não avança. Replay da ativação após avanço não reseta checkpoint. Não fabricar sorteios de sucesso.
8. Migration nova funciona em banco vazio e no recorte anterior preenchido; downgrade com ativação é recusado sem apagar evidência. Não editar migrations antigas nem dispensar constraints/permissões para passar nos testes.
9. Executar testes comuns e integração completa, incluindo importação integral, isolamento, segurança, concorrência e regressões anteriores. Confirmar hashes protegidos, auditoria anterior e encerramento dos clusters. Evidência de teste não representa ativação operacional.
10. Documentar arquitetura/contrato de banco, operação, limites, relatório novo e aprendizados reutilizáveis. Atualizar roadmap e recomendar uma única próxima tarefa, sem executá-la.

## Plano de verificação

Testes puros do pedido/política sem dependências SQL. Casos SQL pequenos para recusas e privilégios; um cenário completo novo com os 2.954 registros reais para aprovação, falhas/rollback, concorrência, replay e passagem ao JSON 2955. O cenário SPEC-0029 permanece separado e continua provando carga sem baseline. Usar somente bytes locais já existentes para 2955/3071; mutações negativas devem ser identificadas como testes, sem resultados fictícios operacionais.

## Resultado e evidências de aceitação

- **1–2:** pedido imutável/validado e plano esperado fixo; raw reconstruído fora de SQL. Auditoria integral refeita no banco da aprovação. Ausência, corrupção, divergência de manifesto, parcial/stopped, alias invalidado e destino bloqueado são recusados. Nenhum relatório externo é aceito como autorização.
- **3–4:** baseline loaded nova no XLSX, referência anterior referenced intacta, vínculo append-only com relatório/hash e ator SQL, checkpoint JSON inicialmente 2954/review_next 2955, sem lease/step inicial. Candidato real 3071 já presente não altera a fronteira.
- **5–6:** concorrência com duas chamadas, resposta perdida após COMMIT, recuperação pela mesma chave, conflito de intenção/fluxo e rollback após cada INSERT/before_commit verificados. Baseline/vínculo imutáveis, ingestor sem capacidade de inicialização e passagem sem vínculo recusada.
- **7:** bytes reais arquivados de 2955/3071 copiados integralmente para fixtures; zero GETs. Falha após step reverte tudo; repetição legítima confirma uma observação/step e avança 2954→2955. Replay da aprovação preserva o checkpoint avançado e o instante da decisão; salto para 3071 e nova operação com fonte bloqueada são recusados.
- **8:** head 0030_01, upgrade/downgrade vazio, upgrade sobre baseline/checkpoint referenciados anteriores e downgrade recusado quando há ativação. FKs de contexto, ator e snapshot reforçados sem reescrever migrations 0024.
- **9:** **334 testes distintos aprovados**: 235 comuns (202,79 s) e 99 no runner completo (2.080,574 s; 91 PostgreSQL reais + oito dublês). Reexecução focal com as constraints finais: seis casos aprovados (1.110,716 s), já incluídos nos 99, não contados duas vezes. Os 70 arquivos protegidos mantiveram hashes; auditoria local anterior reproduzida exatamente/healthy. Todos os clusters desta etapa desligados, postmaster.pid ausente, serviços PostgreSQL 12/13 preservados.
- **10:** arquitetura/contrato de banco, operação, relatório novo, roadmap e aprendizados L-162–L-167 documentados. Uma única próxima tarefa indicada, não executada.

A suíte completa foi iniciada antes do último reforço de constraints da migration ainda em elaboração. Por isso a funcionalidade inteira (aprovação com 2.954 linhas + cinco verificações rápidas) foi reexecutada em cluster independente com o DDL final. Ambos os cenários positivos tiveram o mesmo hash de cobertura `6406a246210b3b55116dfcb30a343359969eac59f9d978bef21708304dd0efa9`, com UUIDs diferentes e próprios de cada banco. O smoke inicial teve uma expectativa de classe de erro incorreta (RaiseException em vez de CheckViolation); o teste foi corrigido e essa tentativa com erro não foi contada como aprovação.

## Artefatos e limites finais

- [Evidência nova de execução e aprovação](../data/mega-sena-baseline-spec-0030.json), sem alterar o relatório da SPEC-0029.
- [Modelo físico, FKs e privilégios](../database/baseline-auditada.md).
- [Operação, reprodução, estado e replay](../engineering/baseline-sincronizacao-mega-sena.md).
- Log completo: `.local-postgres/spec0030-integracao-20261025.log`; cluster `883b1ebac360425cb013c13d3e26a462`, saída 0.
- Log com a funcionalidade/constraints finais: `.local-postgres/spec0030-ativacao-final-20261025.log`; cluster `7cc4e8e0f83d4ce0a75fbe7a1e1190f0`, saída 0.

Não houve criação de banco/baseline operacional, GET externo, agendamento, interface, autenticação administrativa, publicação, nova modalidade, nova dependência ou alteração dos raws/fixtures/relatórios/migrations anteriores. As duas fixtures acrescentadas são cópias íntegras de bytes locais, não sorteios inventados. Os dados/logs dos clusters ficam locais e ignorados, sem servidor ativo. Mudanças preexistentes foram preservadas.

## Única próxima tarefa recomendada

**SPEC-0031 — Orquestração PostgreSQL da sincronização limitada Mega-Sena.** Carregar a baseline/checkpoint aprovados para descoberta, avanço contíguo e revisão com orçamento, espaçamento, cooldown e recuperação. Ainda não há esse orquestrador SQL; não confundir o fluxo de sincronização em arquivos com ativação automática do banco. Sem agendamento/publicação/ativação operacional como efeito colateral. Não executada.
