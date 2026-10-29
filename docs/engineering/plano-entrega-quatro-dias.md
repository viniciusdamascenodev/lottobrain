# Plano de entrega do LottoBrain em quatro dias

## Prazo e resultado esperado

Planejamento reorganizado em 26/10/2026, America/Sao_Paulo, após a SPEC-0032. Meta: versão inicial completa e utilizável online até 30/10/2026. Para organizar o trabalho, quatro dias significam uma janela aproximada de 96 horas a partir de 26/10; o horário final deve ser alinhado no início da execução. O prazo é uma meta com risco alto, condicionado a fontes acessíveis, contas e infraestrutura disponíveis.

O lançamento reúne as seis loterias, dados atuais auditados, atualização recorrente, acesso controlado, painel explicativo, previsões iniciais avaliadas, cadastro administrativo e operação reproduzível. A amplitude do laboratório de modelos e os refinamentos posteriores ficam no backlog; os requisitos essenciais abaixo não desaparecem por causa do prazo.

Esta revisão conclui o planejamento. A SPEC-0033 está em execução na fundação da etapa 5; sua capacidade funcional e as SPECs 0034–0036 ainda não foram entregues. A [consolidação da etapa 3](../architecture/visao-geral.md) em 27/10 define arquitetura privada, atualização +1h/D+1 e consulta básica das seis já na 0033. Nenhuma contratação, coleta ou publicação decorre desta documentação; a ampliação da primeira entrega aumenta o risco do prazo original, que não foi reiniciado.

## Decisões de produto confirmadas em 27/10/2026

O usuário definiu três condições para a primeira versão:

- **Acesso inteiramente privado:** cadastro começa pendente; somente o proprietário/administrador aprova o acesso. Login ou e-mail confirmado não concedem aprovação automaticamente. Consultas, gráficos, previsões e arquivos exigem autorização no backend; apenas telas necessárias a entrar, cadastrar e recuperar acesso são públicas. Revogação também bloqueia sessões/tokens ainda existentes.
- **Atualização +1h/D+1, revista pelo usuário na etapa 3:** primeira tentativa devida cerca de uma hora após o sorteio, com reconciliação no dia seguinte às 09h da fonte. Modo diário é aceitável se necessário por cota/fonte; mostrar política e atraso por modalidade/série. Incorporar acréscimos por política aprovada sem clique humano a cada sorteio; não prometer cinco/quinze minutos.
- **Custo inicial R$ 0/mês:** usar cotas gratuitas, sem assinatura paga, trial que exija migração paga, domínio comprado ou cobrança automática por excedente. Esgotamento de cota exige interrupção/alerta ou decisão explícita do usuário, não contratação silenciosa. Crescimento e desempenho serão medidos antes de afirmar que as cotas comportam todo o produto.

Essas decisões fecham público/acesso, atualidade e orçamento. A escolha técnica foi consolidada na etapa 3; sua implantação será comprovada na SPEC-0033. A meta original de 30/10/2026 permanece como planejamento de risco alto, sem prova de capacidade ou reinício da janela.

## Base que será aproveitada

Fundação da etapa 5 validada em 28/10/2026 e integrada à `main` em 29/10/2026: [ambiente, dependências, testes e workflow](etapa-5-desenvolvimento-ci.md). [PR #1](https://github.com/viniciusdamascenodev/lottobrain/pull/1) integrada, [CI pós-merge aprovado](https://github.com/viniciusdamascenodev/lottobrain/actions/runs/40964245312), `main` protegida e fechamento documental concluído. Esta atualização não inicia a próxima etapa. Não equivale à entrega funcional da SPEC-0033 nem reinicia o prazo original.

Em 28/10/2026, a [etapa 4 de experiência visual](../design/etapa-4-experiencia-visual.md) foi concluída com protótipo desktop/celular para as seis loterias e administração. Reutilizar desenho, textos, componentes e cenários nas SPECs 0033/0035. Trata-se de UX local com dados de referência e operações simuladas; não altera o estado planejado das quatro entregas nem reinicia o prazo original.

| Capacidade existente | Uso nas próximas entregas |
|---|---|
| Domínio, catálogo, seis normalizadores e 20 versões de regras | autoridade de validação; não criar outro modelo de loteria no frontend ou no coletor |
| Qualificação dos 15.471 registros históricos | entrada das cargas; confirmar cada conjunto efetivamente gravado, sem repetir a descoberta já concluída |
| PostgreSQL, migrations, revisões, evidência e permissões | preservar invariantes e acrescentar apenas migrations forward necessárias |
| Importação, aprovação, sincronização e auditorias Mega-Sena | compor a operação real; não construir um terceiro pipeline |
| Ponte XLSX/JSON e perfis históricos | reconciliar sem perda; estender escritor/leitor às outras modalidades com contratos próprios |
| Fixtures, suítes e templates SQL de teste | reutilizar preparação real e manter isolamento; não substituir aprovação por JSON fictício |
| Arquitetura de referência e aprendizados | manter monólito modular, fronteiras e decisões já comprovadas |

Estado de partida: os históricos completos terminam em dezembro de 2025; Mega-Sena tem avanço local até 2955 e candidato isolado 3071, com lacunas intermediárias. As provas SQL ocorreram em bancos descartáveis. Atualização recorrente, frontend final, contas de usuários e infraestrutura operacional ainda precisam ser entregues.

A [primeira verificação técnica de 27/10](../data/verificacao-fontes-atuais-2026-10-27.md) comprovou contratos básicos por amostra. O [fechamento da etapa 2](../data/fechamento-etapa-2.md) complementou a descoberta com calendários excepcionais oficiais, matriz de campos e continuidade de 756 registros posteriores às fronteiras dos arquivos originais. Passaram 43 testes offline do recorte consolidado. O host configurado CAIXA é `servicebus3`; seu JSON acrescenta `tituloConcursoEspecial` e o parser existente sinaliza mudança de schema. Mega-Sena permanece observada em 3075 e o ZIP FDJ avançou para 27/10; nenhum cursor ou banco foi atualizado. Condições de uso dos fornecedores, adaptação de código, transporte Double Play e enriquecimento financeiro estão explicitados como condições de implementação/ativação, sem nova rodada genérica de inventário. Não afirmar licença irrestrita ou prontidão operacional das seis fontes.

O [encerramento vigente da etapa 2](../data/encerramento-etapa-2.md) define as fontes para a integração: CAIXA oficial pública nas brasileiras, OPEN-NY nos principais recentes dos EUA e SELAE oficial por data no EuroMillions, com arquivo histórico FDJ para carga/reconciliação. Acrescentou amostras SELAE desde 2004, fronteiras de regras, retorno sem sorteio e 26 faixas recentes de ganhadores Europa conferidas; o recorte consolidado passou em **98 testes offline**. EXT-01 foi removida como bloqueio genérico, e EXT-03 foi substituída pela escolha fundamentada do canal EuroMillions para uso factual privado. A restrição concreta Colorado/Double Play EXT-02 permanece na integração desse complemento. Não repetir inventário nem confundir descoberta concluída com seis coletores já funcionando. O prazo original e o estado planejado das SPECs não são reiniciados por esta qualificação.

## Entregas e dependências

| Janela | SPEC e entrega funcional | Dependências | Evidência para encerrar |
|---|---|---|---|
| Dia 1, 26–27/10 (meta original) | [0033 — Plataforma privada e consulta das seis](../specs/SPEC-0033-primeiro-fluxo-online-mega-sena.md) | composição escolhida, acessos, perfis históricos e fontes qualificadas | usuário aprovado consulta conjuntos históricos reais das seis pela API/interface online; contas, SQL/leitura e CI comprovados |
| Dia 2, 27–28/10 (meta original) | [0034 — Seis loterias atualizadas e agendamento](../specs/SPEC-0034-seis-loterias-atualizadas-e-agendamento.md) | consulta/perfis históricos 0033; adaptadores atuais | seis coberturas recentes reconciliadas; jobs +1h/D+1 ou diários declarados e diagnóstico comprovados |
| Dia 3, 28–29/10 | [0035 — Painel, previsões e catálogo](../specs/SPEC-0035-painel-analitico-previsoes-e-catalogo.md) | snapshots aprovados e identidade/acesso | abas, gráficos e explicações; experimentos temporais e previsões registradas; nova loteria em rascunho e ativação controlada |
| Dia 4, 29–30/10 | [0036 — Validação operacional e publicação](../specs/SPEC-0036-validacao-operacional-e-publicacao.md) | jornadas integradas; ambiente e serviços disponíveis | acesso, dados, jobs, backup/restauração, alertas e deploy verificados; release e pendências explicitadas |

As janelas são metas, não comprovação de execução. Preparação de infraestrutura, verificação limitada das seis fontes, esqueleto visual e CI começam no dia 1. A coleta dos demais jogos não espera o painel ficar pronto. Segurança e deploy evoluem em cada SPEC, em vez de serem inaugurados no último dia.

O antigo recorte proposto para a SPEC-0033, um comando manual isolado, passa a ser uma atividade interna da nova SPEC-0033. As SPECs concluídas 0001–0032 e suas evidências continuam preservadas como histórico; o [roadmap](../architecture/roadmap.md) e este plano definem a sequência atual.

## Critérios obrigatórios da primeira versão

| Requisito | Aceitação observável | SPEC responsável |
|---|---|---|
| Dados das seis loterias | fronteira e fonte registradas; contagem, lacunas, duplicações, regras e diferenças reconciliadas por conjunto | 0034 |
| Atualização recorrente | calendário/fuso e janela de publicação por fonte; execução real limitada e recuperação de execução perdida demonstradas | 0034 |
| Atualidade visível | último resultado confirmado e último disponível observado, instante de verificação/coleta, atraso, falhas e lacunas exibidos; nunca declarar atualizado só pelo maior candidato | 0033–0035 |
| Conta e acesso restrito | Google/Supabase com cadastro interno pendente, aprovação pelo proprietário, login/logout, recuperação no provedor, revogação e autorização backend; usuário não aprovado não lê conteúdo privado | 0033, conferência 0036 |
| Administração | aprovar/revogar usuários; acompanhar jobs; cadastrar regras/fontes/modalidade em rascunho; trilha de alterações sensíveis e MFA administrativo | 0033–0035 |
| Interface por loteria | seis abas/páginas, filtros de período, layout responsivo, gráficos legíveis e descrição acessível pelo ícone de informação | 0035 |
| Estatísticas | frequência, evolução em janelas, distribuição de pares/ímpares e somas, intervalos entre ocorrências; especiais tratados separadamente e métricas explicadas | 0035 |
| Previsões | referências aleatória/frequência/janela móvel e ao menos um método supervisionado simples por contrato qualificado; avaliação temporal, métricas, dataset/modelo e previsões versionados | 0035 |
| Novas loterias | formulário/fluxo administrativo funcional; rascunho não inicia coleta; ativação exige regras, fonte qualificada e adaptador suportado | 0035 |
| Qualidade de código | domínio independente, casos de uso reutilizados, SQL/HTTP/UI separados, sem mover diretórios apenas por estética | todas |
| Entrega e operação | GitHub Actions, migrações reproduzíveis, serviços persistentes, TLS, segredos, testes de acesso/E2E, backup restaurado e alertas exercitados | 0033–0036 |
| Documentação | contratos e instruções operacionais correspondem ao que foi entregue; evidência aponta resultado, fronteira e limitações reais | todas |

Os critérios são cumulativos. Se uma fonte ou serviço impedir um requisito obrigatório, registrar bloqueio e impacto assim que identificado. Uma demonstração local ou uma loteria com lacuna não equivale a lançamento completo. Não marcar a versão concluída apenas para cumprir a data.

## Arquitetura para executar o plano

Manter a direção já documentada: backend Python modular, PostgreSQL e storage persistente, frontend React/Next.js com TypeScript, API/worker/scheduler como processos com responsabilidades claras. Escolher versões compatíveis e fixá-las na primeira entrega, aproveitando as dependências existentes quando adequadas. A tarefa não começa com uma reorganização física de todo o repositório.

Para o orçamento zero, a composição inicial **escolhida na etapa 3** é Vercel Hobby para frontend/API Python leve, Supabase Free para PostgreSQL/Auth/Storage privado e Actions para comandos Python. [Infraestrutura vigente](../architecture/entrega-e-infraestrutura.md) concentra unidades, agendamento, ambientes e recuperação; [segurança](../architecture/seguranca-e-requisitos.md) concentra Google/PKCE, sessões, aprovação e MFA. Uso pessoal não comercial/elegibilidade e cotas serão comprovados na configuração. Não há serviço provisionado por esta decisão.

A Vercel suporta FastAPI como uma função, sujeita aos limites de Functions; Hobby é destinado a uso pessoal não comercial. Colocar somente HTTP curto na API; carga histórica, polling e treino executam fora do request. O cron Hobby é diário e não atende à frequência pretendida. [FastAPI](https://vercel.com/docs/frameworks/backend/fastapi), [Hobby](https://vercel.com/docs/plans/hobby), [cron](https://vercel.com/docs/cron-jobs/usage-and-pricing), [limites](https://vercel.com/docs/functions/limitations). Não usar disco temporário como banco ou depósito permanente de raws.

Supabase Free informa 500 MB para o banco, 1 GB de arquivos e pausa após uma semana de inatividade; backups automáticos não estão incluídos. Medir tabelas, índices, revisões e crescimento real, não apenas o tamanho dos arquivos históricos. Os backups precisam ser exportados, protegidos, guardados fora da origem e restaurados em teste. [Cotas](https://supabase.com/pricing), [backup](https://supabase.com/docs/guides/platform/backups). Validar versão PostgreSQL, migrations, extensão `btree_gist`, papéis restritos, pooling/TLS e limites de conexão antes de aprovar o ambiente; a lista de extensões inclui `btree_gist`, mas isso não substitui o teste do projeto criado. [Extensões](https://supabase.com/docs/guides/database/extensions), [conexão](https://supabase.com/docs/guides/database/connecting-to-postgres).

A decisão é Google OAuth/PKCE com Supabase e recuperação no provedor, sem SMTP próprio na primeira versão. Aprovação, revogação e privilégios continuam sendo regras internas do LottoBrain, com MFA administrativo. Login social não concede acesso automático e não exige dar acesso ao painel do projeto a usuários comuns.

GitHub Actions é o executor escolhido, com jobs curtos devidos após +1h e reconciliação D+1. O schedule pode atrasar/perder disparos; PostgreSQL conserva jobs/leases e o próximo ciclo recupera trabalho. [Agendamento](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule). Não prometer execução exata em uma hora. Modo diário é alternativa aceita por orçamento/fonte e deve aparecer no diagnóstico.

Actions em repositório privado consome a franquia da conta; GitHub Free lista 2.000 minutos mensais, compartilhados também com CI. Confirmar plano/cota, orçamento e bloqueios da conta, retenção de artefatos e limites de gasto antes de habilitar jobs. Não alterar visibilidade do repositório para obter gratuidade. Exemplo apenas para dimensionamento: 300 execuções mensais de dois minutos usam 600 minutos antes de somar testes e backup; não assumir essa duração sem medição. Polling a cada cinco minutos durante o dia inteiro geraria 8.640 execuções em 30 dias e não é o plano. [Franquia](https://docs.github.com/en/billing/reference/product-usage-included), [cobrança e orçamento](https://docs.github.com/en/billing/concepts/product-billing/github-actions).

Render Free foi considerado como alternativa Python, mas não é a primeira escolha: o serviço web dorme após 15 minutos sem tráfego, perde arquivos locais em reinícios e a própria documentação não o recomenda para produção. Também não oferece todos os tipos de serviço gratuitamente. [Limites do Free](https://render.com/docs/free). Evitar depender desse host para um worker permanente ou guardar dados; avaliar outra composição apenas se o teste da API Vercel falhar.

A leitura inicial escolhida usa conjuntos aprovados por modalidade, membros exatos e manifesto imutável. Baseline e política recebem aprovação administrativa; acréscimos elegíveis podem ser promovidos automaticamente pela política, enquanto conflitos aguardam revisão. `published_revision_id` permanece protegido: não remover `publication_not_implemented`. Publicação individual/outbox é evolução posterior, não escolha pendente da primeira tela. Publicar a aplicação com login e disponibilizar um dataset são operações diferentes.

O catálogo já suporta variações; o writer Mega-Sena não é um importador universal. A SPEC-0033 passa a incluir gravação/leitura histórica das seis; a 0034 integra contratos atuais e sincronização. Uma URL não substitui adaptador. As duas entregas têm critérios por perfil, identidade, moeda, componentes e regras.

## Caminho crítico e decisões iniciais

No início da SPEC-0033, comprovar a implantação escolhida e a integração dos perfis necessários; revalidar somente contratos efetivamente alterados ou necessários ao smoke test. A etapa 2 e a decisão arquitetural já estão encerradas. Segredos são configurados por canal apropriado, fora de chat, logs e repositório.

| Dependência ou risco | Ação inicial e responsável | Consequência se pendente |
|---|---|---|
| Hospedagem, cotas e acesso | orçamento inicial zero definido; assistente valida a composição gratuita e o usuário habilita contas/permissões necessárias | publicação e jobs externos bloqueados sem acesso ou cota; ambiente local não resolve o aceite online |
| Fontes alteradas/inacessíveis | assistente verifica contratos reais e avalia alternativa qualificada desde o dia 1 | modalidade fica com estado de atraso/bloqueio; requisito de seis atualizadas continua pendente |
| Escritor/leitor ainda Mega-Sena | assistente implementa perfis históricos das seis na 0033 e incrementais na 0034, sobre o núcleo existente | risco ampliado da primeira entrega; não encerrar com cinco placeholders ou dados fictícios |
| Identidade, recuperação e MFA | implementar Google/Supabase, recuperação no provedor, aprovação e MFA da decisão arquitetural | desenho não comprova conta configurada ou jornada; aceite operacional continua pendente |
| Histórico e análise pesados | carga inicial e treino fora do request web; medir tempo e usar artefatos/snapshots reutilizáveis | não aumentar timeout indiscriminadamente nem reprocessar todo histórico por consulta |
| Prazo versus critérios | reportar cada bloqueio assim que comprovado e revisar a previsão de entrega | ajustar prazo/escopo explicitamente com o usuário; não cortar requisito essencial silenciosamente |

Não há autorização implícita para contratar plano pago, criar recursos com cobrança ou publicar sem os acessos e a aprovação que forem necessários. Preparar configurações, testes e resultado revisável antes de solicitar uma decisão dependente do usuário. A reorganização atual não solicita nova aprovação para tarefas reversíveis já autorizadas.

## Trabalho diário com SDD

1. Abrir a SPEC correspondente: confirmar entradas, critérios e risco técnico principal; o estado continua planejado até começar execução.
2. Fazer um plano curto de implementação dentro da mesma SPEC, incluindo migrations, API/UI, operação e testes necessários à capacidade. Não abrir uma SPEC para cada camada.
3. Implementar o menor fluxo completo, comprovar integração e ampliar dentro da mesma entrega. Quando uma descoberta mudar o contrato, registrar a decisão e o impacto, não escondê-los no código.
4. Demonstrar o resultado no ambiente alvo e relacionar cada critério à evidência. Registrar concluído, parcial ou bloqueado com honestidade; quantidade de testes não é medida de cobertura funcional.
5. Encerrar com um único próximo objetivo funcional, resultados e aprendizados que mudem a próxima implementação.

## Compounding Engineering e redução de retrabalho

- Consultar aprendizados e contratos relevantes antes de redesenhar uma capacidade; referenciar os existentes em vez de copiar seu conteúdo.
- Manter SPEC como aceite/estado, documentação de arquitetura como contrato estável, runbook como operação e evidência como resultado observado. Um assunto tem uma referência principal.
- Acrescentar aprendizado somente quando houver descoberta reutilizável: problema, evidência e ação futura concreta. Não gerar outro documento de repetição por cerimônia.
- Usar testes pequenos para planejamento, domínio, apresentação e falhas locais. Reservar PostgreSQL real para transações, permissões, concorrência e invariantes de persistência.
- Preparar fixture SQL real uma vez por suíte com clones isolados; fortalecer a seleção de cenários para corrigir um teste local sem recarregar todo o histórico. Reexecutar carga integral quando parser, mapeamento, schema ou cobertura histórica mudarem, e no aceite correspondente. Nunca trocar uma aprovação real por um certificado fictício.
- Regenerar fixture/preparação quando mudar versão de schema, parser ou contrato; reutilização de cenário antigo não certifica código novo.
- Rodar testes afetados durante iteração e regressão comum no fechamento; executar a suíte SQL completa quando houver alteração de invariantes compartilhadas e no aceite de release. Não repetir uma suíte pesada já aprovada sem nova mudança, falha ou hipótese a resolver.
- Preservar o caminho legado como referência, sem ampliar suas funções ou duplicar capacidades novas nele. O painel final não utiliza probabilidades fixas nem fallback artificial do protótipo.

## Acompanhamento e encerramento

Em cada checkpoint de execução informar capacidade demonstrável, critérios restantes, bloqueios, evidência e previsão do próximo marco. Indicadores principais: seis fronteiras verificadas, atraso por calendário, execução recorrente bem-sucedida, jornadas de acesso/painel/admin/previsão aprovadas, CI e restauração comprovados. Uma lista de SPECs concluídas é apoio, não o resultado do produto.

No final de cada dia, usar os critérios da SPEC como decisão de passagem. Verificações frequentes e curtas substituem dias sem demonstração. Dia 4 recebe reserva para correções e teste integrado; não concentra toda a segurança, implantação ou preparação de CI.

Permanecem após a primeira versão: laboratório amplo de modelos e busca automática de parâmetros, treinamento pesado distribuído, cadastro com geração automática de adaptadores arbitrários, notificações multicanal, personalização avançada, relatórios sofisticados e otimizações sem demanda medida. O objetivo de previsão permanece; ampliar técnicas exige comparação temporal reproduzível. Microsserviços, Kubernetes, broker e GPU permanente continuam sem justificativa atual.

## Execução do recorte de persistência — etapa 6

A [etapa 6](etapa-6-persistencia.md) reutiliza as entregas anteriores e acrescenta os caminhos comuns SQL das seis, conjuntos aprovados e operação limitada por CLI. Instalação Supabase e regressão CI têm aceite próprio; dados de teste não são apresentados como banco operacional. A criação do projeto foi solicitada ao usuário, que informou ainda não o ter criado. Este recorte não inicia carga integral, autenticação, atualização ou análises e não reinicia as metas originais do plano.
