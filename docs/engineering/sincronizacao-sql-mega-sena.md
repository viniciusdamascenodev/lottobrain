# Sincronização SQL limitada Mega-Sena — SPEC-0031

## Composição e escopo

`SyncMegaSenaPostgres.execute(SyncBatchRequest(checkpoint_id, command, policy))` opera somente sobre um checkpoint aprovado pela SPEC-0030, stream Mega-Sena esperado e fonte JSON qualificada. Não inicializa estado nem adapta o workspace em arquivos. O retorno de ativação com initial_cursor=2954 não é usado como leitura do cursor vivo.

A aplicação recebe UoW, storage, transporte e função de espera por injeção. CaptureMegaSena/ProcessMegaSena são reutilizados. Sem CLI operacional, agendamento, configuração global de DSN ou HTTP disparado no import. Uma composição real deverá usar espera real; os testes registram as chamadas de espera e usam transporte dublê.

## Planejamento do lote

1. Validar pedido/política e recuperar comando terminal idêntico sem novo I/O/lease. Mudança de checkpoint, política ou versão do pedido na mesma chave é conflito.
2. Qualificar fonte, exigir baseline loaded/vínculo auditado, conferir o hash do relatório da aprovação e adquirir lease. Recusar outra execução ativa, inclusive mesma chave com lease ainda ocupada.
3. Congelar cursor/janela de revisão e política. Capturar descoberta e interpretá-la com fencing. Fonte atrás do cursor encerra stopped, sem regressão.
4. Avançar somente cursor+1. Se a descoberta já é exatamente o próximo, reutilizar o receipt, sem outro GET. Um candidato 3071 não preenche o intervalo anterior.
5. Reservar capacidade para uma revisão durante backlog quando houver orçamento; quando em dia, usar capacidade restante para a janela inicial circular. Não revisar dados recém-avançados no mesmo lote. Reutilizar descoberta quando a revisão é da mesma identidade.
6. Parar ao esgotar orçamento, alcançar a fronteira descoberta, encontrar quarentena/erro ou perder autorização/lease. caught_up refere-se à descoberta deste lote, não a uma garantia de que o provedor não publicou outro sorteio depois.

## Orçamento honesto e I/O

`max_requests` 1–10, `review_window` 0–20, `interval_seconds` 2–30. A política é a existente, compartilhada com o backend em arquivos, não apresentada como limite oficial do provedor.

Cada operação que pode exigir GET reserva uma chave estável antes do I/O. `request_slots_used` é limite conservador de intenções de captura, **não** uma alegação de quantas consultas chegaram ao servidor depois de uma queda. Falha antes de enviar pode consumir slot; isso não autoriza ampliar orçamento na retomada.

O transporte guardado verifica/renova lease, espera o intervalo e verifica novamente antes de GET novo. Espera, HTTP e storage ficam fora de transações SQL. O primeiro GET de outro lote também espera. Reutilização de receipt não executa o transporte nem outra espera e não ganha uma reserva nova.

T1 sem receipt pode ser resultado desconhecido. A mesma captura não é repetida automaticamente: o lote encerra capture_unresolved, preservando o comando/slot. Repetir com outra chave não é uma recuperação idempotente; exige nova intenção e investigação quando apropriado.

## Retomada, falhas e leases

- Chaves de captura são fixas por operação. T2 confirmado é recuperado pelo Capture existente, mesmo quando o vínculo da operação ainda não foi atualizado.
- Chaves de interpretação incluem operação e token. Só pending pode adquirir novo contexto; done nunca é reinterpretada por causa de outra lease.
- Operação/step/revisão confirmados juntos dispensam novo processamento quando a resposta de T3 ou o resumo é perdido.
- T3 de descoberta/revisão também tem testemunho diferível de lease. Não basta conferir o token antes do HTTP ou mover o cursor somente no avanço.
- Uma invocação não compartilha lease ativa com outra. Ela renova somente seu token e tenta liberá-lo no finally, sem mascarar o erro/resultado original. Se o processo morrer ou a aquisição tiver resultado ambíguo antes de devolver o token, aguardar expiração (até 300 segundos), não roubar/resetar estado.
- Infraestrutura interrompida mantém running para a mesma intenção retomar. Mudança/bloqueio de catálogo impede novos efeitos; não se troca silenciosamente a política de um lote em andamento. Estado que exija outra decisão deve ser diagnosticado, não destravado por edição manual do cursor.

O lease/CAS do checkpoint e as constraints existentes continuam sendo a autoridade de continuidade. Renovações/liberações não alteram cursor, baseline ou evidência. O resumo terminal é persistido e replay devolve a decisão passada mesmo com fonte bloqueada, sem reautorizar coleta.

## 429, respostas inválidas e transporte

O receipt 429 é preservado e o cooldown é gravado antes da T3, inclusive em descoberta/revisão. Se a T3 reverter, o cooldown permanece; novas chamadas são recusadas sem GET. Quarentena não avança nem rotaciona revisão. 404 e payload inválido interrompem sem sucesso; falha de transporte não tem retry automático.

O cooldown atual é de 15 minutos por política interna existente. Durante cooldown, retomar uma execução parcial pode ser recusado até ele terminar; os receipts já armazenados não são apagados. Não há loop de espera/requisição contínua nesta tarefa.

## Verificação e reprodução

Fixtures 2954/2955/3071 são bytes reais existentes, sob versão e com os hashes anteriores. O transporte, a espera e perdas/expirações são simulados e identificados. Não há sorteio 2956 fictício de sucesso para preencher backlog: testes de planejamento usam contadores em memória; o caso SQL de 429 na revisão exercita diretamente a fronteira T3 sem fabricar o concurso intermediário.

A suíte focal prepara uma aprovação real com os 2.954 registros. Na regressão completa, o cenário da SPEC-0030 publica um clone consistente de sua aprovação antes do avanço/bloqueio final; o mesmo processo/cluster usa esse template nos testes novos. Cada caso ganha outro banco isolado. Não se reutiliza um JSON de documentação como certificado de carga. Em execução focal sem esse template, a carga/aprovação são feitas integralmente.

```powershell
.venv\Scripts\python -m pytest tests/test_sql_sync_planning.py tests/test_mega_sena_sync.py -q
.venv\Scripts\python scripts/database/run_integration.py --pg-bin .local-postgres\17.11-3\pgsql\bin --test-pattern test_sync_batches_smoke.py
.venv\Scripts\python scripts/database/run_integration.py --pg-bin .local-postgres\17.11-3\pgsql\bin --test-pattern test_sync_batches*.py
.venv\Scripts\python scripts/database/run_integration.py --pg-bin .local-postgres\17.11-3\pgsql\bin
.venv\Scripts\python -m pytest tests --ignore=tests/database -q
```

Filtros são diagnóstico, não substituem regressão completa. O runner valida o cluster descartável e encerra o servidor ao terminar; não executar testes em banco operacional. As dependências opcionais existentes de banco continuam separadas. Contratos/fingerprints de chamadas anteriores sem batch foram preservados.

## Evidência final de 26/10/2026

Foram aprovados **375 testes distintos**: 257 comuns em 81,92 segundos e 118 no runner isolado em 7.114,014 segundos (110 com PostgreSQL real e oito com dublês). A execução focal anterior aprovou 15 casos em 629,467 segundos; o smoke aprovou três em 11,664 segundos. Esses subconjuntos não aumentam o total. O tempo da regressão é duração observada desta execução, não benchmark de importação ou sincronização.

O runner completo reutilizou o clone SQL da aprovação real comprovada pela SPEC-0030 e também repetiu a importação/auditoria independente da SPEC-0029. A prova positiva do lote tem cursor 2954→2955, um slot e duas operações com receipt/observação compartilhados. Os novos cenários de resumo perdido, 429 no avanço/revisão e fonte atrasada/bloqueada passaram na regressão completa. A alteração final de limpeza best-effort foi verificada na suíte comum, inclusive provocando falha na liberação; a assinatura adicional do protocolo não altera comportamento.

Os 76 arquivos anteriores protegidos permaneceram idênticos, e a auditoria anterior continuou healthy, igual ao relatório salvo. Os clusters descartáveis foram desligados; os serviços PostgreSQL preexistentes não foram alterados. Nenhuma consulta externa ou ativação operacional ocorreu. [Evidência com relatório, hashes e referências dos logs](../data/mega-sena-sincronizacao-sql-spec-0031.json).

## Limites e única próxima tarefa recomendada

**SPEC-0032 — Auditoria somente leitura da sincronização PostgreSQL Mega-Sena.** Relacionar lotes/operações, capturas, interpretação, steps/checkpoint e bytes, destacando execução parcial, captura inconclusiva e divergências. Gerar diagnóstico/recomendações sem reset de cursor, retry HTTP, reabertura ou correção automática. Sem publicação, agendamento ou ativação operacional. Não executada nesta etapa.
