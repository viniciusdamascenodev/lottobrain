# Etapa 5 — Desenvolvimento reproduzível e integração contínua

## Escopo e estado

Tarefa única autorizada em 28/10/2026, dentro da SPEC-0033. Reaproveita domínio, ingestão, fixtures, migrations, executor PostgreSQL e desenho da etapa 4. Entrega ambiente local, dependências resolvidas, fundações HTTP/frontend, verificações e workflow no mesmo repositório `viniciusdamascenodev/lottobrain`.

**Estado: preparação local validada; validação remota em execução.** Resultados locais e execução remota estão registrados separadamente em [evidências](etapa-5-evidencias.json). A conta proprietária foi autenticada no GitHub CLI do computador, com acesso administrativo e escopo de workflows. Essa autenticação é independente da conta do plugin. Criar YAML não comprova execução no GitHub; o aceite depende do run e da proteção de branch. Nenhum token ou senha deve entrar no chat.

Validação local: 401 testes comuns aprovados sem avisos, 137 testes PostgreSQL aprovados em cluster descartável desligado, instalação limpa/frontend com três testes e build, quatro verificações HTTP e auditorias sem vulnerabilidades conhecidas no recorte ativo. Os 149 arquivos anteriores protegidos de dados, fixtures, protótipo e migrations permaneceram idênticos. A fundação recusa dados, inclusive pelo proxy do frontend. A suíte SQL completa levou cerca de 35 minutos neste Windows; o tempo no runner Linux ainda será medido, com limite de 60 minutos no job para não mascarar timeout como aprovação.

Esta entrega não implementa autenticação/aprovação, consulta operacional das seis, carga histórica adicional, atualização, modelos ou publicação. A fundação recusa acesso aos dados enquanto esses recursos não existem. Concluir esta etapa não encerra a SPEC-0033.

## Critérios de aceite

| ID | Prova |
|---|---|
| E5-01 | Runtimes declarados e instalação Python/frontend pelos lockfiles em ambiente novo |
| E5-02 | Perfil API leve separado de jobs, testes e ferramentas; legado preservado |
| E5-03 | Qualidade, tipos, testes comuns offline e build do frontend aprovados |
| E5-04 | Migrations e suíte PostgreSQL real executadas pelo cluster descartável existente, sem skip e com desligamento |
| E5-05 | Verificação básica de credenciais e auditoria de dependências sem alertas conhecidos no recorte executado |
| E5-06 | Falha intencional detectada e correção aceita; smoke local da fundação sem exposição de dados |
| E5-07 | Workflow versionado no repositório correto, execução real identificada e todos os jobs obrigatórios aprovados |
| E5-08 | Comandos, ambientes, segredos, limites, preservação e aprendizados documentados |

## Runtimes e dependências

- Python **3.12.x**, declarado em `.python-version` e `pyproject.toml`. O patch efetivo é registrado na execução; o CI instala a linha 3.12 atualizada. O ambiente local anterior foi preservado.
  O `runtime.txt` legado também foi alinhado à linha 3.12 para não manter dois alvos contraditórios.
- Node **24.19.0**, declarado em `.node-version`; npm **12.2.1**. Não usar o Node 14 que estava no PATH deste computador para o frontend novo. Nenhuma instalação global foi alterada durante a implementação.
- `pyproject.toml` é a entrada ativa das dependências da plataforma; `uv.lock` fixa o grafo e hashes, incluindo variações de plataforma. uv **0.13.6** é exigido.
- `frontend/package.json` fixa dependências diretas; `package-lock.json` fixa o grafo e integridade. Instalar com `npm ci --ignore-scripts`.

| Grupo Python | Uso |
|---|---|
| `api` | FastAPI/Uvicorn, sem Selenium, pandas, treinamento ou ferramentas de desenvolvimento |
| `database` | SQLAlchemy, psycopg e Alembic |
| `jobs` | Banco e dependências de leitura/processamento histórico |
| `test` | API/jobs e ferramentas de teste; reutiliza os casos existentes |
| `quality` | Ruff, mypy e pip-audit |

O ambiente de desenvolvimento padrão reúne `test` e `quality`. Instalação mínima: `uv sync --frozen --no-default-groups --group api`. Jobs: `uv sync --frozen --no-default-groups --group jobs`. O CI usa ambientes próprios por job.

`requirements.txt`, `requirements-test.txt`, `requirements-database.txt`, Flask e o `vercel.json` antigo são compatibilidade legada; não são o manifesto do frontend/API novos. A correção Requests 2.33.0 também foi aplicada ao requirements legado. Não iniciar o produto novo pelo Flask nem promover essa configuração antiga como deploy da SPEC-0033. Substituir o alvo de publicação na entrega de acesso real, preservando este histórico e usando o perfil mínimo da API.

`.editorconfig` define convenções para edição nova. `.gitattributes` impede normalização de finais de linha em raws, fixtures e evidências hashadas; o Git precisa conservar os bytes entre Windows e Linux. Nenhum raw foi reescrito ou renormalizado por esta tarefa.

## Preparação local

Pré-requisitos: Git, Python 3.12, Node da `.node-version` e npm 12.2.1. Use o gerenciador de versões de sua preferência ou a distribuição oficial; confirme `node --version` e `npm --version` antes de instalar. Para não alterar a `.venv` anterior, os exemplos criam `.venv-dev`.

Windows/PowerShell, a partir da raiz:

```powershell
py -3.12 -m venv .tools
.tools/Scripts/python -m pip install uv==0.13.6
$env:UV_PROJECT_ENVIRONMENT = '.venv-dev'
.tools/Scripts/uv sync --frozen
.venv-dev/Scripts/python scripts/engineering/check.py all
```

Linux/macOS:

```bash
python3.12 -m venv .tools
.tools/bin/python -m pip install uv==0.13.6
export UV_PROJECT_ENVIRONMENT=.venv-dev
.tools/bin/uv sync --frozen
.venv-dev/bin/python scripts/engineering/check.py all
```

Frontend, em outro terminal com o Node/npm corretos:

```text
cd frontend
npm ci --ignore-scripts
npm run check
```

O comando `check` do frontend executa lint, geração de tipos de rota, TypeScript, testes de configuração e build. `next typegen` vem antes de `tsc`: arquivos gerados do Next não podem ser uma dependência oculta da máquina do desenvolvedor.

`next-env.d.ts`, `.next` e caches são gerados e ignorados pelo Git. A checagem precisa funcionar quando esses tipos ainda não vieram de uma execução local anterior.

Para modificar dependências, alterar o manifesto e regenerar o lock com a ferramenta fixada; revisar o diff e rodar as verificações afetadas. `uv sync --frozen`/`npm ci` não devem resolver silenciosamente um grafo diferente. O CI também usa `uv sync --locked` para recusar manifesto fora de sincronia.

## Executar a fundação

Copiar `.env.example` para `.env` e `frontend/.env.example` para `frontend/.env.local`, somente localmente. Os exemplos não têm credenciais e a fundação não precisa de banco operacional.

API, com o ambiente de desenvolvimento selecionado:

```text
uv run --frozen --env-file .env uvicorn app.interfaces.http.main:app --host 127.0.0.1 --port 8000
```

Se uv foi instalado em `.tools`, usar o executável correspondente no lugar de `uv`. Frontend: `npm run dev`, na pasta `frontend`. As portas 8000/3000 são locais; encerrá-las ao terminar. Smoke automatizado usa portas livres e desliga somente seus próprios processos.

`/healthz` confirma que o processo responde; `/readyz` retorna **503**, pois o produto ainda não está pronto. `/api/v1/*` recusa todas as operações com `PLATFORM_NOT_READY`. OpenAPI/Swagger públicos estão desativados. Respostas da API são `no-store`; a página inicial não contém resultados nem credenciais. Não representar esse shell como autenticação implementada.

O frontend encaminha `/api/v1/*` para `LOTTOBRAIN_API_ORIGIN`, configurada no servidor/build, sem credenciais no navegador. Aceita HTTP somente em loopback local e exige HTTPS explícito nos ambientes remotos. Usuário, senha, caminho, query e fragmento na origem são recusados.

## Testes e qualidade

`python scripts/engineering/check.py quality` verifica erros fatais no Python existente, lint/formatação mais abrangentes nos arquivos novos, tipos na fundação nova e arquivos de ambiente/chaves/tokens conhecidos. O escopo gradual evita reformatar o núcleo inteiro para preparar o CI. Não é declaração de tipagem ou auditoria completa do legado.

`python scripts/engineering/check.py test` executa pytest e gera `test-results/python.xml`. A suíte comum bloqueia DNS/conexões externas; loopback é permitido no mecanismo interno de `asyncio.socketpair` do Windows. Chamadas inesperadas a fontes devem falhar, usando fixtures e transportes simulados. Testes SQL não são descobertos pelo pytest padrão, e tampouco são aprovados por skip: usam o executor abaixo.

```text
python scripts/database/run_integration.py --pg-bin CAMINHO_POSTGRESQL_17_BIN
```

O executor cria cluster/credenciais/porta novos, confere identidade do diretório, aplica migrations e testa privilégios, transações, concorrência, idempotência e recuperação. Os artefatos ficam em `.local-postgres/runs`, ignorado pelo Git. O bloco `finally` desliga o cluster. Nunca apontar esses testes a Supabase ou banco existente. No Windows local, a execução precisou da permissão para iniciar processos/conexões do cluster isolado; a tentativa restrita falhou e não contou como teste aprovado.

A auditoria Python exporta os perfis API/jobs resolvidos do lock e consulta pip-audit; o frontend usa `npm audit --audit-level=high`. Uma falha de consulta não equivale a ausência de vulnerabilidades. O scanner local de credenciais reconhece um conjunto limitado de padrões; não substitui revisão, gerenciamento de segredos ou mecanismos do provedor.

## GitHub Actions

O [workflow](../../.github/workflows/ci.yml) executa em push na `main`, pull requests e acionamento manual. Branches de trabalho usam o evento do PR, evitando duplicar a mesma bateria em push e PR. Jobs:

1. **Python:** ambiente resolvido, Ruff, mypy, scanner básico, pytest e auditoria API/jobs.
2. **PostgreSQL:** instala binários 17 no runner Ubuntu descartável e reutiliza o executor de integração completo.
3. **Frontend:** Node/npm fixados, instalação por lock, lint, tipos, testes, build e auditoria.
4. **Quality gate:** só aprova se os três grupos terminarem com sucesso, sem mascarar falha/skip.

Actions oficiais estão fixadas por SHA completo. O token tem apenas leitura de conteúdo, checkout não persiste credencial, não há `pull_request_target`, segredo de produção ou deploy. Resultados de testes têm retenção de sete dias; clusters, dumps, `.env` e logs com credenciais não são enviados como artefatos. Dependabot propõe atualizações semanais de uv, npm e Actions; atualizar grafo exige CI aprovado.

O status `Quality gate` deve ser exigido na política de integração da branch principal, com as proteções disponíveis na conta. Não alterar visibilidade para obter recursos. Configurar/exercitar proteção no GitHub é diferente de escrever YAML; registrar explicitamente a situação real.

## Ambientes e segredos

| Ambiente | Preparação nesta tarefa | Fora deste aceite |
|---|---|---|
| local | Runtime, ambiente isolado, templates, API/frontend e verificações | Dados operacionais e autenticação real |
| CI | Instalação limpa e testes sem credenciais operacionais | Usar ou migrar banco de produção |
| preview/staging | Contrato de variáveis e validação HTTPS/TLS; sem valores secretos versionados | Provisionar serviços, configurar OAuth e provar deploy na SPEC-0033 |
| produção | Mesmos nomes/validação, valores isolados por provedor | Release, operação, backups e autenticação ainda não entregues |

| Variável | Natureza e uso |
|---|---|
| `LOTTOBRAIN_ENV` | `local`, `test`, `preview`, `staging` ou `production`; erro de digitação é recusado |
| `LOTTOBRAIN_WEB_ORIGIN` | Origem do frontend; HTTPS fora de local/test, sem credenciais/caminho |
| `LOTTOBRAIN_API_ORIGIN` | Destino do proxy do frontend, exclusivo do servidor/build |
| `LOTTOBRAIN_DATABASE_URL` | Segredo backend/CLI quando utilizado; PostgreSQL/psycopg e TLS fora de local/test; omitido de repr/log |

Chaves Auth/Storage/OAuth e sessões serão acrescentadas quando os respectivos adapters existirem, conforme a arquitetura de segurança. Não criar variáveis fictícias como se integrações estivessem prontas. Valores privados ficam nos gerenciadores dos serviços/ambientes autorizados; nunca em `NEXT_PUBLIC_*`, chat, commit, print de ambiente ou artefato público. Nenhuma credencial operacional é necessária para o CI desta etapa.

## Preservação e passagem

Dados brutos, amostras, relatórios de qualificação, protótipo visual, migrations e invariantes anteriores devem continuar intactos. O único ajuste de lógica legada nesta tarefa captura a mensagem da exceção antes de utilizá-la no callback de persistência, corrigindo o erro apontado pelo lint sem mudar o fluxo.

Não reiniciar inventário, reescrever domínio ou criar um coletor/modelo por ferramenta. Próximo incremento funcional da SPEC-0033: autenticação/aprovação/MFA e consulta persistente real das seis modalidades, usando esta base. A etapa 5 só recebe estado concluído após as evidências locais **e** remotas de E5-01–E5-08, com pendências externas declaradas.

Referências consultadas: [Next CLI e typegen](https://nextjs.org/docs/app/api-reference/cli/next), [segurança de Actions](https://docs.github.com/en/actions/reference/security/secure-use), [PostgreSQL no Ubuntu](https://www.postgresql.org/download/linux/ubuntu/). Os SHAs das Actions foram conferidos no repositório oficial via Git com certificados do Windows; não houve desativação de TLS.
