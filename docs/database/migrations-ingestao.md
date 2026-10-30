# Migrations do recorte de ingestão — SPEC-0024

## O que existe agora

Três migrations Alembic explícitas, em ordem, no schema `lb`:

| Revisão | Responsabilidade |
|---|---|
| `0024_01` | sete relações de catálogo: loteria, escopo, versão, série, componente, faixa e fonte |
| `0024_02` | dezessete relações de aquisição/interpretação/concurso/conteúdo |
| `0024_03` | baseline, checkpoint e passo contíguo |

São 27 tabelas de domínio/ingestão, além do controle `alembic_version`. Não há tabelas por modalidade, colunas bola1…bola15, ORM paralelo ou seed automático. As seis loterias e suas 20 versões de matriz vêm do catálogo Python existente e são inseridas **somente no banco descartável de testes**. A aplicação operacional ainda usa arquivos.

Os arquivos SQL fazem parte das migrations: não editar uma revisão depois de distribuída/aplicada em ambiente persistente; mudanças posteriores exigem nova migration. O Alembic controla a ordem; SQL PostgreSQL explícito torna visíveis FKs compostas, EXCLUDE, domínios e triggers, sem um modelo ORM ainda sem consumidor.

## Ambiente reproduzível

Qualificado com Python 3.12 e PostgreSQL **17.11**, binários Windows EDB `postgresql-17.11-3-windows-x64-binaries.zip`. SQLAlchemy 2.0.55, Alembic 1.20.0 e Psycopg 3.3.6 estão fixados em `requirements-database.txt`; dependências de testes em `requirements-test.txt`. A versão major 17 é exigida pelo ambiente de migration e o teste registra/confere 17.11. Atualização de patch exige nova qualificação, não significa fixar indefinidamente uma versão de segurança.

Origem dos binários: [distribuição Windows PostgreSQL](https://www.postgresql.org/download/windows/) → [EDB](https://www.enterprisedb.com/download-postgresql-binaries). SHA-256 **observado localmente**, não checksum independentemente autenticado do fornecedor: `4b8db0930c38f6ef845db919551dedda3b6b845aeb0927b3d79a6e8e9e4537cf`. O executável consultado não possui assinatura Authenticode. O download veio por HTTPS da EDB; isso não equivale a uma cadeia de distribuição auditada para produção. Nenhum instalador/serviço foi executado.

Na raiz, em PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-database.txt -r requirements-test.txt
.venv\Scripts\python scripts/database/run_integration.py --pg-bin 'CAMINHO\PostgreSQL-17.11\bin'
.venv\Scripts\python -m pytest tests --ignore=tests/database -q
```

O runner aceita binários já obtidos pelo operador; não baixa/executa programas arbitrários. Cria diretório UUID em `.local-postgres/runs`, porta livre em `127.0.0.1`, senha aleatória e autenticação SCRAM. Confere `data_directory` antes dos testes e sempre tenta desligar esse cluster no `finally`, inclusive em falha de inicialização parcial. Dados/logs ficam ignorados pelo Git para diagnóstico; não reutilizar esse cluster como banco operacional. O arquivo temporário da senha é removido. Não imprime senha nem DSNs.

O PostgreSQL local precisa poder abrir socket loopback e criar processos auxiliares. Em ambiente restrito Windows, a execução precisou de autorização para essa operação; não alterar serviços existentes para contornar a restrição. O runner deixa claro o diretório/log do cluster. As tentativas iniciais bloqueadas e o problema de herança de pipes foram resolvidos no executor, sem alterações aos históricos.

Não apontar a suíte para banco de usuário. A integração falha se não receber a identidade do cluster isolado; ausência de PostgreSQL não é tratada como teste aprovado por skip. `pytest` do legado exclui expressamente essa pasta, e a suíte PostgreSQL é comando separado obrigatório.

## Aplicar em um banco de desenvolvimento provisionado

O proprietário das migrations deve ser um login dedicado, sem superuser, com propriedade/CREATE apenas no banco destinado ao LottoBrain. `btree_gist` é extensão trusted no ambiente testado; provedores gerenciados podem exigir provisionamento explícito. O teste aplica DDL como `lb_migrator`, NOSUPERUSER/NOCREATEDB/NOCREATEROLE. O bootstrap do cluster usa administrador apenas para criar banco e papéis, nunca como identidade da aplicação.

Definir `LOTTOBRAIN_DATABASE_URL` pelo mecanismo local de segredos, no formato `postgresql+psycopg://…`, sem versionar/colar senha em comandos compartilhados. Depois:

```powershell
.venv\Scripts\python -m alembic upgrade head
.venv\Scripts\python -m alembic current
```

Reaplicar `head` não recria tabelas. Cada comando aplica seu lote de DDL e ledger em uma transação, com lock consultivo mantido até o último passo para serializar migradores. Conexões programáticas precisam ser dedicadas e sem transação ativa. Não chamar autogenerate sem revisar o SQL explícito; ainda não existe metadata ORM como autoridade concorrente. Migrations não chamam rede, coletores ou normalizadores.

O provisionador aplica explicitamente `scripts/database/roles.sql` no banco correto e associa logins aos papéis, sem compartilhar credenciais de migração. Papéis globais criados são NOLOGIN, sem privilégios administrativos:

- `lottobrain_ingest`: leitura, inserções necessárias e atualizações por coluna de estados/ponteiros/lease. Sem DDL, DELETE, TRUNCATE, edição de catálogo/baseline ou ponteiro publicado.
- `lottobrain_audit`: somente leitura do recorte, para uso interno; **não é um papel público**, pois permite acessar evidências/diagnósticos.

O script é aditivo e destinado a ambiente novo: ele não certifica nem corrige papéis globais preexistentes que já tenham privilégios extras. Antes de produção, auditar memberships, grants, TLS, segredos, backups e papéis de publicação/API. Papéis de grupo nunca devem ser membros do proprietário das tabelas.

Duas funções de integridade (`guard_revision` e `validate_revision`) são SECURITY DEFINER, com `search_path` fixo e referências qualificadas: precisam travar a regra sem conceder UPDATE no catálogo ao ingestor. São funções de leitura/validação, sem SQL arbitrário. EXECUTE público foi revogado; apenas a validação necessária é concedida ao ingestor. Triggers não usam usuário superuser; o dono é o migrador restrito. Proteções não se destinam a resistir ao proprietário/administrador que deliberadamente desabilite triggers.

## Garantias implementadas

- Regras validadas não se sobrepõem, por EXCLUDE/daterange `[início,fim)`; exatamente uma série principal e componentes definidos são checados no commit.
- Contextos loteria/regra/série/componente/faixa/escopo/concurso usam FKs compostas.
- A revisão confirma somente selada, com observação aceita e concluída, hash/versão coerentes, regra aplicável, séries obrigatórias e números válidos. Uma linha pode concluir enquanto o lote continua `running`.
- Quantidade, tipo, limites, unicidade, ordinais contíguos, ordenação canônica e extração opcional completa são validados por trigger diferível. Extração não é deduzida da lista crescente; trevos continuam sem ordinal de extração inventado.
- Após o selo, bloquear UPDATE/DELETE da revisão e INSERT/UPDATE/DELETE de conteúdo, inclusive filhos tardios. Observações adicionais são append-only. Catálogo referenciado é congelado, exceto fechamento de vigência que preserve revisões existentes.
- Dinheiro usa numeric sem escala coercitiva: finito, não negativo, até 10¹⁸ e seis casas. Moeda/valor existem só no estado conhecido; zero é válido. Chave com `NULLS NOT DISTINCT` impede duplicata com faixa/moeda ausentes. Escopo e cash/annuity permanecem separados.
- Raw deduplica bytes pelo hash, não capturas. Receipt HTTP exige tentativa com status correspondente; falha de transporte não obriga raw fictício. IDs/receitas/contextos e evidências não são reescritos silenciosamente.
- Checkpoint inicia na baseline; avance de uma unidade exige passo aceito da fonte/loteria/identidade oficial, lease vigente e token atual. Passo/cursor incoerentes não confirmam. Candidato adiante não estabelece continuidade. Baseline referenciada não significa histórico carregado.
- Publicação está **bloqueada** por CHECK e privilégio de coluna até implementar T5/decisões/outbox.

CHECKs não consultam outras tabelas. FKs/UNIQUE/EXCLUDE cobrem relações; triggers específicos cobrem agregados e transições. Locks nas regras/revisões/checkpoints evitam validar catálogo mutável como se fosse constante; concorrência dos casos de uso ainda exige testes próprios com duas conexões.

## Limites explícitos

- Formato do hash e coerência entre metadados são SQL; reproduzir bytes/canonicalização ainda é responsabilidade da aplicação/auditor. Os testes usam hashes do formato semântico legado identificados como tal, não fingem um formato relacional novo.
- Campos financeiros opcionais podem estar ausentes. Quantidade de faixas exigida por cada fonte e semântica de cada medida seguem no normalizador; não há DSL financeira em SQL.
- Snapshot de fonte tem versão, tamanho e chaves permitidas. Redação de URLs/valores e significado dos campos continuam responsabilidade do adaptador; a allowlist não é detector universal de segredos.
- Atualização de status de execução não prova sucesso do processo externo; armazenamento não participa da transação SQL. Faltantes/órfãos exigem auditoria.
- O baseline deste incremento é imutável. Promoção após carga terá evidência/manifesto de materialização próprio no incremento de importação, sem apagar o registro referenciado.
- Claim de lease, CAS, retry, tradução de erros, replay e reconstrução A→B→A ainda não têm repositórios implementados. DDL não fornece sozinho essas operações.
- Não há carga operacional, scheduler, API, frontend, usuários reais, decisões de publicação, audit_event, outbox ou tabelas de ML.
- Vetores relacionais das seis modalidades permanecem obrigatórios **antes de importar**; fixtures SQL não os substituem.

## Recuperação

Downgrade é somente para estruturas vazias. `0024_03` recusa continuidade preenchida; `0024_02` recusa qualquer evidência; `0024_01` recusa catálogo preenchido. Banco vazio passa head → base → head. A extensão `btree_gist` não é removida, pois pode ser compartilhada. O lote transacional preserva também as revisões anteriores/ledger quando outra migration bloqueia a reversão; conferir `alembic current`, nunca insistir em apagar conteúdo.

Em banco preenchido: interromper escritores, preservar backup e evidência, diagnosticar, criar migration forward ou restaurar backup em outra instância e auditar antes da troca. Não editar `alembic_version`, desabilitar triggers ou truncar tabelas para forçar sucesso. Restauração de backup de produção ainda não foi qualificada nesta etapa.

## Referências consultadas

- [Alembic — tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html).
- [Psycopg — instalação](https://www.psycopg.org/psycopg3/docs/basic/install.html).
- [PostgreSQL 17 — constraints](https://www.postgresql.org/docs/17/ddl-constraints.html), [triggers](https://www.postgresql.org/docs/17/sql-createtrigger.html), [numeric](https://www.postgresql.org/docs/17/datatype-numeric.html) e [btree_gist](https://www.postgresql.org/docs/17/btree-gist.html).

Cobertura executada e pendências: [relatório de verificação](verificacao-spec-0024.md).

## Evolução na SPEC-0030

O head passa a `0030_01`, acrescentando aprovação append-only e vínculo explícito de baseline XLSX para checkpoint JSON. As migrations 0024 permanecem intactas. [Contrato, FKs e privilégios](baseline-auditada.md) e [operação/verificação](../engineering/baseline-sincronizacao-mega-sena.md).

Reaplicar `scripts/database/roles.sql` explicitamente após o upgrade para provisionar as permissões da nova tabela. O papel bootstrap não é um login nem é atribuído ao ingestor. Downgrade com ativação preenchida é recusado; não apagar vínculos ou alterar o ledger para contornar o bloqueio. Não há migration operacional automática, worker ou agendamento nesta evolução.

## Evolução na SPEC-0031

O head passa a `0031_01`, com `sync_batch` e `sync_batch_operation`, índices/guardas de orçamento e testemunho diferível de lease no COMMIT. [Relações, atomicidade e privilégios](lotes-sincronizacao.md) e [operação/recuperação](../engineering/sincronizacao-sql-mega-sena.md).

Reaplicar os privilégios explicitamente após o upgrade. Ingestor ganha apenas as escritas necessárias nos novos registros; bootstrap não passa a executar lotes. Downgrade com lote presente é recusado. Não há scheduler ou migration automática em banco operacional.

## Evolução da etapa 6 na SPEC-0033

A revisão 0033_01 acrescenta política, conjuntos aprovados, membros, decisões e ponteiro ativo, além das views privadas de leitura. As revisões 0024–0031 permanecem intactas. [Contrato das seis](persistencia-seis-loterias.md), [operação](../engineering/etapa-6-operacao.md) e [estado/evidência](../engineering/etapa-6-persistencia.md).

Reaplicar scripts/database/roles.sql explicitamente após upgrade. Ingestão não recebe aprovação; leitor não recebe tabelas de candidatos/raw. Downgrade com políticas ou datasets preenchidos é recusado. A migration não carrega históricos, cria logins, consulta fontes nem configura Supabase automaticamente.
