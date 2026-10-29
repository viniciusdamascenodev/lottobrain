# Validação da etapa 4

**Data:** 28/10/2026. **Resultado:** concluída no escopo de experiência visual, documentação e protótipo navegável local. A [especificação de experiência](etapa-4-experiencia-visual.md) concentra o aceite. Nenhuma capacidade operacional foi certificada por esta entrega.

[Registro final de encerramento](evidencias/encerramento.json): escopo, contagens, preservação e servidor de revisão encerrado. A aba já carregada continua navegável sem novas consultas; para reabrir/recarregar, seguir as instruções locais.

## Verificações executadas

| Recorte | Evidência e resultado |
|---|---|
| Seis loterias × quatro seções em computador | 24 páginas percorridas a 1440×1000; título, seção, painel e ausência de transbordamento horizontal. [Registro](evidencias/rotas-desktop.json) |
| Seis loterias × quatro seções em celular | 24 páginas percorridas a 390×844; mesmos critérios. [Registro](evidencias/rotas-mobile.json) |
| Larguras adicionais | Catálogo e formulário em 320×740, 390×844, 768×1024 e 1024×768, sem transbordamento de página após a correção. Lotofácil também conferida em 320 px. [Registro](evidencias/larguras-adicionais.json) |
| Filtros | Dez registros, período vazio, restauração dos 30 com limpeza da query e erro de intervalo invertido. [Registro](evidencias/filtros.json) |
| Consulta e componentes | Especiais Powerball separados (26 opções), paginação 7–12, detalhe Double Play/Power Play e ausência explícita de faixas OPEN-NY. Detalhe EuroMillions conferido com ganhadores Europa/rateio França. [Registro](evidencias/componentes-e-dialogo.json) |
| Teclado e diálogo | Setas movem foco sem ativar; Enter ativa e conserva foco; Home retorna à primeira aba; abertura/Escape/retorno de foco; atalho de conteúdo mantém rota. Tab/Shift+Tab circulam dentro do diálogo. [Abas e foco](evidencias/teclado.json), [circulação no diálogo](evidencias/componentes-e-dialogo.json) |
| Acesso e administração | Visitante/pendente/revogado/expirado sem painel privado; rota administrativa recusada ao usuário comum; desafio MFA demonstrativo; aprovação/revogação; cadastro duplicado e quantidade inválida; rascunho/ativação local; execução e revisão por modalidade. [Registro](evidencias/jornadas.json) |
| Estados de dados | Carregamento, vazio, erro, atraso, sob revisão, conjunto superado e fonte indisponível. Solicitação de experimento desabilitada nos três últimos cenários de bloqueio previstos. [Registro](evidencias/jornadas.json) |
| Cálculos e integridade | 22 verificações locais: seis matrizes/períodos, frequências/intervalos/somas/pares calculados independentemente, filtros/vazios, datas impossíveis, validação de configuração, seis hashes de origem e contrastes. [Registro](evidencias/calculos-e-integridade.json) |
| Arquivos anteriores | Baseline de 336 arquivos: 329 idênticos; somente sete documentos de navegação/contratos/SPECs/aprendizados alterados; nenhum arquivo anterior removido, código de produção ou relatório/dado anterior modificado. [Registro](evidencias/preservacao.json) |

Sintaxe dos três arquivos JavaScript conferida com Node. Console do navegador sem erros/avisos de aplicação na captura final. Menu móvel abre, navega e fecha. Revisão visual por capturas desktop e celular; ajuste de viewport temporário removido ao terminar. Não houve instalação de dependências, requisição automática às fontes, carga SQL ou execução de pipeline. Os scripts de extração/verificação foram temporários em diretório local ignorado; não viraram infraestrutura de produção.

## Correções durante a revisão

- Restaurar período deixava a query antiga reaplicar os filtros. Agora limpa o endereço e recupera a amostra.
- Troca de aba perdia foco com atualização de DOM e foco adiado. Agora o foco é atribuído ao elemento já renderizado; atalhos de abas foram novamente conferidos.
- O atalho de conteúdo concorria com o roteamento por hash. Agora move foco sem alterar a rota.
- Cabeçalho administrativo transbordava em 320 px. O breadcrumb redundante é omitido nessa largura; menu e ações permanecem visíveis. A tabela/formulário foram novamente conferidos nas quatro larguras.
- O teste de Tab/Shift+Tab mostrou saída do foco do diálogo no navegador de revisão. Foi acrescentada circulação explícita de foco e a prova final confirma permanência nos controles do diálogo.
- A atribuição do recorte EuroMillions foi mantida como FDJ, sem confundir a amostra preservada com a fonte planejada para aquisição futura.

## Capturas para revisão

- [Visão geral no computador](evidencias/desktop-visao-geral.png).
- [Página de loteria no computador](evidencias/desktop-loteria.png).
- [Administração no computador](evidencias/desktop-administracao.png).
- [Lotofácil no celular](evidencias/mobile-lotofacil.png).
- [Menu no celular](evidencias/mobile-menu.png).
- [Administração no celular](evidencias/mobile-administracao.png).

## Limites da prova

Os dados reais são recortes, não históricos completos. A fronteira de cada modalidade consta da proveniência; o texto “referência até 27/10” não afirma que todas têm sorteio naquela data. Faixas indisponíveis, probabilidades não validadas e métricas não calculadas não foram preenchidas artificialmente.

Navegação foi testada por HTTP local no navegador integrado. Os assets são relativos e não exigem servidor de dados/build; abertura direta do HTML é o modo previsto para uso local, mas **não foi testada por `file://`**, protocolo que o navegador integrado não permite. Há instrução de servidor local no [README](prototipo/README.md). Não houve publicação. O servidor temporário de QA foi encerrado; capturas e registros permanecem no repositório.

Teste visual/contraste/teclado não equivale à certificação completa WCAG, teste com leitor de tela, teste em aparelhos físicos ou cobertura entre navegadores. Esses testes e autenticação real, autorização no servidor, CSRF, auditoria, concorrência, jobs, avaliação de modelos e operação online pertencem aos aceites de implementação/publicação. Os arquivos demonstrativos não devem ser promovidos como frontend privado pronto.

## Próxima tarefa

Executar a **SPEC-0033 — Plataforma privada e consulta das seis loterias**, com a preparação de ambientes e CI da etapa 5 integrada. Reaproveitar UX, cenários, fontes, normalizadores e contratos; substituir simulação por serviços autorizados e provar consulta real por perfil. As SPECs 0034–0036 continuam planejadas, sem nova rodada de inventário ou redesenho genérico.
