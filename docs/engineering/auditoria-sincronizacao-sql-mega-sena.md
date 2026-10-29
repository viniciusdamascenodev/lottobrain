# Auditoria somente leitura da sincronização SQL — SPEC-0032

## Responsabilidades e execução

`AuditMegaSenaPostgres(reader, storage).execute(SyncAuditRequest(checkpoint_id))` verifica um checkpoint explícito e o histórico limitado de sincronização. A aplicação depende de uma porta de snapshot e de leitura de objetos; não recebe transporte, writer ou capacidade de retomar lotes. O adaptador PostgreSQL é independente da UoW de escrita, usa REPEATABLE READ READ ONLY com timeouts, termina com rollback e fecha a conexão antes de ler bytes. Conexões autocommit são recusadas: SET TRANSACTION fora de uma transação não seria proteção suficiente.

Não há migration, concessão de privilégios nova, agendamento ou alteração de dados. O papel `lottobrain_audit`, já existente, tem as leituras necessárias. A conexão deve pertencer a um login com esse papel e sem privilégios de escritor, bootstrap ou administração. A transação READ ONLY também impede escrita caso alguém forneça um login mais privilegiado.

```powershell
# Configurar LOTTOBRAIN_PG_AUDIT_DSN por gerenciamento local de segredos;
# não colocar credenciais no comando, relatório ou repositório.
.venv\Scripts\python -m app.interfaces.audit_sync_postgres --checkpoint <UUID> --object-root <raiz-existente-dos-objetos>
```

O comando imprime JSON e não salva arquivos. Saída 0: healthy; 2: diagnóstico que exige atenção, inconsistência, seleção incompleta ou checkpoint ausente; 1: argumentos/configuração/infraestrutura indisponíveis. Erros de infraestrutura são códigos fixos, sem DSN, SQL, caminhos ou mensagens de exceções. A raiz pode ser inexistente: a leitura relata evidência ausente, sem criar diretórios. Não apontar este comando a um banco por suposição nem reutilizar a variável de conexão do ingestor implicitamente.

## Evidência verificada

| Recorte | Conferências |
|---|---|
| Baseline e aprovação | vínculo de fontes/baseline/checkpoint, relatório e hash de cobertura, manifesto/plano e raw histórico, run de importação concluído |
| Continuidade | steps desde a fronteira histórica até o cursor, identidade oficial, observação, conteúdo relacional e token coerente |
| Lote | hash do pedido, política/janela congelada, descoberta, ordem e cursor das operações, orçamento e fronteira descoberta |
| Captura | chave estável, comando/tentativa, identidade pedida, receipt e artefato; receipt confirmado antes do attach continua visível |
| Interpretação | chave por operação/token, hash do pedido, tentativa/receita/observação e contexto de catálogo, revisão selada e identidade |
| Bytes | disponibilidade, SHA-256 e tamanho; JSON aceito normalizado de forma pura e comparado com observação/conteúdo relacional |
| Resumo terminal | reconstrução a partir das operações, cursor e revisão ao fim daquele lote; cursor atual não substitui a fronteira histórica |

Uma descoberta 3071 pode existir como candidata sem demonstrar continuidade até 3071. `cursor_claimed` é o valor lido; `steps_checked`, problemas e status precisam acompanhá-lo. O relatório não declara atualização ao presente, publicação, autorização de coleta ou probabilidade de previsão.

Esta auditoria **não reexecuta a prova integral dos 2.954 concursos da baseline**. Ela verifica a aprovação referenciada, seus vínculos e bytes. Para reauditar o histórico relacional inteiro, usar a cobertura da SPEC-0029, sem confundir aprovação passada com certificação nova. Também não enumera objetos órfãos do storage nem comandos sem vínculo com o checkpoint selecionado.

## Estados e recomendações

| Situação | Diagnóstico |
|---|---|
| `healthy` | nenhuma divergência ou aviso no recorte completo selecionado; não autoriza escrita |
| `attention` | fato operacional esperado, como fonte bloqueada, cooldown, quarentena ou execução interrompida |
| `inconsistent` | vínculo, sequência, pedido, resumo, conteúdo ou bytes não conferem |
| `incomplete` | limite alcançado, sem inconsistência demonstrada; nunca vira healthy por omitir dados |
| `not_found` | checkpoint não existe; nada é criado |

Uma operação pending distingue captura não iniciada, captura inconclusiva, transporte falho, receipt ainda não associado e interpretação pendente. Operações done são verificadas como confirmadas ou em quarentena. O auditor não exige lease antiga ativa para aceitar um fato confirmado. Em lote running, avalia token/validade relativamente ao instante do snapshot para separar execução ativa de interrompida. Esse instante não prova liveness do processo.

Recomendações têm `automatic=false`. Captura inconclusiva exige investigação sem reenviar HTTP; lease ativa/cooldown pede espera e nova auditoria. Retomada com a mesma chave continua uma decisão explícita pelo fluxo existente. Nenhuma recomendação altera cursor, orçamento, catálogo, lease ou resumo.

## Limites e consistência

Padrões: até 100 lotes e 5.000 steps por checkpoint. `--max-batches` aceita 1–200 e `--max-steps` 1–5.000, sem bool/float no contrato da aplicação. Lotes são selecionados do mais antigo ao mais recente; o leitor busca um extra para detectar truncamento. As operações têm o limite físico de 22 por lote. Tentativas auxiliares têm teto de 20.000, também com sinalização de truncamento. Conteúdo relacional é lido em blocos de até 500 revisões; uma revisão inválida não esconde as demais.

O snapshot é consistente no banco; arquivos são lidos depois, por hash, e não participam da mesma transação distribuída. Falha ou alteração de bytes nesse intervalo aparece como indisponibilidade/divergência, sem conserto automático. O leitor não usa locks de linha/advisory, não renova lease e não qualifica fonte para autorizar escrita. O catálogo atual é somente um diagnóstico adicional; bloqueio não impede examinar fatos passados.

## Reprodução dos testes

```powershell
.venv\Scripts\python -m pytest tests --ignore=tests/database -q
.venv\Scripts\python -m unittest discover -s tests/database -p test_sync_audit_reader.py -v
.venv\Scripts\python scripts/database/run_integration.py --pg-bin .local-postgres\17.11-3\pgsql\bin --test-pattern test_sync_audit.py
.venv\Scripts\python scripts/database/run_integration.py --pg-bin .local-postgres\17.11-3\pgsql\bin --test-pattern test_sync_audit_smoke.py
```

O recorte principal carrega/audita/aprova os 2.954 registros em banco descartável (ou usa clone consistente da aprovação SQL real no mesmo processo/cluster). Só o transporte usa bytes reais arquivados em dublê, sem GET. Testes puros usam metadados dublês explicitamente identificados; o relatório antigo é entrada de teste, nunca certificado para criar uma baseline SQL. Danos são restritos ao snapshot em memória ou storage temporário de teste.

## Evidência final de 26/10/2026

**311 testes distintos passaram nesta etapa:** 292 comuns em 137,90 segundos, dez cenários SQL principais em 727,194 segundos, três guardas PostgreSQL em 12,730 segundos e seis dublês de conexão em 0,007 segundo. Os 35 casos puros focais são subconjunto da suíte comum, não um acréscimo. A regressão SQL anterior de escrita não foi reexecutada inteira: o writer, pipeline, migrations e grants não mudaram.

A primeira execução SQL teve nove aprovações e uma falha no spy de storage compartilhado, que observava o escritor concorrente. O teste foi corrigido com um leitor exclusivo para o auditor; o recorte completo foi repetido sobre nova aprovação/carga real e passou com a implementação final. O caso histórico também comprovou cursor final antigo 2954 após avanço posterior a 2955. O teste concorrente comprovou snapshot estável em 2954 enquanto o escritor avançava a 2955, com I/O do auditor somente depois do fechamento SQL.

O relatório positivo final verificou os dois artefatos (histórico/JSON), um step e duas operações com cursor 2955, sem issues. Todos os fingerprints das tabelas e bytes do storage de teste ficaram iguais antes/depois. Os 79 arquivos protegidos anteriores permaneceram intactos, e a auditoria local anterior produziu o mesmo relatório healthy. Clusters descartáveis desligados; sem HTTP externo, banco operacional ou agendamento. [Evidência, histórico das execuções e hashes do código](../data/mega-sena-auditoria-sql-spec-0032.json).

## Única próxima tarefa recomendada

**SPEC-0033 — Comando manual seguro para sincronização PostgreSQL Mega-Sena.** Compor explicitamente auditoria, checkpoint aprovado, limites, espera real e transporte existente em uma entrada operacional opt-in, com testes e orientação de uso. Sem scheduler, credencial embutida, criação de baseline ou execução real de coleta como efeito da implementação. O serviço SQL já existe; uma entrada manual revisável deve preceder a automação. Não executada nesta tarefa.
