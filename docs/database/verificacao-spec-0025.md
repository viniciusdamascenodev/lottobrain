# Verificação da SPEC-0025

## Ambiente e execução

21/10/2026 (America/Sao_Paulo). Python 3.12, PostgreSQL 17.11, Psycopg 3.3.6 e migrations head `0024_03`; nenhuma migration alterada/criada neste incremento.

- Suíte comum final: **157 testes aprovados** (92,19 s), sendo 148 anteriores e nove de canonicalização/storage/CLI.
- Suíte isolada final: **63 testes aprovados** (119,904 s): 31 de integridade SQL, 27 casos de uso PostgreSQL e cinco de ciclo de vida com conexão simulada.
- Total: **220 testes aprovados**, sem warnings de conexão aberta. As duas execuções terminaram com código 0; runner confirmou também o desligamento do cluster.
- Log final local: `.local-postgres/runs/4f9ce5e3439b429aa741b3dba4cd36f2/server.log`. Logs/dados de teste ignorados pelo Git, não banco operacional.
- `compileall`, links internos e `git diff --check` verificados; aviso de CRLF em requirements.txt é preexistente, arquivo não editado nesta tarefa.

Comandos reproduzíveis: `python scripts/database/run_integration.py --pg-bin CAMINHO/bin` no ambiente virtual e `python -m pytest tests --ignore=tests/database -q`. São dois comandos: não apresentar exclusão dos testes database no pytest como aprovação implícita da integração.

Cada caso novo usa clone de catálogo em banco descartável dedicado. As bases não são clones de banco do usuário; o template é criado do zero neste mesmo cluster. Login da aplicação `lb_test_ingestor`, sem propriedade das tabelas, superuser, criação de banco ou papel. Administrador cria somente o ambiente de testes; aplicação não usa suas credenciais.

Nenhuma requisição foi enviada à CAIXA ou a outras loterias. Fakes de transporte usam fixture real e mutações/situações de falha explicitamente marcadas como teste. COMMIT perdido é injeção **após commit SQL real**; não foi desconectado fisicamente o servidor nem simulada perda de disco.

## Casos executados

Números abaixo referem-se a `tests/database/test_postgres_ingestion.py`:

| Testes | Evidência |
|---|---|
| 01 | T1–T3/T6, login restrito, roundtrip/hash do vetor e nenhuma publicação |
| 02–03 | mesma chave retorna efeito anterior sem GET; parâmetros/receipt diferentes produzem conflito |
| 04 | um raw, duas capturas e observações, uma revisão idêntica |
| 05 | A→B→A e replay antigo; head e instante original da interpretação não regridem/mudam |
| 06–07 | quarentena sem draw fictício; transporte sem corpo não cria raw/receipt nem repete GET |
| 08 | GET, PUT e leitura de bytes com conexões SQL já fechadas; T1 visível em outra conexão |
| 09–10 | avanço atômico e retry idempotente; falhas em revisão, filhos, observação, passo, cursor e pré-commit revertem T3 inteiro |
| 11 | duas conexões disputam o mesmo alias real; savepoint perdedor não deixa draw/revisão órfãos |
| 12 | resposta de commit T3 perdida; mesma chave recupera único efeito confirmado |
| 13 | correções distintas serializadas; segunda conexão observada bloqueada por pg_blocking_pids antes de liberar a primeira |
| 14 | duas chaves disputam mesma receita: uma observação/revisão, duas tentativas |
| 15–16 | token vencido/lease ocupada/CAS de cursor incorreto; captura mantida sem avanço |
| 17 | descoberta não avança; a observação pode ser reutilizada no avanço posterior |
| 18–19 | 429 persiste cooldown apesar de T3 falhar; novo GET bloqueado; 404 com corpo permanece em quarentena |
| 20 | retry limitado a três abortos SQL conhecidos, sem GET/PUT adicionais |
| 21–22 | objeto ausente/corrompido e catálogo incompatível impedem processamento; catálogo inválido falha antes do GET |
| 23–24 | lease perdida no commit reverte agregado/cursor; 429 sem baseline também impede nova aquisição |
| 25–26 | PUT órfão não fabrica receipt nem repete GET; T2 confirmado/retorno perdido retoma sem nova captura |
| 27 | desconhecido e zero conhecido sobrevivem ao roundtrip relacional sem conversão silenciosa |

Corridas usam Barrier/Event e estado real de locks, com limites de espera. O polling de `pg_blocking_pids` verifica a condição; não presume que um sleep tenha criado a corrida. Retry por deadlock/serialization e perda de lease no fim são injeções identificadas; a serialização de identidade/correções foi observada em conexões reais.

`test_uow_lifecycle.py` complementa os testes reais: fechamento em sucesso, corpo com erro, rollback que falha, rejeição no commit, conexão perdida no commit e erro na inicialização. Não contabilizar seus cinco casos simulados como prova física de PostgreSQL.

## Evolução da matriz DB-01…DB-37

A cobertura SQL da [SPEC-0024](verificacao-spec-0024.md) permanece. Aqui só avançam os pontos comprovados no fluxo JSON Mega-Sena; os demais contextos/fontes não estão automaticamente qualificados.

| DB-ID | Situação após SPEC-0025 |
|---|---|
| DB-01/03/06–16/35 | proteção física anterior mantida; roundtrip e operação com login não proprietário acrescentados |
| DB-02 | pendente para conciliação de fontes diferentes; o processador atual aceita somente fonte JSON qualificada |
| DB-04/05 | pendentes: identidade por slot e alteração administrativa de alias/data |
| DB-17/18 | comprovados no adaptador local/T1–T3 com transporte simulado; storage externo/HTTP real não exercitados |
| DB-19 | retry com chave após commit real/retorno perdido, testes 02/09/12/26 |
| DB-20/21 | replay antigo/A→B→A, testes 05/17; correções são simulações declaradas |
| DB-22/23 | concorrência real de duas conexões, testes 11/13/14, sem draw órfão/publicação |
| DB-24 | falhas controladas em todas as escritas de T3 e retomada idempotente, testes 09/10/12/23 |
| DB-25/26 | candidato adiantado, CAS e fencing, testes 15/16/17/23 |
| DB-27 | 429/cooldown independente e bloqueio de GET, testes 18/24; intervalo operacional de 15 min, não SLA oficial |
| DB-28 | publicação continua bloqueada por CHECK/privilégio; T5 não implementado |
| DB-29/30 | pendentes: decisões/publicação/audit_event/outbox/consumidor |
| DB-31 | baseline apenas referenciada nos testes; materialização/importação operacional pendente |
| DB-32 | workspace local não importado; permanece íntegro e separado |
| DB-33 | vetor v1 e roundtrip **JSON Mega-Sena** comprovados; hashes legados preservados. XLSX Mega-Sena e outras cinco modalidades ainda precisam de vetores próprios |
| DB-34 | importação de linhas XLSX/duplicatas sem identidade continua pendente |
| DB-36 | snapshots/backtests temporais continuam pendentes |
| DB-37 | fingerprint de intenção e conflito de reutilização comprovados, testes 03/09 |

Não existe ainda ambiente de staging, CI/CD obrigatório, benchmark de carga, teste físico de falha de disco/rede, restauração de backup nem aprovação de coleta recorrente. Nenhum desses itens é inferido apenas da aprovação de testes locais.

## Preservação

Auditoria SPEC-0022 reproduzida exatamente, status healthy, sem erros/avisos. Manifesto permanece `01c1e25c4cedc3e63b05aef2356bc28fdd18e2dc3a0188c5f790fc799a335324`: baseline 2954, cursor 2955, candidatos 2954/2955/3071, somente candidatos. Maior concurso salvo não significa último sorteio online; fonte não reconsultada.

Os hashes dos seis históricos raw coincidem antes/depois com o inventário anterior. Dados de coleta, relatórios anteriores, migrations 0024 e `requirements.txt` não foram editados. Serviços `postgresql-x64-12`/`postgresql-x64-13` permanecem Running e não foram alvos de conexão do projeto.

Binários PostgreSQL já disponíveis e dependências fixadas foram reutilizados. Não houve instalação de serviço, importação/cadastro operacional ou novas bibliotecas. Artefatos/binários/bases de testes locais ficam ignorados pelo Git; temporários de objetos são descartados pelos testes. A primeira rodada de 43 testes aprovou a suíte mas ultrapassou 30 s de shutdown do harness; o log confirmou desligamento posterior. O executor passou a ter buffers menores e até 55 s para desligar, sem desabilitar fsync.

## Próxima tarefa única

**SPEC-0026 — Qualificação da importação histórica: mapeamentos e vetores das seis loterias.**

Definir e provar a tradução dos históricos reais para o modelo relacional, inclusive diferenças de dinheiro, escopo, versões, IDs provisórios, Double Play e símbolos, sem executar carga em massa. Incluir Mega-Sena XLSX versus JSON e manter fatos comuns distintos de metadados exclusivos. Qualificar vetores/hashes/estados de ausência e o plano de importação auditada antes de mover os arquivos existentes ao banco.

Justificativa: a escrita vertical já tem garantias; a próxima lacuna é a representação fiel das seis fontes históricas. Importar agora por conveniência reutilizando um mapper só de Mega-Sena JSON perderia diferenças já descobertas. Não executada nesta tarefa.
