# SPEC-0031 — Orquestração PostgreSQL da sincronização limitada Mega-Sena

## Estado

Concluída em 26/10/2026 (America/Sao_Paulo). Critérios registrados antes da implementação.

## Objetivo e limites

Executar lotes manuais e limitados de descoberta, avanço contíguo e revisão circular usando exclusivamente baseline/checkpoint aprovados pela SPEC-0030. Não adaptar implicitamente o SyncState em arquivos ao SQL. Sem HTTP externo nesta entrega, agendamento, banco operacional, publicação, interface, autenticação administrativa ou novas modalidades.

## Decisões

- Reutilizar SyncPolicy e os casos de uso CaptureMegaSena/ProcessMegaSena. O backend em arquivos e os fingerprints anteriores permanecem intactos.
- Duas relações novas, de lote/operação, preservam intenção, política, fronteira/janela inicial, receipt, interpretação e resumo. Não criar framework de jobs, broker ou histórico de sorteios fictício.
- Cada operação reserva uma chave de captura estável antes do I/O. O orçamento limita slots reservados (incluindo falhas/intenções de resultado desconhecido), não afirma conhecer quantos GETs chegaram ao provedor após uma interrupção.
- O transporte recebe uma guarda que verifica/renova a lease, espera fora de SQL e revalida antes de cada GET novo. Replays de receipt não fazem GET nem consomem novo slot.
- Operações, revisão e progresso são concluídos na mesma T3 da interpretação. Testemunho diferível de operação confere token/lease no COMMIT também para descoberta/revisão, não apenas para avanço.
- A chave do processamento inclui operação/token; uma operação já confirmada nunca é reinterpretada na retomada. Lease ativa não é compartilhada por duas invocações, mesmo com a mesma chave. Exceção tenta liberar somente o próprio token; morte de processo requer expiração, sem roubo de lease.
- Descoberta pode ser reaproveitada para o próximo avanço ou revisão da mesma identidade. Candidato adiantado não pula lacunas. Janela de revisão é fixada pela cobertura anterior ao lote, sem rever dados recém-avançados.
- 429 é persistido em T2 e impõe cooldown antes de qualquer nova captura, inclusive na descoberta/revisão. Não há retry automático de HTTP, PUT ou COMMIT ambíguo.

## Critérios de aceitação

1. Validar checkpoint UUID, comando e política; exigir vínculo/baseline loaded aprovada, fonte JSON qualificada e stream esperado. Não inicializar/reparar/promover baseline ou checkpoint como efeito da sincronização.
2. Novo lote fixa cursor, ponteiro/janela de revisão, política, catálogo e chaves. Mesma chave/pedido terminal retorna o resumo original sem I/O/lease; intenção incompatível é conflito. Outro lote durante execução ativa é recusado.
3. Reservas de captura não excedem max_requests (1–10); revisão 0–20, intervalo 2–30 segundos. Espera, HTTP e storage ficam fora de SQL. Cada GET novo é espaçado, inclusive o primeiro de outra invocação. Dados brutos existentes não são modificados.
4. Descoberta identifica último concurso validado, para quando fonte está atrás e reutiliza receipt sem outro GET quando aplicável. Somente cursor+1 avança; candidato 3071 não preenche 2956–3070. Revisão circular limitada atualiza somente ponteiro/revisão, não cursor.
5. Step/cursor, rotação da revisão, interpretação/observação e conclusão da operação confirmam ou revertem juntos. Quarentena não avança/rotaciona. Token obsoleto, expiração no COMMIT e concorrência não permitem efeitos parciais.
6. Repetir lote interrompido reutiliza receipt existente e operações confirmadas, inclusive após perda de resposta de T2/T3 ou resumo. Nova lease não reinicializa cursor nem orçamento. Captura T1 de resultado desconhecido não é repetida automaticamente.
7. 429 em descoberta, avanço ou revisão interrompe o lote; cooldown é preservado mesmo com falha de T3. Transporte/404/payload inválido/quarentena param sem marcar sucesso e sem retry HTTP. Fonte bloqueada/catálogo alterado/lease ocupada impedem novas operações.
8. Lote terminal tem resumo durável limitado e histórico imutável de operações confirmadas. Exceção de infraestrutura mantém execução retomável; resultado ambíguo não é convertido em sucesso. Não mascarar erro original se liberação da lease falhar.
9. Migration forward nova, sem editar migrations aplicadas. Integridade/FKs/permissões e downgrade vazio/preenchido verificados; ingestor não ganha privilégios de bootstrap, DDL ou publicação.
10. Testes puros de planejamento e testes SQL sobre fixture de baseline realmente auditada, com bytes reais 2954/2955/3071 e mutações negativas identificadas. Regressão comum/SQL, hashes protegidos, auditoria anterior e desligamento dos clusters confirmados. Nenhum GET real ou sorteio fictício de sucesso.
11. Documentar arquitetura, operação, limites, evidência nova e aprendizados; atualizar roadmap. Recomendar uma única próxima tarefa sem executá-la.

## Verificação

Preparar uma vez um template SQL de teste com carga integral e aprovação reais; clonar o banco isoladamente entre cenários, preservando cada caso. A SPEC-0029/0030 continuam com suas próprias provas independentes. Captura/Processamento mantêm a camada SQL real; somente transporte/relógio/espera e falhas explicitamente simuladas são dublês. Fixtures versionáveis já existentes substituem consultas à rede.

## Resultado e rastreabilidade

Os onze critérios foram atendidos. `SyncMegaSenaPostgres` compõe captura/processamento existentes; o planejamento fica na aplicação, o registro transacional nos repositórios e as invariantes de persistência na migration nova `0031_01`. Duas tabelas registram lotes/operações sem criar infraestrutura de agendamento.

- **375 testes distintos aprovados:** 257 comuns e 118 no runner isolado (110 PostgreSQL real, oito dublês). As execuções focais de 15 e três testes são subconjuntos, não somadas novamente.
- A prova positiva registrou 2954→2955 com um slot de captura e duas operações que compartilham receipt/observação. Revisão, backlog 3071 sem salto, concorrência, expiração no COMMIT, rollback, confirmações perdidas e 429 nas três fases foram verificados.
- Os quatro casos SQL acrescentados depois da execução focal passaram na regressão completa: perda de resumo, 429 no avanço/revisão e fonte atrasada/bloqueada. O teste de falha na liberação da lease passou na suíte comum final.
- Os 76 arquivos anteriores protegidos mantiveram seus hashes; a auditoria em arquivos permaneceu healthy e idêntica ao relatório anterior. Dados brutos, relatórios anteriores, fixtures e migrations aplicadas foram preservados.
- Provas somente em bancos descartáveis; nenhum GET externo, banco operacional, agendamento ou publicação. Os três clusters de teste foram desligados.

[Evidência desta execução](../data/mega-sena-sincronizacao-sql-spec-0031.json), [contrato SQL](../database/lotes-sincronizacao.md), [operação e reprodução](../engineering/sincronizacao-sql-mega-sena.md) e [aprendizados L-168–L-173](../engineering/learnings.md).

**Única próxima tarefa: SPEC-0032 — Auditoria somente leitura da sincronização PostgreSQL Mega-Sena.** Diagnosticar o encadeamento persistido e capturas inconclusivas antes de introduzir ferramentas de reparo ou operação. Não executada nesta entrega.
