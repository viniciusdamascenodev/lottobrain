# Piloto de importação Mega-Sena — SPEC-0027

## O que está comprovado

O piloto importa somente as linhas **1, 2 e 2954** do XLSX qualificado (ou um subconjunto delas) e permite comparar/importar a fixture JSON do concurso 2954. Foi executado exclusivamente em PostgreSQL descartável, sob login ingestor restrito. Não é uma carga dos 2.954 concursos nem uma baseline materializada.

Não houve rede, novos resultados, banco operacional, modificação de raw, publicação, agendamento ou avanço de checkpoint. Casos de conflito/corrupção são mutações negativas explícitas de teste em storage temporário; não foram salvos em `data/raw`.

O arquivo XLSX completo de 221.261 bytes é arquivado como evidência por SHA-256; apenas as linhas selecionadas geram observações/revisões. Seu hash continua `0e1936e3ac94a35a89c13ef31d705d3fb363239779ad6224b5e41171a3238686`. Fixture JSON formatada não é promovida a bytes originais HTTP.

## Separação e reutilização

| Parte | Responsabilidade |
|---|---|
| `app/application/historical_pilot.py` | preparação limitada, manifesto, restauração a partir dos bytes e caso de uso por linha; porta de persistência, sem SQL |
| `app/application/mega_sena_bridge.py` | projeção transitória e decisão conservadora entre os dois contratos; sem merge e sem escrita |
| `app/infrastructure/postgres/historical_pilot.py` | registro legado, ledger por localizador, evidência, ponte sob lock e finalização |
| `app/infrastructure/postgres/draws.py` | escrita/leitura relacional compartilhada da Mega-Sena; contrato histórico habilitado apenas por parâmetro explícito |
| `app/infrastructure/postgres/catalog.py` | qualificação específica de fonte JSON ou XLSX; default JSON mantido |
| `tests/database/persistence_support.py` | harness isolado compartilhado, extraído dos testes anteriores para não duplicar preparação/segredos/roles |

Unidade de trabalho, retries de SQL abortado, storage imutável e disputa de alias via savepoint continuam reutilizados. Default do writer/leitor JSON mantém sua versão anterior. Não criar ORM genérico, novo parser, tabelas de lote ou framework para três linhas: a prova usa os campos existentes sem relaxar triggers. Migrations/head continuam `0024_03`.

## Plano e proveniência

`PreparedPlan`/`PreparedRow` são imutáveis; conteúdo/evidência são bytes JSON canônicos, não dicionários mutáveis compartilhados. Seleção fora de 1/2/2954 ou repetida é rejeitada. Para XLSX, hash integral deve corresponder ao raw qualificado; o leitor recebe BytesIO dos mesmos bytes arquivados, evitando troca do arquivo entre hashing e parsing.

O manifesto fixa origem, observação legada, raw SHA/tamanho, fonte, normalizador, código `spec-0027-v1`, política `mega-sena-historical-bridge-v1`, seleção, localizadores, contrato/hash de conteúdo e hash de evidência. A ordem canônica é a ordem dos registros emitidos pelo leitor, não a ordem dos argumentos. Relógio da inspeção não muda a identidade do plano.

Antes de executar, o plano é novamente reconstruído dos bytes e confrontado com o manifesto. Uma alteração manual no DTO/manifesto não permite importar outro conteúdo conservando o plano anterior. `restore_plan` também é usado na retomada.

O catálogo SQL qualificado tem fingerprint próprio, vinculado à intenção e ao receipt. Mesma chave com outra seleção/origem/entrada ou outro catálogo falha fechado. Arquivo igual em planos diferentes pode compartilhar raw e gerar receipts/observações distintos.

O receipt usa `capture_kind=legacy_import`, sem fetch_attempt/status HTTP, URL `urn:lottobrain:legacy:SHA` e `legacy_reference` versionada com manifesto, run e fingerprint do catálogo. `captured_at` aqui é registro local da importação, explicitamente **não** download original comprovado. Source config conserva a URL conhecida do catálogo, sem alegar que foi acessada.

## Transações e retomada

1. Preparar/validar em memória e PUT de bytes fora de SQL. PUT pode deixar bytes órfãos se o registro falhar; isso não fabrica receipt nem autoriza GET/reparo automático.
2. Registrar run/receipt idempotentes em uma transação curta, arbitrada pela chave da intenção. O manifesto fica persistido antes da primeira linha.
3. Para cada linha, verificar storage fora de SQL e abrir uma nova transação: lock da chave derivada de run/localizador, reconhecimento de identidade/draw, leitura do head verificado, receita na versão de saída, decisão, filhos/observação/tentativa e eventual selagem/head. Tudo dessa linha confirma junto.
4. Finalizar somente depois de comprovar tentativa para cada localizador do plano. Resultado completed se todas foram aceitas; stopped se houve quarentena. Interrupção deixa run running, sem alegar lote concluído.

Cada linha tem comando determinístico por run/localizador em processing_attempt. Repetição recupera a observação original antes de reconciliar de novo; não regride head nem recria tentativa/revisão. processing_run agrega a interpretação do receipt por versão de saída; pode ficar running enquanto o plano está incompleto, sem invalidar linhas já confirmadas. A finalização preserva finished_at original em replay.

`ImportHistoricalPilot.resume(source_key, key)` lê o manifesto/objeto registrados, fecha a transação, lê/verifica bytes do storage e reconstrói o plano. Não precisa do caminho XLSX original nem do objeto Python anterior. Storage ausente/corrompido impede retomada; o sistema não substitui evidência automaticamente.

Lock order deste caminho: chave de linha → draw/alias → receita **do piloto**. Receitas do piloto têm code/policy próprios, não compartilham o lock de receita JSON da SPEC-0025. Dois finalizadores do mesmo run são serializados; alias concorrente perde dentro de savepoint e não deixa draw órfão. A integração futura no coletor deve rever a ordem global de locks, não copiar este recorte sem análise.

Retry automático continua limitado a SQL comprovadamente abortado. Perda da resposta de COMMIT não dispara aquisição nem nova intenção: repetir a mesma chave ou usar resume. As provas injetam a perda **depois de COMMIT SQL real**; não simulam falha física de disco.

## Ponte conservadora

| Relação entre head e entrada | Decisão no piloto | Efeito |
|---|---|---|
| head inexistente | new | revisão no contrato da entrada |
| igual ou entrada parcial compatível | support / unchanged | observação de apoio; head e filhos intactos |
| entrada estritamente mais completa, compartilhado igual | enrichment / correction_candidate | nova revisão selada no contrato da entrada |
| compartilhado divergente ou remoção + acréscimo simultâneos | quarantined | conserva evidência/diagnóstico; não muda head; plano stopped |
| contrato desconhecido | erro explícito | rollback da linha, receipt preservado |

A projeção do JSON relacional v1 para o contrato histórico foi comparada à saída do normalizador real. Ela só existe em memória: não renomeia hash/versionamento das revisões seladas. Fatos known/unknown divergentes não são resolvidos automaticamente, mesmo que pareçam enriquecimento; correções reais exigem decisão posterior.

O SQL exige que versão/hash da observação de apoio coincidam com a revisão. Assim, ao apoiar JSON com XLSX, a receita/semantic_hash usam o **contrato/hash apoiado**, enquanto diagnostic_payload guarda separadamente input_contract/input_hash/input_content, evidência/hash, comparação, plano e política. A entrada histórica não desaparece nem recebe falsamente o hash do JSON.

Payload canônico por observação limitado a 32 KiB; não inclui o arquivo inteiro. Novos textos/locais/source_texts de uma captura de apoio ficam na observação/raw, sem UPDATE nos filhos imutáveis de uma revisão antiga.

No sentido XLSX→JSON, há duas revisões com seus hashes originais. No sentido JSON→XLSX, há uma revisão e duas observações. A ordem de extração `[2,6,1,5,3,4]` e demais enriquecimentos JSON permanecem intactos, inclusive sob corrida de fontes e replay antigo.

## Reprodução segura

No ambiente virtual, a partir da raiz:

```powershell
.venv\Scripts\python -m pytest tests/test_historical_pilot.py -q
.venv\Scripts\python scripts/database/run_integration.py --pg-bin .local-postgres\17.11-3\pgsql\bin
.venv\Scripts\python -m pytest tests --ignore=tests/database -q
```

O runner cria cluster PostgreSQL 17 dedicado em `.local-postgres/runs/UUID`, confirma sua identidade, usa login restrito no writer e o desliga ao terminar. Não executar descoberta unittest de database diretamente contra bancos existentes. Não foi adicionado comando de importação operacional ou DSN padrão. A API Python só foi exercitada no harness descartável; não constitui autorização para apontá-la a um banco operacional.

## Evidências e limites

Verificação final em 21/10/2026: **267 testes aprovados** — 191 comuns (dez novos) e 76 no runner isolado (71 PostgreSQL reais + cinco UoW simulados; 13 SQL novos). Tempo da suíte comum: 173,07 s; integração: 220,977 s. Não apresentar a exclusão de `tests/database` no pytest como execução implícita da integração: os dois comandos foram executados.

Log final: `.local-postgres/runs/a541a4c077374faca7cbf1816e473434/server.log`, com desligamento confirmado e sem postmaster.pid. Serviços PostgreSQL 12/13 existentes permaneceram Running. Hashes de 31 arquivos protegidos iguais antes/depois; auditoria anterior reproduzida exatamente/healthy. Dados, relatórios JSON e vetores anteriores não foram regravados.

`tests/database/test_historical_pilot.py` comprova: roundtrip do XLSX; JSON→XLSX sem alteração de filhos; XLSX→JSON e replay antigo; interrupção entre linhas; cinco falhas T3; perda de resposta de commit da linha e do registro; conflito financeiro em quarentena; mudança de catálogo; disputa entre fontes; duas retomadas concorrentes; reconstrução pelo manifesto persistido; corrupção recusada; gate do writer JSON existente.

Os 27 testes PostgreSQL anteriores do fluxo JSON continuam, após extrair apenas o harness comum. Regressões de integridade/permissões e UoW são executadas pelo mesmo runner. Esses testes usam fixtures reais e mutações negativas declaradas; não fazem GET de loterias.

Não comprovados: carga integral/desempenho de batch, perdas físicas de infraestrutura, publicação, baseline materializada, outras loterias ou operação em produção. legacy_reference textual/lookup por run é suficiente para este piloto pequeno, não decisão definitiva de indexação/gestão de lotes em escala. O storage atual limita artefatos a 256 KiB; XLSX deste recorte cabe, mas ampliar isso exigirá política explícita antes de outros históricos maiores.

**Gate preservado:** o coletor JSON da SPEC-0025 ainda recusa head histórico com outra canonicalization_version. A ponte só é ativada pelo caso de uso explícito do piloto. Não fazer carga integral enquanto importação e atualização incremental não tiverem política interoperável aprovada.

## Única próxima tarefa recomendada

Nota de evolução: a recomendação abaixo foi executada na SPEC-0028. O gate do writer JSON descrito como limite do piloto foi substituído pela [integração explícita e seus testes](ponte-ingestao-incremental.md); o importador piloto continua limitado. A sequência atual está no roadmap.

**SPEC-0028 — Integração da ponte XLSX/JSON ao fluxo incremental da Mega-Sena.**

Provar a atualização JSON sobre revisões históricas mantendo correções A→B→A, replay, identidade, catálogo, leases/cursor atômico e evidência por observação. Integrar por decisão explícita, não por troca de constante ou hash. Isso remove o gate real observado no teste 13 antes da carga completa; não foi executado nesta SPEC.
