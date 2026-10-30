# Operação controlada da persistência — etapa 6

## Pré-requisitos

Usar os runtimes e lockfiles da [etapa 5](etapa-5-desenvolvimento-ci.md), com o perfil
Python jobs. São necessários PostgreSQL 17.x e um banco exclusivo do LottoBrain.
O executor de integração só aceita seus clusters descartáveis; não é instalador de Supabase.

O usuário ainda não disponibilizou projeto Supabase. Os passos abaixo são o procedimento
preparado, não uma implantação declarada concluída. A [documentação oficial](https://supabase.com/docs/guides/getting-started/quickstarts/reactjs)
orienta a criação de projeto pelo painel. Manter organização/plano Free para respeitar
o orçamento escolhido.

## Configuração privada

Guardar LOTTOBRAIN_DATABASE_URL em arquivos locais ignorados pelo Git ou no gerenciador
de segredos do ambiente. Usar conexão PostgreSQL com sslmode=require ou verificação mais
forte fora de loopback. Não usar publishable/anon key como credencial SQL.

Separar credenciais em .env.database-admin, .env.database-catalog, .env.database-ingest,
.env.database-approver e .env.database-reader. Esses nomes são exemplos de arquivos
privados, não arquivos para versionar. A URL aceita os esquemas postgresql ou
postgresql+psycopg; o Alembic usa postgresql+psycopg. Nenhum comando recebe senha por flag.

No painel Connect do Supabase, escolher conexão direta ou de sessão para migrations.
Antes de aplicar, confirmar versão, extensão btree_gist, permissões e que o banco/schema
destinado à aplicação é o ambiente correto. O schema lb não será exposto por API pública.

## Instalação

Na raiz, com o uv fixado:

    uv run --frozen --no-default-groups --group jobs --env-file .env.database-admin python -m app.interfaces.persistence inspect
    uv run --frozen --no-default-groups --group jobs --env-file .env.database-admin python -m alembic upgrade head

O comando inspect emite somente versão, TLS, sinalizadores de schema e revisão Alembic
quando o papel puder lê-la; não emite DSN, senha ou host. A versão esperada após a
instalação desta etapa é 0033_01.

O provisionador aplica scripts/database/roles.sql no banco correto usando a conexão
administrativa. Em seguida cria/associa logins limitados aos grupos do
[contrato de persistência](../database/persistencia-seis-loterias.md#permissões).
Os segredos dos logins são guardados apenas nos ambientes privados correspondentes.
O script é aditivo; papéis globais preexistentes exigem conferência dos privilégios.

    uv run --frozen --no-default-groups --group jobs --env-file .env.database-catalog python -m app.interfaces.persistence bootstrap
    uv run --frozen --no-default-groups --group jobs --env-file .env.database-admin python -m app.interfaces.persistence inspect

Bootstrap repetido deve devolver seis loterias e 20 regras, sem duplicação.
Uma divergência gera catalog_drift e rollback; não corrigir o catálogo referenciado
por edição silenciosa ou desativação de triggers.

## Uma amostra por modalidade

O comando sample seleciona exatamente um ordinal real do arquivo informado. Não há
opção all, GET ou coleta nesta CLI. O root de objetos deve ser um diretório dedicado.
Neste recorte controlado, usar .local-postgres/objects e conservar esse arquivo de objetos.

| Loteria | Arquivo preservado | Perfil para política |
|---|---|---|
| mega_sena | data/raw/mega_sena/mega_sena_resultados.xlsx | caixa_mega_sena_xlsx |
| lotofacil | data/raw/lotofacil/lotofacil_resultados.xlsx | caixa_lotofacil_xlsx |
| mais_milionaria | data/raw/mais_milionaria/mais_milionaria_resultados.xlsx | caixa_mais_milionaria_xlsx |
| powerball | data/raw/powerball/powerball_resultados.html | usamega_powerball_html |
| mega_millions | data/raw/mega_millions/mega_millions_resultados.html | usamega_mega_millions_html |
| euro_millions | data/raw/euro_millions/euro_millions_resultados.json | pedromealha_euromillions_api_json |

Exemplo PowerShell para Mega-Sena, repetindo depois com os perfis da tabela:

    $sample = uv run --frozen --no-default-groups --group jobs --env-file .env.database-ingest python -m app.interfaces.persistence sample --lottery mega_sena --file data/raw/mega_sena/mega_sena_resultados.xlsx --ordinal 1 --object-root .local-postgres/objects --command-key e6-mega-sample-1 | ConvertFrom-Json
    $policy = uv run --frozen --no-default-groups --group jobs --env-file .env.database-approver python -m app.interfaces.persistence policy --lottery mega_sena --version samples_v1 --source caixa_mega_sena_xlsx --actor operador | ConvertFrom-Json
    $dataset = uv run --frozen --no-default-groups --group jobs --env-file .env.database-approver python -m app.interfaces.persistence approve --policy $policy.policy_id --revision $sample.revision_id --actor operador --command-key e6-mega-approve-1 | ConvertFrom-Json
    uv run --frozen --no-default-groups --group jobs --env-file .env.database-approver python -m app.interfaces.persistence activate --dataset $dataset.dataset_id --expected-version 0 --actor operador --command-key e6-mega-activate-1
    uv run --frozen --no-default-groups --group jobs --env-file .env.database-reader python -m app.interfaces.persistence read --lottery mega_sena --dataset $dataset.dataset_id --limit 20

Conservar os UUIDs reais emitidos e conferir outcome antes da aprovação.
Zero é a versão esperada apenas na primeira ativação. Uma troca posterior exige a
versão atual observada. O leitor devolve dataset_id e next_offset; repetir dataset_id
nas páginas seguintes.

O parâmetro allow-correction é decisão administrativa explícita para criar revisão
candidata do mesmo contrato. Não ativa dados nem resolve automaticamente conflitos
entre contratos. A quarentena devolve exit code 2 e conserva a revisão anterior.

## Verificação e evidência

1. Conferir versão 17.x, TLS remoto e head 0033_01.
2. Executar bootstrap duas vezes e conferir seis loterias/20 regras.
3. Persistir uma amostra real de cada perfil e repetir a mesma chave.
4. Aprovar e ativar seis conjuntos com as credenciais de aprovação.
5. Ler os seis como leitor e verificar recusa de acesso direto aos candidatos/raw.
6. Abrir conexão nova e confirmar os mesmos UUIDs, conteúdo e manifestos persistidos.
7. Registrar resultados e hashes em evidência sanitizada, mantendo credenciais e corpos
   privados fora do GitHub. A prova em Supabase continua pendente até ser executada.

## Testes do desenvolvimento

    python scripts/engineering/check.py all
    python scripts/database/run_integration.py --pg-bin CAMINHO_POSTGRESQL_17_BIN --test-pattern test_six_lottery_persistence.py

A suíte completa de PostgreSQL no CI reutiliza todos os casos anteriores. Os novos
testes cobrem 45 vetores reais/20 regras, papéis separados, manifesto, concorrência,
rollback, paginação estável e compatibilidade da ponte Mega-Sena.
