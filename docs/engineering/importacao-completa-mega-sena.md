# Importação completa Mega-Sena — SPEC-0029

## Recorte e separação de responsabilidades

Carga exclusivamente controlada do raw Mega-Sena já qualificado: **2.954 registros, concursos 1–2954, 11/03/1996–20/12/2025**, arquivo integral de 221.261 bytes e SHA `0e1936e3ac94a35a89c13ef31d705d3fb363239779ad6224b5e41171a3238686`.

O piloto mantém seu limite de três linhas. A carga completa tem plano/caso de uso próprios, não uma flag que remove silenciosamente o limite do piloto. Nenhuma nova coleta, modalidade, baseline carregada, checkpoint, publicação ou banco operacional faz parte desta entrega.

| Parte | Responsabilidade |
|---|---|
| `app/application/historical_import.py` | plano completo imutável, manifesto compacto em cache, reconstrução e orquestração por registro |
| `app/application/historical_coverage.py` | diagnóstico determinístico de cobertura/evidência, recebendo snapshot já reconstruído |
| `app/infrastructure/postgres/historical_import.py` | perfil completo, pendências por ledger, auditoria snapshot e finalização condicionada à cobertura |
| `app/infrastructure/postgres/historical_pilot.py` | registro/ledger/escrita conservadora compartilhados; perfis explícitos distintos de piloto e carga completa |
| `app/infrastructure/postgres/content_reader.py` | reconstrução do conteúdo a partir das tabelas relacionais, em lote e com conferência dos hashes |

Reutilizados: leitor/normalizador existente, PreparedRow, ponte conservadora, unidade de trabalho, storage por hash, aliases/savepoint, escrita e selagem. Sem novo parser, ORM/broker, dependency ou migration. Os contratos/hashes canônicos anteriores permanecem; código da carga é `spec-0029-v1`.

## Plano e manifesto

HistoricalImportPlan aceita somente o checksum aprovado e exatamente 2.954 registros, com locator `data_record:N` e concurso N sem lacuna, repetição ou reordenação. O período também é conferido. Preparação/reconstrução usam BytesIO dos mesmos bytes arquivados, fora de SQL.

O manifesto fixa origem legada, raw SHA/tamanho, fonte, normalizador, código/política, canonicalização, intervalo e `records_manifest_sha256`. Este último é calculado sobre a sequência completa de localizador, concurso, hash de conteúdo e hash de evidência. Os detalhes de cada linha ficam no raw e nas observações; não se duplica um manifesto enorme em cada receipt.

O JSON compacto do manifesto e seu fingerprint são calculados **uma vez**, em um plano imutável. Serializar os 2.954 registros em cada T3 seria custo quadrático. A propriedade manifest devolve cópia, e a execução reconstrói o plano a partir do raw antes de aceitar seus hashes; um DTO editado não é uma autorização para outro conteúdo.

Registro legado conserva instante local de importação, explicitamente diferente de um horário original de download não comprovado. Não inventar GET/status HTTP para esses arquivos. Chave da intenção continua vinculada ao manifesto e fingerprint de catálogo; tentar usar uma seleção piloto na mesma chave da carga é conflito.

## Escrita, progresso e retomada

1. Preparar/reconstruir input e fazer PUT fora de SQL.
2. Registrar run/receipt/manifesto, com `mode=historical_import`.
3. Consultar o ledger do receipt de uma só vez e selecionar pendências por comando determinístico de run/localizador. Não usar max(concurso), contagem de revisões ou o resumo do processo como cursor da carga.
4. Confirmar **uma linha por transação**, com sua evidência/observação/revisão/filhos/tentativa atômicos. Uma falha não apaga registros anteriores nem anuncia o arquivo completo.
5. Verificar a integridade do objeto antes de cada bloco (padrão 50, limite 1–100) e antes de finalizar. Bloco aqui limita I/O/verificação, não é uma transação SQL de 50 linhas.
6. Auditar a cobertura e só então finalizar. `completed` exige diagnóstico qualificado; falhas/quarentenas resultam stopped ou erro explícito, nunca promoção de sucesso.

`resume(key)` recupera manifesto/objeto registrados, fecha a transação, lê/verifica o storage e reconstrói o plano. Não requer caminho original XLSX nem objeto Python anterior. Com carga já concluída, consulta pendências em lote, não reexecuta 2.954 T3; nova auditoria confirma o estado e finished_at fica estável.

Retomada não é uma autorização permanente de escrita: `register/process` continuam qualificando o catálogo atual. Mudança de fingerprint exige outra decisão explícita/intenção, não reutilização silenciosa da chave anterior. Fonte bloqueada impede retomada mesmo que seus bytes históricos ainda sejam válidos.

O storage atual suporta esse arquivo de 221.261 bytes dentro do limite de 256 KiB. Nenhum limite HTTP global foi aumentado. Integridade é verificada por blocos e na auditoria, não se promete atomicidade entre filesystem e PostgreSQL. Corrupção/ausência de bytes requer investigação; não existe reparo automático ou substituição do raw.

## Auditoria e finalização

`audit(key)` reconstrói o plano dos bytes arquivados e executa consultas em **REPEATABLE READ READ ONLY**. A finalização usa snapshot REPEATABLE READ e lock do run. Assim, observações, aliases e revisões não são combinados de instantes inconsistentes enquanto outro fluxo pode atualizar o head.

A auditoria verifica por localizador:

- presença única da observação; decisões aceitas versus quarentena;
- comando/tentativa, request hash, receita, código, normalizador, fingerprint e política;
- número oficial/alias ativo do mesmo draw;
- payload versionado, contrato/hash de entrada e evidência, confrontados com normalização dos bytes;
- revisão apoiada selada, versão/hash de suporte e conteúdo efetivamente relacional;
- head existente e com hash relacional verificado; nenhuma publicação indevida;
- registros e comandos ausentes, inesperados, duplicados ou inconsistentes;
- manifesto observado dos registros, que deve coincidir com o esperado do raw.

O leitor em lote faz seis consultas de conteúdo para o conjunto de revisões: pais, séries, componentes/valores, atributos, medidas e faixas. Reconstroi os dois contratos Mega-Sena das **tabelas**, não de um JSON de diagnóstico/cache. Hash divergente falha fechado. O limite de 6.000 revisões cobre até 2.954 suportadas + 2.954 heads neste recorte; não é uma consulta pública arbitrária ou um leitor universal de todas as modalidades.

O relatório não usa UUIDs/relógios como hash de cobertura. Campos de contexto, como contratos dos heads e contagem de continuidade, descrevem o snapshot. Uma correção JSON posterior pode mudar o head legitimamente sem apagar a validade da observação histórica original: a cobertura é aferida pela revisão apoiada naquele processamento, não pela exigência de que o head atual nunca mude.

Número de revisões igual a 2.954, isoladamente, não prova completude. Apoio JSON pode não criar revisão; correções podem criar várias. Da mesma forma, cobertura qualificada não promove baseline nem autoriza publicar dados.

### Correções incorporadas após a revisão

**Evidência histórica e autorização atual são distintas.** `describe` localiza o run/receipt histórico sem exigir a aprovação atual da fonte. Confere schema, run, fonte, tamanho/hash do artefato e request hash derivado do manifesto e fingerprint registrados. A auditoria usa esse fingerprint original na receita. Uma aprovação, mudança de política ou bloqueio posterior não invalida automaticamente a evidência antiga nem autoriza novas escritas. Isso não é autenticação/autorização de usuários: as permissões SQL continuam necessárias.

**Estado de encerramento e qualidade do snapshot são distintos.** `finish` bloqueia o run e, somente se running, define completed/stopped com retorno do estado efetivamente atualizado. Estados terminais e seus tempos ficam preservados; nenhuma receita é reencerrada no replay terminal. `run_status` relata o encerramento persistido e `qualified` relata a auditoria atual. Assim, completed com qualified=false em uma reavaliação é um sinal de investigação, não uma reescrita retroativa do sucesso nem autorização para publicar.

Um run stopped não é reaberto automaticamente. Exceção entre commits deixa running e permite a retomada comprovada. Falha/quarentena encontrada na finalização deixa stopped. Mesmo que uma execução posterior preencha pendências ou outra intervenção torne a cobertura completa, o estado terminal original não é promovido silenciosamente: aprovação/reabertura exige fluxo próprio, não inferência de qualified=true.

## Sobreposição JSON e execução controlada

O cenário integral começa com o JSON real 2954 já presente. A carga deve criar as revisões históricas dos demais concursos e apoiar o JSON sem remover extração, fundos ou metadados. Conteúdo de entrada histórico e revisão JSON são verificados cada um no seu contrato, pela ponte conservadora, sem substituir seus hashes.

O teste interrompe realmente após 100 commits, verifica auditoria incompleta (100 presentes, 2.854 ausentes) e restaura usando nova instância e manifesto/bytes persistidos. Após concluir, repete a retomada/auditoria sem duplicação, tenta reutilizar a chave com seleção piloto (conflito) e testa uma correção JSON posterior, explicitamente simulada e separada do relatório positivo da carga.

No mesmo banco descartável, após o relatório positivo, o teste altera a política/aprovação da fonte e depois a bloqueia: a auditoria histórica permanece qualificada, mas retomadas são recusadas (conflito de intenção ou catálogo não qualificado). Outro cenário SQL finaliza uma carga sem linhas como stopped e verifica repetição/auditoria sem promover sucesso ou alterar finished_at.

`tests/test_historical_coverage.py` exercita o avaliador puro com uma linha real e identificadores dublês, exclusivamente em memória: ledger, receita, alias, evidência, payload, selagem, hash, conteúdo relacional, head, publicação, quarentena, lacunas, duplicação, registros/comandos inesperados e manifesto divergente. O plano reduzido não é aceito pelo importador. Esses testes não substituem a evidência SQL integral.

`tests/database/test_historical_import_lifecycle.py` verifica os estados terminais completed/stopped/failed com auditoria posterior diferente, usando dublês sem conexão. Fica com as dependências opcionais de banco; a suíte comum não importa repositórios PostgreSQL. O runner também descobre esses casos, mas sua prova é unitária, não SQL real.

As mutações negativas não são novos resultados históricos. Todas as escritas ocorreram em PostgreSQL descartável, sob login ingestor restrito; o runner confirma o diretório do cluster e o encerra ao terminar. Nenhum banco/serviço instalado é usado como alvo da carga.

## Reprodução

### Verificação final em 25/10/2026

**312 testes distintos aprovados**, sem contar execuções repetidas:

| Grupo | Resultado desta verificação |
|---|---|
| Suíte comum, sem imports de infraestrutura PostgreSQL | 219 aprovados, 105,54 s |
| Runner isolado | 90 aprovados, 1.012,140 s; 85 PostgreSQL reais + cinco dublês UoW |
| Estados terminais, dublês sem conexão | três aprovados, 0,004 s; comando próprio |

Os três testes de estado foram extraídos da suíte comum enquanto o runner já executava e validados separadamente. Nas próximas execuções completas, a descoberta inclui esses três também (93 casos no runner). Isso não transforma os oito casos com dublês em testes PostgreSQL reais.

Cobertura positiva: **2.954/2.954**, sem lacunas, duplicações, quarentenas ou inconsistências; 2.953 novas revisões históricas e um apoio ao JSON existente. Manifesto esperado/observado `9c963b7f327ea52482a83d86433ad2e48c990838be1f1ebee6ffa1e175c298e5`; plano `f9e8eda3f302f647acbedd3cf0361c867ac98625bb1e6568cf7b93bf3fa0ada6`. Baseline/checkpoint/step continuam zerados no cenário da carga. [Relatório novo com contexto e preservação](../data/mega-sena-cobertura-spec-0029.json).

Log aprovado: `.local-postgres/spec0029-fechamento-20261025-reexecucao.log`, saída 0. Cluster `.local-postgres/runs/3fa44c4a11f4482dbae1d617e2fd0fe1`, PostgreSQL 17.11; server.log confirma desligamento e postmaster.pid ausente. Dados físicos/logs ficam locais e ignorados, não são uma base operacional ativa. Serviços PostgreSQL 12/13 existentes continuaram em execução e não foram alvos dos testes.

A primeira tentativa desta retomada gerou a mesma cobertura positiva, mas terminou **89/90**: a preparação do teste de evolução do catálogo chamou fetchall depois de UPDATE sem RETURNING. O erro foi corrigido no teste com RETURNING id, sem alterar os dados históricos ou relaxar a auditoria. Log preservado em `.local-postgres/spec0029-fechamento-20261025.log`, cluster `7f955c81e5a24134ab41d71eea4d8ca8`, também desligado. A aprovação usa somente a reexecução integral sem erros. A execução antiga de 21/10, sem resultado final recuperável, não foi reaproveitada como prova.

Os **69 arquivos protegidos** mantiveram seus hashes: seis raws, 29 documentos de dados anteriores, nove fontes de migrations, nove fixtures fixas e 16 arquivos da coleta local. A auditoria local anterior foi reproduzida exatamente com status healthy. Nenhum relatório anterior, vetor, contrato canônico, migration ou dependência foi alterado para obter aprovação.

```powershell
.venv\Scripts\python -m pytest tests/test_historical_import.py tests/test_historical_coverage.py -q
.venv\Scripts\python -m unittest discover -s tests/database -p test_historical_import_lifecycle.py -v
.venv\Scripts\python scripts/database/run_integration.py --pg-bin .local-postgres\17.11-3\pgsql\bin
.venv\Scripts\python -m pytest tests --ignore=tests/database -q
```

O teste integral é `tests/database/test_full_history_import.py`; imprime progresso e relatório positivo derivado do SQL. A integração não é executada pelo pytest que exclui database. Não foi adicionada CLI de importação operacional ou DSN implícito.

## Limites e próxima tarefa

A carga só qualifica este recorte/checksum da Mega-Sena. Não certifica dados atualizados até hoje, semântica econômica de zeros antigos, novas fontes ou funcionamento em produção. Auditoria usa as permissões e metadados deste ambiente controlado; não é uma API pública/autorização de usuários. O SQL compartilhado ainda é específico dos dois contratos Mega-Sena.

**SPEC-0030 — Registro de baseline auditada e inicialização segura da sincronização Mega-Sena.**

Justificativa: transformar a evidência de cobertura em um ponto de partida explícito para a sincronização, com regras próprias e sem alterar baseline já referenciada/imutável. Exigir encerramento completed e auditoria atual qualificada, não somente um desses sinais. Definir vínculo entre fontes histórica/JSON e comprovar a continuidade antes de qualquer ativação operacional. Não executada nesta SPEC.
