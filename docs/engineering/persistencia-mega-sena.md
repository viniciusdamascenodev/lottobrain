# Persistência transacional Mega-Sena — SPEC-0025

## Resultado e limites

Existe um fluxo PostgreSQL **opcional**, separado dos coletores em arquivos. Usa os normalizadores e transporte já qualificados, sem editar o legado nem suas evidências. Implementa aquisição T1/T2, interpretação/reconciliação T3, avanço contíguo opcional e fechamento resumido T6. Não implementa scheduler/batch SQL, T4 administrativo, T5/publicação, importação histórica, API ou interface.

O schema continua comum às seis loterias. Este primeiro adaptador/mapper foi deliberadamente qualificado somente para o JSON Mega-Sena e sua regra atual documentada. Ele recusa catálogo incompatível, em vez de presumir que regras desconhecidas funcionam. Não é um cadastro universal de modalidades e não habilita SQL para as outras cinco automaticamente.

## Separação de responsabilidades

| Local | Responsabilidade |
|---|---|
| `app/application/persistence.py` | portas, DTOs, erros estáveis e retry de transação abortada |
| `app/application/mega_sena_content.py` | representação canônica relacional, versão e hash; sem SQL |
| `app/application/persist_mega_sena.py` | CaptureMegaSena, ProcessMegaSena e orquestração manual |
| `app/infrastructure/postgres/catalog.py` | qualificar definições SQL contra o normalizador suportado |
| `…/captures.py` | tentativa, artefato, receipt e resumo |
| `…/processing.py` | receita, chave de comando, tentativa, observação/quarentena |
| `…/draws.py` | identidade, revisão/filhos, hash e leitura de verificação |
| `…/sync.py` | lease, token, CAS, passo e cooldown |
| `…/uow.py` | conexão única/commit/rollback/close e tradução segura de erros |
| `app/infrastructure/raw_storage.py` | objetos imutáveis por SHA-256; nenhuma metadata de captura |
| `app/interfaces/collect_mega_sena_postgres.py` | CLI opt-in, configuração explícita e resultado seguro |

Repositórios compartilham a conexão da unidade de trabalho; não confirmam transações nem chamam rede/storage. A aplicação depende das portas, não de Psycopg/SQLAlchemy. Não foi criado ORM paralelo ao DDL existente. Nenhuma migration 0024 foi alterada; o recorte coube nas 27 tabelas já disponíveis.

## Sequência implementada

```text
T1: qualificar catálogo → chave de aquisição → tentativa → commit/close
    GET único com timeout, sem conexão SQL aberta
    PUT de bytes imutáveis, sem conexão SQL aberta
T2: registrar artefato/receipt + resposta da tentativa → commit/close
    ler/verificar bytes, normalizar e canonicalizar fora de transação
    se 429: cooldown independente, quando houver checkpoint
T3: chave de processamento → checkpoint → receita → draw → conteúdo
    observação + selo + passo/cursor (se solicitado) + tentativa → commit/close
T6: fechar resumo da aquisição em transação curta
```

Falha sem corpo confirma a tentativa como transport_error e execução failed, sem raw/receipt fictícios. HTTP de erro com corpo conserva artefato e captura e produz observação em quarentena; código/field_path são guardados, e o conteúdo original continua no raw. Não há publicação implícita.

Somente um receipt SQL HTTP registrado por este fluxo é aceito pelo processador atual. Receipts locais/legacy_import e XLSX serão tratados pelo incremento de importação com proveniência própria; não são reconstruídos como GETs históricos.

## Comandos e retomada

Pré-requisitos: PostgreSQL com migrations 0024 em head; catálogo Mega-Sena/escopo common_result/três faixas/fonte JSON qualificados; login membro de `lottobrain_ingest`, nunca proprietário/superuser; raiz de objetos nova e dedicada. O coletor **não** cadastra catálogo nem cria baseline. Nenhum banco operacional foi preparado nesta tarefa: exemplos abaixo são instruções para uso posterior, não comandos já executados contra a CAIXA.

Definir `LOTTOBRAIN_PG_DSN` por mecanismo seguro de ambiente (`postgresql://…`). Não confundir com `LOTTOBRAIN_DATABASE_URL` do Alembic (`postgresql+psycopg://…`). Não versionar DSNs/senhas.

```powershell
# Uma intenção manual; reutilizar a mesma chave para recuperar confirmação perdida.
.venv\Scripts\python -m app.interfaces.collect_mega_sena_postgres --contest 2954 --command-key CHAVE-UNICA --object-root data/postgres-artifacts

# Replay de receipt SQL existente, sem GET. Nova chave = tentativa intencional distinta.
.venv\Scripts\python -m app.interfaces.collect_mega_sena_postgres --replay UUID-DO-RECEIPT --command-key OUTRA-CHAVE --object-root data/postgres-artifacts
```

Sem `--contest`/`--replay`, consulta somente o último resultado, um GET. Não há loop de downloads ou scheduler. Códigos de saída: 0 resultado aceito, 2 quarentena, 1 falha. CLI não oferece avanço de checkpoint nem imprime SQL, DSN, resposta arbitrária da rede ou traceback de driver. UUIDs/código de resultado são a saída operacional.

Raiz de objetos não pode ser repositório, `data/raw` ou `data/collections`. A raiz nova padrão dos exemplos fica no Git ignore. Ela é configuração de infraestrutura **única por banco**; não alternar raízes entre execuções como se fossem storage intercambiável. Object keys são relativas por hash; namespace/backends compartilhados/S3 serão qualificados antes de produção.

### Semântica das chaves

- Chave de aquisição: deduplica intenção de GET por fonte/parâmetro; mesma chave com outro concurso é idempotency_conflict.
- Chave de processamento: deduplica receipt/receita/contexto de avanço. Reutilização após commit ambíguo retorna o efeito confirmado, sem nova observação/revisão/passo. Alteração de receipt, receita/catalog fingerprint ou contexto de avanço é conflito, não outro pedido silencioso.
- Mesma receita com **nova chave** registra outra tentativa e retorna replay da observação antiga, sem comparar o raw antigo com o head atual.
- Nova captura intencional usa outra chave; mesmos bytes conservam outro receipt e observação, mas podem reutilizar revisão idêntica.
- Tentativas abortadas sem efeito confirmado não reservam uma chave em ledger externo: persistir um registro parcial separado destruiria a atomicidade pretendida. Retomar preservando a intenção original; para outra intenção, sempre gerar outra chave.

Receita identifica receipt + adapter/code/canonicalization/validation versions + catalog fingerprint, sem fingir commit Git desconhecido. Versões locais explícitas acompanham o código; nova semântica exige nova versão e vetores. Mudança de configuração pode exigir nova chave de processamento, não reaproveitamento de comando antigo para uma nova interpretação.

## Concorrência e correções

READ COMMITTED e locks curtos. Ordem: comando → checkpoint (quando necessário) → receita → draw → filhos. O lock consultivo de comando é uma otimização de arbitragem; UNIQUEs continuam a proteção física. Colisões do hash de lock apenas serializam pedidos extras; não fazem dois pedidos parecerem iguais.

Para nova identidade, criar o agregado dentro de savepoint e só depois disputar o alias oficial. Perdedor desfaz draw/revisão/filhos/observação daquele savepoint e recarrega o vencedor sob lock. A referência externa é registrada **depois** da disputa do alias, para não criar uma segunda disputa antes do ponto de arbitragem.

Revisões são comparadas somente depois de travar o draw. Conteúdo A→B→A admite revisões 1/2/3; hashes repetidos em ocorrências diferentes não são UNIQUE globais. Um replay da receita A original retorna a revisão 1 e não troca o ponteiro atualmente na revisão 2/3. Observações e tentativas registram esses fatos separadamente. `processing_run.finished_at` original não é reescrito por replay.

O hash do head é conferido contra sua reconstrução tipada antes de compará-lo. Head de canonicalização legada/desconhecida retorna canonicalization_conflict: não é renomeado como v1 nem conciliado por suposição.

Retry limitado a três transações SQL completamente abortadas por conflito conhecido (40001, 40P01 ou lock timeout 55P03), sem repetir GET/PUT. Conflitos de integridade/identidade não são retentados genericamente. Falha de conexão/retorno de COMMIT incerto é `commit_outcome_unknown`; o chamador repete a mesma intenção/chave, não inicia novo download. A unidade fecha a conexão em finally, inclusive quando commit/rollback falham.

## Continuidade opcional (porta da aplicação)

Após baseline/checkpoint SQL previamente aprovados, o orquestrador pode chamar `claim_lease` e passar `Advance(checkpoint_id, expected_cursor, lease_token)` a ProcessMegaSena/CollectMegaSenaPostgres. A lease é de 5–300 segundos; padrão 300, clock do banco. Lease ativa gera lease_busy; não é roubada nem renovada implicitamente. Commit ambíguo ao reivindicar lease requer investigação/espera pela expiração, não takeover imediato.

O worker conserva a intenção para retries. Avanço exige identidade oficial `expected_cursor+1`, fonte compatível, token atual e validade no início e no commit; UPDATE usa cursor/token/row_version em CAS. Uma descoberta isolada não avança; sua observação pode ser reutilizada numa transação posterior de avanço. Observação, revisão nova, passo e cursor confirmam juntos ou nada confirma.

Lease perdida não elimina T2: bytes e receipt já estão preservados e podem ser reprocessados por um worker legítimo. Quarentena nunca cria passo. O controlador em arquivos e seu cursor não são reaproveitados diretamente como se estivessem no mesmo UnitOfWork.

429 alimenta cooldown por 15 minutos em transação própria quando há checkpoint. Mesmo sem checkpoint, a captura 429/finished_at confirmada é consultada antes de aceitar nova intenção de GET da fonte. Replay offline e recuperação de comando já confirmado continuam permitidos. Não se apresenta esse intervalo como limite oficial da CAIXA nem autorização para automação recorrente.

## Canonicalização v1

Versão: `lottobrain.mega_sena.result.v1`. UTF-8, JSON compacto com chaves ordenadas, arrays em ordem definida; dinheiro decimal como string sem zeros fracionários irrelevantes; sem float/NaN. UUIDs SQL, capture time, URLs, raw hash e source_text monetário não definem o conteúdo. Eles continuam na cadeia de proveniência/evidência.

Conteúdo inclui loteria, número oficial, data, versão da matriz, séries/componentes, ordinais canônicos e de extração opcionais, escopo/forma de pagamento/status/moeda, faixas/ganhadores e metadados normalizados. Alteração de ordem de extração é mudança de conteúdo. Sem prova de extração, ordinal continua null. Snapshot do número oficial da revisão fica na chave reservada `_canonical_identity` dos metadados SQL; a projeção canônica o reconstrói separadamente. Não depende de um alias que futuramente possa ser corrigido/desativado.

Vetor fixado em `tests/fixtures/mega_sena_relational_v1.json`, a partir do JSON real 2954 já existente:

- fixture de entrada formatada: SHA-256 `b248665f1736f655b190f1ce143371108781aaf90bd2150ea7832522f072ec85`;
- hash canônico esperado: `62755ae7c8057839aa4fcb97c2840afbc6e0a296844f7b02fb6d66f81bbe6477`;
- números: 1, 9, 37, 39, 42, 44; posições de extração: 2, 6, 1, 5, 3, 4;
- prêmio Sena conhecido zero e moeda BRL são preservados; desconhecido é amount/currency null, nunca zero.

A fixture formatada não é o wire original de 1750 bytes; seus hashes não são intercambiáveis. Hashes semânticos legados dos arquivos existentes permanecem intocados. Este vetor não qualifica ainda XLSX Mega-Sena nem as outras cinco loterias; antes de importar, qualificar os respectivos mapeamentos/vetores e estados de ausência.

## Falhas e recuperação

| Ponto | Evidência persistente / ação |
|---|---|
| T1 falhou antes do commit | mesma chave pode iniciar sem efeito anterior |
| T1 confirmado, GET/PUT interrompido sem receipt | capture_in_progress; não repetir GET nem inventar captura. Investigar; nova intenção explícita para recapturar |
| PUT feito, T2 ausente | objeto pode ser órfão; conservar e auditar. Bytes sozinhos não recuperam horário/status HTTP perdido |
| T2 confirmou mas resposta do commit se perdeu | repetir mesma chave encontra receipt e não faz GET |
| Parsing/T3 falhou | receipt/bytes permanecem; replay com intenção preservada |
| T3 confirmou mas resposta do commit se perdeu | mesma chave retorna revisão/observação/passo já confirmados |
| Lease expirou/token mudou | nenhum avanço; worker legítimo reprocessa receipt com novo contexto/chave |
| Falha no resumo T6 | repetir comando recupera resultado; resumo não substitui observação/passo |

Não há reparador/varredura automática de objetos SQL nesta etapa. Não apagar órfãos ou fabricar receipts para “fechar” o fluxo. Procedimentos de auditoria/retencão/restauração desse storage precisam ser qualificados antes da troca operacional. Hardware/falha de disco e COMMIT que realmente respondeu com timeout de rede não foram provocados fisicamente: testes injetam essas falhas de forma controlada.

## Verificação e referências

Executar a suíte isolada documentada na [operação de migrations](../database/migrations-ingestao.md). As bases dos novos casos são clones de um template de catálogo descartável, nunca de banco do usuário. Usam login lb_test_ingestor, não o proprietário; fakes de rede transportam fixtures, sem acessar loterias. Correções, 404/429 e fronteiras de baseline são simulações explícitas, não novos dados históricos verdadeiros.

O executor foi ajustado a 32 MiB de shared_buffers/20 conexões e até 55 s para desligamento: a multiplicação das bases descartáveis aumentou o checkpoint de shutdown no Windows. fsync continua habilitado. Não foi alterada configuração de serviço existente.

Referências primárias: [Psycopg — transações](https://www.psycopg.org/psycopg3/docs/basic/transactions.html), [PostgreSQL 17 — isolamento](https://www.postgresql.org/docs/17/transaction-iso.html), [INSERT/ON CONFLICT](https://www.postgresql.org/docs/17/sql-insert.html). O comportamento qualificado é demonstrado nos testes com Psycopg 3.3.6/PostgreSQL 17.11, não inferido apenas da documentação online.

Resultados e cobertura: [verificação SPEC-0025](../database/verificacao-spec-0025.md).

## Evolução na SPEC-0028

O fluxo incremental agora usa código/política próprios para interoperar com head histórico qualificado, sem alterar o contrato/hash JSON v1 descrito acima. Preserva comandos/receitas anteriores como replay e registra evidência por observação. Divergência entre contratos confirma quarentena sem avanço; correções JSON→JSON continuam permitidas. [Política atual, compatibilidade e provas de continuidade](ponte-ingestao-incremental.md). Isso não materializa automaticamente históricos/baselines nem ativa produção.
