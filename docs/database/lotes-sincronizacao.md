# Lotes de sincronização PostgreSQL — SPEC-0031

## Relações e responsabilidades

| Relação | Responsabilidade |
|---|---|
| `baseline_activation` / `ingestion_baseline` | aprovação histórica já existente; não são recriadas pelo lote |
| `sync_checkpoint` / `sync_step` | cursor contíguo, ponteiro de revisão, cooldown e fencing já existentes |
| `sync_batch` | comando/pedido, política, catálogo fixado por fingerprint, fronteira/janela iniciais e resumo terminal |
| `sync_batch_operation` | descoberta/avanço/revisão, reserva de captura, receipt, comando de processamento, observação e decisão |

Migration nova `0031_01`, posterior a `0030_01`. Nenhuma migration anterior foi editada. Um índice parcial permite somente um lote running por checkpoint. Outro lote não contorna uma execução interrompida: é preciso retomar a mesma chave ou investigar o estado.

Um lote pode ter no máximo dez reservas de captura e operações limitadas por ordinal (até 22, margem conservadora para reaproveitamento). O planejador usa no máximo uma descoberta e uma volta na janela inicial de até 20 revisões, sob orçamento de consultas. FK composta impede reaproveitar uma operação de outro lote. O reaproveitamento aponta somente para descoberta concluída da identidade esperada.

## Estados e imutabilidade

`sync_batch`: running → completed ou stopped. completed significa lote concluído segundo o orçamento, não necessariamente toda a fonte atualizada; conferir stop_reason e remaining. Contexto inicial é imutável. Depois do encerramento, nem resumo nem instante são reescritos.

`sync_batch_operation`: pending → done. Receipt, uma vez associado, não é substituído. Comando/token de processamento podem mudar somente enquanto pending, permitindo retomar com outra lease sem reinterpretar uma operação confirmada. Operação done é append-only; lotes/operações não têm DELETE comum.

Operação pending em lote stopped pode representar captura inconclusiva ou falha de transporte. Ela não vira done para fazer a contagem parecer completa. O resumo expõe outcome/receipt ausentes e o motivo da interrupção.

## Atomicidade e ordem de locks

Ordem suportada no processamento: comando de interpretação → checkpoint → lote/operação → receita → draw/filhos. Administração do lote usa checkpoint antes do lote/operação; nenhum caminho adquire um comando de processamento depois de segurar checkpoint para esperar por outro processador.

Na mesma T3 são confirmados:

- interpretação, evidência, revisão/observação e tentativa idempotente;
- step/cursor quando forward aceito, ou review_next quando review aceito;
- conclusão da operação e, na descoberta aceita, latest_sequence;
- encerramento idempotente do resumo da captura correspondente.

`sync_operation_complete`, diferível até COMMIT, valida fonte/loteria/receipt/observação/comando, identidade oficial e token/lease. Para avanço exige step correspondente; para revisão exige o ponteiro planejado. Também protege descoberta, que não move o cursor, contra lease expirada no COMMIT. Quarentena nunca avança ou rotaciona.

O resumo do lote vem depois, em transação separada. Se ele falhar, operações/steps confirmados permitem reconstruí-lo, sem repetir GET ou regredir cursor. Campos resumidos não substituem o ledger nem a evidência relacional.

## Privilégios e recuperação de schema

Reaplicar `scripts/database/roles.sql` após a migration. O ingestor ganha INSERT e UPDATE limitado nos novos registros, não bootstrap/DDL/DELETE/publicação. Bootstrap conserva sua capacidade separada e não ganha INSERT de lotes. Audit continua somente leitura.

Downgrade com lote existente é recusado antes de remover evidência, mesmo que o lote esteja interrompido. Downgrade vazio remove apenas o recorte novo e permite reupgrade. Não editar ledger, desabilitar triggers ou truncar registros para forçar rollback.

Não foram adicionados broker, scheduler, outbox universal ou ORM de resultados. São duas relações para um consumidor concreto; fontes sem sequência oficial e outras modalidades não são adaptadas implicitamente.
