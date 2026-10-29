# Verificação da SPEC-0024

## Execução

Data: 21/10/2026 (America/Sao_Paulo). Ambiente: Python 3.12, PostgreSQL 17.11 Windows, Psycopg 3.3.6, SQLAlchemy 2.0.55, Alembic 1.20.0.

- Suíte existente: **148 testes aprovados**, `pytest tests --ignore=tests/database -q`, 116,99 s.
- Integração: **31 testes aprovados** em PostgreSQL 17.11, 17,264 s, sem ResourceWarning na rodada final. Total das duas suítes: **179 testes aprovados**.
- Log final: `.local-postgres/runs/f795aff6252f416fa2b2053696268725/server.log`; dados/logs locais descartáveis, ignorados pelo Git. Runner terminou com código 0 após desligar o cluster.
- `compileall` das migrations/executor/testes e `git diff --check` sem erros; aviso de CRLF em `requirements.txt` é preexistente.

Integração usa PostgreSQL real, não SQLite/mocks de driver. O dono do DDL é não superuser; o administrador fica restrito ao bootstrap. Testes comuns usam transação revertida; os de commit/rollback/materialização criam bases próprias dentro do mesmo cluster descartável. Nenhum banco operacional foi criado ou alimentado. Execução sem ambiente de integração é erro, não skip aprovado.

## Evidência de compatibilidade

O teste `test_02` grava, sela e valida uma fixture real de **cada uma das seis loterias** na mesma estrutura. O catálogo de teste contém as 20 versões já definidas, incluindo fronteiras de Powerball, Mega Millions e EuroMillions. Power Play é atributo, Double Play é outra série; estrelas e trevos são componentes, não colunas exclusivas. EuroMillions mantém flag booleana e escopo de provedor PT/ES, sem inventar quantidade de ganhadores ou país.

As capturas dos testes identificam a origem como fixture/legacy_import e usam relógio de teste explícito, não o apresentam como instante original de download. O caso HTTP 404 é metadado **simulado** sobre bytes reais apenas para exercitar relações SQL, sem consultar fonte nem inventar um resultado operacional. Baselines de transição e mutações inválidas são cenários técnicos de teste, não auditorias de históricos aprovadas para importar.

## Cobertura da matriz da SPEC-0023

`test_NN` refere-se a `tests/database/test_integrity.py`. **SQL** significa garantia física exercitada; **parcial** não significa cenário completo aprovado. A matriz original permanece como contrato histórico, com este relatório de execução vinculado.

| DB-ID | Estado e evidência | O que ainda falta |
|---|---|---|
| DB-01 | SQL, test_03 | tradução do conflito pelo adaptador |
| DB-02 | pendente | conciliação entre fontes no repositório |
| DB-03 | SQL, test_03 | uso das referências pelo repositório |
| DB-04 | pendente; não há UNIQUE global de data | teste de identidade qualificada por slot |
| DB-05 | pendente | correção de data e decisão de alias |
| DB-06 | SQL, test_04 e seed das 20 regras | política de evolução operacional do catálogo |
| DB-07 | SQL, test_06 | comando administrativo auditado |
| DB-08 | SQL, test_07 e test_23 | mapeamento de erros no adaptador |
| DB-09 | SQL, test_08/test_25/test_27; domínio já testado | vetores relacionais por versão antes da carga |
| DB-10 | SQL, test_05 | ativação administrativa auditada |
| DB-11 | SQL, test_09 e commit real test_22 | UoW do caso de uso |
| DB-12 | SQL, test_10 e test_25 | observações/revisões via repositório |
| DB-13 | SQL, test_11 | roundtrip do mapper monetário |
| DB-14 | SQL, test_12 | envelope específico de cada adaptador |
| DB-15 | SQL, test_13 | qualificação de escopos/payout na carga |
| DB-16 | SQL, test_13 | política de medidas no mapper |
| DB-17 | parcial, test_14 | storage real e deduplicação via porta |
| DB-18 | parcial, test_24 | GET real/falha/quarentena pelo caso de uso |
| DB-19 | parcial, UNIQUE em test_28 | retorno idempotente após timeout de commit |
| DB-20 | pendente | replay antigo sem regressão de ponteiro |
| DB-21 | parcial, test_29 permite repetição de hash | reconciliação real A→B→A |
| DB-22 | pendente | duas conexões, corrida mesma identidade/conteúdo |
| DB-23 | pendente | serialização de correções concorrentes |
| DB-24 | parcial, test_17 e test_22 | UoW, falhas em cada fronteira e retry |
| DB-25 | parcial, test_16 | ingestão real de candidato adiantado |
| DB-26 | parcial, test_18 | duas conexões e comando com fencing/CAS |
| DB-27 | parcial, test_31 | resposta 429 integrada ao cooldown SQL |
| DB-28 | parcial, test_23/test_26 e papel restrito | T5; publicação permanece bloqueada |
| DB-29 | pendente | decisão/publicação/auditoria/outbox atômicos |
| DB-30 | pendente | outbox e consumidor idempotente |
| DB-31 | parcial, test_17 | importação e manifesto de materialização |
| DB-32 | pendente | importação do workspace auditado |
| DB-33 | pendente; hash legado tem versão explícita | representação relacional e vetores das seis modalidades |
| DB-34 | parcial, unicidade de posição em test_28 | importar duplicatas/quarentena reais sem perda de linhas |
| DB-35 | SQL, test_15/test_19/test_30 | retenção/restauração operacional autorizada |
| DB-36 | pendente | snapshots analíticos temporais |
| DB-37 | parcial, chave única/contexto imutável | comparar request_hash e retornar idempotency_conflict |

Não houve testes de concorrência de escritores sincronizados com duas conexões nesta etapa. Os testes de commit usam conexões reais, mas isso não autoriza declarar resolvidas corridas de repositórios. Nenhum dos itens de publicação, importação e análises foi implementado por antecipação.

## Preservação

Auditoria offline continuou `healthy`, sem erros/avisos; JSON reproduzido exatamente igual ao salvo na SPEC-0022. Manifesto: `01c1e25c4cedc3e63b05aef2356bc28fdd18e2dc3a0188c5f790fc799a335324`.

Permanecem baseline 2954, cursor 2955 e candidatos 2954/2955/3071. Fonte online não foi reconsultada; o maior concurso salvo não é afirmação de atualidade. Hashes SHA-256 dos seis arquivos raw foram conferidos antes/depois e coincidem com o inventário anterior. Nenhum raw, receipt, revisão local, relatório de qualidade anterior ou pipeline foi modificado.

Serviços existentes `postgresql-x64-12` e `postgresql-x64-13` continuam Running, sem conexão de aplicação/migration a eles. O cluster de teste termina desligado; logs/dados descartáveis e binários ficam em `.local-postgres/`, ignorado pelo Git. Não há senha versionada. O `requirements.txt` preexistente não foi editado. Arquivos/alterações anteriores foram preservados.

## Próxima tarefa única

**SPEC-0025 — Persistência transacional da Mega-Sena: repositórios e unidade de trabalho.**

Implementar o primeiro adaptador PostgreSQL sobre o schema comprovado, com mapper/canonicalização versionada do recorte, T1–T3, resolução de identidade, replay/idempotência, concorrência com duas conexões e cursor/observação/revisão na mesma transação. Coleta externa continua fora da transação SQL. Não fazer carga histórica em massa nem publicação nesse incremento.

Justificativa: uma estrutura íntegra ainda não é um fluxo operacional persistente. Validar primeiro a escrita vertical e suas falhas evita migrar históricos para um adaptador cuja atomicidade não foi demonstrada. Vetores relacionais das demais modalidades seguem como gate antes de suas cargas; importação auditada e T5 virão depois.
