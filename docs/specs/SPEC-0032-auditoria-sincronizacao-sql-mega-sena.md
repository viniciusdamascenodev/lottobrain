# SPEC-0032 — Auditoria somente leitura da sincronização PostgreSQL Mega-Sena

## Estado

Concluída em 26/10/2026 (America/Sao_Paulo). Escopo e critérios registrados antes da implementação.

## Objetivo e limites

Diagnosticar um checkpoint Mega-Sena aprovado e seus lotes/operações, cruzando captura, interpretação, observação, revisão, steps e bytes. Separar integridade de situação operacional e nunca usar o resumo terminal como autoridade de continuidade.

Sem coleta HTTP, parsing com efeitos, atualização de cursor/lease/cooldown, reparo, retomada automática, nova migration, agendamento ou banco operacional. Dados e relatórios anteriores são preservados. Não refazer a auditoria integral dos 2.954 registros históricos: verificar o vínculo da aprovação existente, seu hash e o artefato correspondente; a cobertura histórica continua responsabilidade da SPEC-0029/0030.

## Decisões

- Caso de uso independente do writer: porta de snapshot somente leitura e leitor de bytes, sem acesso a transporte ou métodos de escrita.
- Adaptador PostgreSQL abre REPEATABLE READ READ ONLY antes das consultas, aplica timeouts e sempre rollback/close. Nenhum lock de linha, advisory lock, UoW de escrita ou renovação de lease. Leitura dos objetos ocorre depois de fechar o snapshot SQL.
- Seleção explícita por UUID do checkpoint; limites de lotes e steps, com diagnóstico incomplete quando a consulta truncar. Não declarar saudável uma auditoria parcial. Ordenação determinística; situação temporal relativa ao instante do snapshot.
- Confirmar aprovação/baseline, sequência de steps, contextos e identidades, ledger de processamento e hashes relacionais/bytes. Reaproveitar reconstrução relacional existente, sem comparar contrato histórico e JSON por hash como se fossem iguais.
- Pending sem reserva iniciada, captura inconclusiva, receipt ainda não associado, interpretação pendente e operação confirmada são situações diferentes. Uma captura inconclusiva não autoriza GET novo.
- Confrontar resumo terminal com operações persistidas e cursor ao final daquele lote, não com o cursor atual de um lote posterior. Não exigir lease antiga ainda ativa para validar fatos já confirmados.
- Relatório JSON com códigos fechados e referências UUID; sem DSN, credenciais, SQL, caminhos de objetos ou mensagens arbitrárias de exceções. CLI opt-in exige conexão/raiz explícitas e só imprime resultado; não salva sobre relatórios existentes.

## Critérios de aceitação

1. Auditoria executável como papel audit, transação somente leitura, sem mutação de tabelas/bytes e com fechamento também nas falhas.
2. Baseline aprovada, fonte/stream, cobertura referenciada e steps contíguos verificados; checkpoint inexistente ou sem aprovação nunca é declarado saudável.
3. Lotes/operações relacionados a tentativas, receipts, interpretações, observações e revisões; avanço/revisão/quarentena e reutilização de descoberta conferidos sem duplicar consultas ou mudar estado.
4. Hash e tamanho dos bytes associados verificados fora de SQL; ausência, corrupção e falha de leitura aparecem sem expor caminhos. Revisões reconstruídas do conteúdo relacional, não de um resumo JSON.
5. Execução ativa/interrompida, captura inconclusiva, receipt desacoplado, resumo pendente/divergente, cooldown e fonte bloqueada/alterada distinguidos com recomendações não automáticas.
6. Histórico terminal validado sem confundir cursor atual com cursor histórico ou exigir lease antiga válida. Catálogo bloqueado não impede leitura da evidência passada.
7. Limites explícitos e truncamento incomplete; erros operacionais sanitizados; sem alegação de atualização ao presente ou permissão de coleta.
8. Testes puros de divergências e testes PostgreSQL reais com aprovação histórica real, incluindo snapshot concorrente, permissões e preservação antes/depois. Regressão comum e recorte SQL afetado aprovados; clusters descartáveis desligados.
9. Documentação de contrato/operação, evidência nova e aprendizados; roadmap atualizado e uma única próxima tarefa recomendada sem execução.

## Validação planejada

Reutilizar bytes reais existentes (2954/2955/3071) e uma aprovação SQL construída por importação/auditoria reais. Falhas/danos em snapshots em memória ou storage de teste serão identificados como simulação. Nenhuma edição em migrations aplicadas ou relatórios anteriores. Não repetir toda a regressão SQL de escrita de duas horas se o código existente não mudar; executar o recorte real da funcionalidade nova e a suíte comum completa.

## Entrega e resultados

Os nove critérios foram atendidos. Entrega separada em caso de uso/porta de snapshot, adaptador PostgreSQL somente leitura e CLI opt-in. Nenhum código de escrita existente, migration, grant ou pipeline foi alterado.

- **311 testes distintos aprovados nesta etapa:** 292 comuns, dez cenários SQL principais, três guardas PostgreSQL e seis dublês de ciclo de conexão. Os 35 testes focais puros estão incluídos nos 292, sem contagem duplicada. A suíte SQL anterior de escrita não foi repetida integralmente.
- A prova SQL final preparou importação/auditoria/aprovação reais dos 2.954 registros. O relatório positivo verificou cursor 2955, um step, duas operações e dois artefatos, sem problemas; fingerprints de todas as tabelas da aplicação e bytes do storage de teste ficaram idênticos antes/depois.
- Snapshot concorrente comprovado: escritor avançou a 2955 enquanto a auditoria permaneceu consistente em 2954, sem impedir a escrita. O leitor do auditor só foi chamado depois de fechar SQL. Um lote antigo com fim em 2954 foi validado após avanço posterior a 2955.
- Casos de falta de aprovação, captura inconclusiva, receipt desacoplado, bytes ausentes/corrompidos, fonte bloqueada, truncamento, resumo pendente e cooldown foram diferenciados sem correção automática.
- A primeira execução SQL teve nove aprovações e uma falha na instrumentação compartilhada do teste concorrente; corrigido somente o teste e repetido o recorte inteiro, com dez aprovações. Histórico da falha preservado na evidência; não contado como execução bem-sucedida.
- Os 79 arquivos anteriores protegidos mantiveram hashes; a auditoria local anterior permaneceu healthy e igual ao relatório salvo. Três clusters efetivamente iniciados foram desligados; uma tentativa inicial de provisionamento falhou antes de iniciar o servidor. Serviços PostgreSQL preexistentes não foram alterados.

[Evidência final](../data/mega-sena-auditoria-sql-spec-0032.json), [contrato de leitura](../database/auditoria-sincronizacao.md), [operação e limites](../engineering/auditoria-sincronizacao-sql-mega-sena.md) e [aprendizados L-174–L-178](../engineering/learnings.md).

**Única próxima tarefa: SPEC-0033 — Comando manual seguro para sincronização PostgreSQL Mega-Sena.** Criar uma entrada opt-in que componha diagnóstico, checkpoint explícito, limites e espera real antes de introduzir agendamento. Sem executar coleta real como efeito da implementação. Não executada nesta entrega.
