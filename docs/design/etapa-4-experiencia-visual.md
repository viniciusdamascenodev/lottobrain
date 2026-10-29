# Etapa 4 — Experiência visual do LottoBrain

**Estado:** concluída em 28/10/2026 no escopo de desenho de experiência e protótipo local. A prova está em [validação](validacao-etapa-4.md). Não equivale à implementação ou publicação do produto.

## Objetivo e decisões reaproveitadas

Entregar uma experiência navegável para computador e celular, com as seis loterias e administração, a partir dos [contratos do produto](../architecture/contratos-produto.md), do [encerramento dos dados](../data/encerramento-etapa-2.md) e do [plano vigente](../engineering/plano-entrega-quatro-dias.md). Esta é uma única entrega de SDD: requisitos, desenho executável, critérios e verificação. Não cria uma sequência paralela de SPECs nem reabre o inventário.

Conteúdo inteiramente privado; identidade Google/Supabase Auth e aprovação pelo proprietário são decisões de produção. Administrador precisa de MFA. Atualização planejada +1h/D+1 às 09h no fuso da fonte, com modo diário declarado quando necessário. O objetivo preditivo é buscar a melhor previsão mensurável possível, com avaliação temporal, sem inventar desempenho.

O [protótipo](prototipo/index.html) usa 180 sorteios reais preservados, 30 por modalidade. [Proveniência](proveniencia-prototipo.json) identifica arquivos, hashes e fronteiras. O recorte foi preparado para a experiência visual; não é histórico completo, dataset aprovado ou atualização operacional.

## Navegação e composição

| Destino | Conteúdo e ação principal |
|---|---|
| Entrada | Login gerenciado pelo provedor, explicação da aprovação, recuperação no Google |
| Solicitação pendente / revogado / sessão expirada | Mensagem própria, sem resultados ou análises; saída/retorno ao acesso |
| Visão geral | Seis cartões com modalidade, matriz, último resultado da amostra, data e origem |
| Loteria / Resumo | Filtros, quatro indicadores, último resultado da seleção, gráficos e concursos |
| Loteria / Concursos | Histórico paginado, números separados por componente, detalhe e premiação disponível |
| Loteria / Estatísticas | Frequência, soma, componente principal/especial e detalhe de ocorrência/intervalo |
| Loteria / Previsões | Métodos, comparação, explicação da avaliação e ausência explícita de previsão emitida |
| Minha conta | Estado de acesso, papel, recuperação e saída |
| Administração / Pessoas | Aprovação e revogação com motivo e confirmação |
| Administração / Catálogo | Seis perfis, detalhe, cadastro de rascunho e revisão de ativação |
| Administração / Execuções | Política de atualização, fila, estado e solicitação de trabalho |
| Administração / Revisão | Seleção da modalidade, referência, candidato quando existir e decisão |

No protótipo, endereços usam `#/visao-geral`, `#/loterias/{slug}/{resumo|concursos|estatisticas|previsoes}`, `#/conta` e `#/admin/{pessoas|catalogo|catalogo/nova|execucoes|revisao}`. A entrada é `#/entrada`; pendência e revogação são estados dessa experiência. Produção conserva a informação de navegação em rotas do frontend, sem obrigação de reutilizar o roteador demonstrativo.

Desktop tem menu lateral, cabeçalho de contexto e área de conteúdo. Celular tem botão de menu, diálogo de navegação, lista horizontal das seis modalidades e tabelas reorganizadas em cartões. Navegar pelo menu móvel fecha o diálogo. A identidade visual de cada loteria é complementar ao nome, nunca a única identificação.

## Jornadas e permissões

1. Visitante autentica no provedor → solicitação pendente → proprietário aprova → consulta liberada. Autenticação isolada não aprova cadastro.
2. Usuário escolhe modalidade → janela/data → consulta resumo → explora estatística → abre `i` e valores do gráfico → abre concurso/premiação. Filtros reduzem somente a amostra disponível.
3. Usuário abre previsões → compreende métodos e critérios → consulta métricas/previsões quando realmente existentes. Ausência de avaliação é apresentada como ausência, sem pontuação ilustrativa.
4. Administrador confirma MFA → aprova/revoga com motivo. Usuário comum que chega diretamente a uma rota administrativa recebe estado de acesso insuficiente.
5. Administrador cria rascunho de loteria → valida identificador e componentes → revisa requisitos de fonte/regra/calendário → confirma ativação qualificada. Cadastro não executa scripts arbitrários nem cria coletor automaticamente.
6. Administrador acompanha trabalho → solicita intenção suportada → consulta resultado/atraso. Sucesso de execução não altera por si só a fronteira dos dados.
7. Administrador seleciona modalidade em revisão → compara referência/candidato e proveniência → registra decisão. No protótipo não existe candidato real; a ausência é explícita e nenhuma combinação divergente foi inventada.

| Papel/estado | Leitura privada | Administração |
|---|---|---|
| Visitante, pendente, revogado ou sessão expirada | Não | Não |
| Usuário aprovado | Sim | Não |
| Administrador sem segunda etapa | Sim | Solicitação de MFA |
| Administrador com MFA | Sim | Sim, segundo os privilégios do contrato |

Esses controles são **simulados no navegador** para revisar jornadas. Segurança real exige API, sessão, autorização, CSRF, revogação e auditoria na SPEC-0033; esconder botão não garante autorização. O protótipo contém dados públicos de referência nos arquivos e não deve ser publicado como aplicação privada pronta.

## Diferenças das seis modalidades

Matrizes abaixo correspondem ao recorte recente, sem substituir o catálogo histórico.

| Modalidade | Principais | Especiais | Moeda | Período dos 30 registros |
|---|---|---|---|---|
| Mega-Sena | 6 de 1–60 | — | BRL | 18/08–26/10/2026 |
| Lotofácil | 15 de 1–25 | — | BRL | 21/09–26/10/2026 |
| +Milionária | 6 de 1–50 | 2 trevos de 1–6 | BRL | 15/07–24/10/2026 |
| Powerball | 5 de 1–69 | 1 Powerball de 1–26 | USD | 19/08–26/10/2026 |
| Mega Millions | 5 de 1–70 | 1 Mega Ball de 1–24 | USD | 14/07–23/10/2026 |
| EuroMillions | 5 de 1–50 | 2 estrelas de 1–12 | EUR | 17/07–27/10/2026 |

Brasil usa número oficial de concurso. Nas amostras internacionais a interface identifica o sorteio pela data; não inventa número oficial. Power Play e Double Play são apresentados separadamente quando presentes no recorte Powerball. Multiplicador por bilhete da Mega Millions não é convertido em atributo comum do sorteio.

Faixas brasileiras mostram valores publicados por ganhador. A amostra OPEN-NY não oferece essas faixas: a tela informa ausência. Na FDJ os ganhadores europeus e o rateio publicado na França recebem escopos explícitos; não são somados nem apresentados como prêmio global. O recorte visual EuroMillions vem da FDJ preservada, embora o contrato de aquisição futura possa usar SELAE: não trocar a atribuição da amostra por uma fonte planejada.

Novas loterias precisarão suportar quantidades/intervalos/componentes, moedas, fusos, calendários, séries e regras versionadas. O formulário demonstra principais e um componente especial numérico, com limite local de 100 para inspeção visual. Esse limite não é uma regra de domínio universal; símbolos, outras séries ou mais componentes exigem apresentação configurada. Fonte e adaptador são perfis suportados, nunca uma promessa de aceitar qualquer URL. Mudanças de regras geram nova versão com vigência, sem sobrescrever o passado.

## Análises, filtros e explicações

| Elemento | Definição e apresentação |
|---|---|
| Sorteios na janela | Quantidade efetivamente selecionada; não tamanho do histórico inteiro |
| Mais frequente | Principal com maior contagem; empate desfeito pelo número, sem alegar superioridade |
| Média da soma | Média aritmética das somas dos principais, sem especiais |
| Média de pares | Média da quantidade de principais divisíveis por dois |
| Frequência | Barras dos dez números com maior contagem; componente principal/especial separado; valores disponíveis em tabela |
| Evolução da soma | Um ponto por sorteio, em ordem cronológica; eixo horizontal representa a sequência de sorteios, não dias igualmente espaçados |
| Ocorrência/intervalo | Datas observadas e quantidade de sorteios após última ocorrência na janela; não observado = desconhecido, sem alegar intervalo zero |
| Previsões | Frequência/janela, referência aleatória e modelo supervisionado; métricas não calculadas e previsão não emitida são estados próprios |

Todo `i` abre explicação com finalidade, cálculo/população e limites. Pode ser acionado por teclado e toque. Gráficos têm título/descrição e alternativa tabular; a cor não é necessária para recuperar os valores.

Filtros usam data local e janela de até 30/últimos 10 neste protótipo; a URL conserva a seleção nas abas e permite recarregar. Datas inválidas são rejeitadas; período vazio não afirma inexistência de sorteios fora da amostra. Restaurar remove o filtro da URL. Em produção, `DateRuleFilters` também selecionará versões de regra do catálogo, segmentando análises incompatíveis. Não foi criada uma versão histórica falsa para exercitar esse seletor no recorte atual.

Previsão real deverá exibir modelo/versão, dataset e corte, regra, orçamento de combinações, horizonte/horário, componentes e avaliação temporal. Comparar métodos sob o mesmo orçamento; diferenciar backtest de emissão anterior ao alvo. Esses campos são o contrato de apresentação para a SPEC-0035, não resultados já obtidos. Não há geração de combinações, modelo treinado ou acurácia simulada nesta entrega.

## Estados de interface

O controle **Cenários e jornadas**, exclusivo do protótipo, exercita carregamento, vazio, falha com nova tentativa, atraso, fonte indisponível, revisão, conjunto superado e sessão expirada. Não altera a proveniência nem simula uma coleta bem-sucedida como dado novo.

Atualidade e qualidade são dimensões independentes: dados antigos continuam consultáveis com aviso; indisponibilidade da fonte não apaga histórico; dados sob revisão/conjunto superado suspendem novas previsões afetadas. Valores ausentes ficam “não informado/não calculado”, nunca zero por conveniência. Produção apresentará `last_confirmed`, `verified_at`, `next_due_at`, política e estado do contrato; o protótipo não fabrica esses horários operacionais.

Erros de formulário aparecem junto ao formulário, com mensagem compreensível. Operações demonstrativas retornam confirmação acessível. Motivo é obrigatório para decisão de acesso; confirmação de ativação explica os requisitos. Recarregar restaura as demonstrações: nenhuma alteração administrativa é persistida.

## Handoff para implementação

O [sistema visual](sistema-visual.md) é a referência de tokens, composição, componentes e acessibilidade. O HTML/JS local comprova comportamento de UX; não deve virar uma segunda aplicação de produção. Reutilizar desenho, textos, cenários e oráculos de cálculos ao criar os componentes React/TypeScript previstos pela arquitetura, com serviços tipados e dados autorizados da API.

- SPEC-0033: identidade/aprovação/MFA, estrutura visual privada, catálogo de leitura, histórico/detalhe das seis, estados de acesso e CI. A preparação de ambientes/CI da etapa 5 ocorre nessa entrega integrada.
- SPEC-0034: substituir referência estática pelos dados atualizados, estados reais de atualidade/qualidade e execuções agendadas.
- SPEC-0035: conectar gráficos, avaliação preditiva e catálogo administrativo aos casos de uso reais.
- SPEC-0036: provar jornadas completas, acesso, acessibilidade com usuários/tecnologias assistivas, desempenho, publicação e operação.

## Aceitação desta etapa

- [x] Navegação e jornadas de usuário/administrador definidas, com conteúdo privado e aprovação.
- [x] Seis modalidades reais com componentes e disponibilidades distintas.
- [x] Protótipo local para computador e celular, com filtros, tabelas, gráficos, explicações e detalhes.
- [x] Administração de acesso, rascunho/ativação, execuções e revisão navegáveis como simulação.
- [x] Estados de carregamento, vazio, falha, atraso, qualidade e acesso disponíveis.
- [x] Tokens/componentes e adaptação para o frontend documentados.
- [x] Verificação visual, de comportamento, teclado, cálculos e preservação registrada.
- [x] Limite entre desenho entregue e implementação futura explícito, sem alterar o núcleo ou arquivos brutos.

Não restam pendências de desenho essenciais para iniciar a implementação planejada. Validação operacional, segurança efetiva, teste com leitor de tela e avaliação preditiva continuam nos aceites das entregas funcionais; não foram declarados concluídos por este protótipo.
