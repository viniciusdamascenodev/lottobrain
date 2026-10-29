# SPEC-0035 — Painel analítico, previsões e catálogo

## Estado e objetivo

Planejada em 26/10/2026; não implementada. Meta do dia 3 do [plano de quatro dias](../engineering/plano-entrega-quatro-dias.md): usuários autorizados exploram as seis loterias, entendem os gráficos, consultam previsões avaliadas e administradores gerenciam o catálogo pelo sistema.

## Reuso e dependências

Reutilizar a [experiência e os critérios da etapa 4](../design/etapa-4-experiencia-visual.md), o [sistema visual](../design/sistema-visual.md) e seus cenários. O novo protótipo local usa recortes reais e não inventa probabilidades; o motor analítico/preditivo e a administração persistente continuam exigindo implementação e validação nesta SPEC. A restrição ao pipeline artificial abaixo refere-se ao protótipo legado de `app/web`, que não foi alterado.

Usar snapshots/conjuntos aprovados, APIs, contas e estado de atualidade das entregas anteriores. O catálogo existente é a autoridade para regras e componentes. Reutilizar contratos de dados; não usar o pipeline de probabilidades fixas nem o fallback artificial do protótipo.

## Atividades integradas

1. Completar as seis páginas/abas com filtros por período e regra, identidade visual compartilhada, responsividade e estados de carregamento, vazio, atraso e falha.
2. Entregar frequência de números, evolução em janelas, pares/ímpares, distribuição de somas e intervalos entre ocorrências. Números principais e especiais usam suas próprias regras. Cada análise informa pelo ícone de informação: objetivo, cálculo, período, unidade, interpretação e limitações; explicação também acessível por teclado e toque.
3. Produzir snapshots/features temporais versionados, referências uniforme aleatória, frequência e janela móvel, mais ao menos um modelo supervisionado simples para cada contrato qualificado. Usar features de concursos anteriores para avaliar o próximo resultado; nunca treinar a previsão de um sorteio com outras bolas do próprio sorteio.
4. Executar backtesting temporal com orçamento comparável, métricas pertinentes e configuração/seed/dataset registrados. Respeitar fronteiras históricas de regras. Publicar previsão de concurso futuro antes do evento, com versão imutável e indicação do estado do experimento; mostrar desempenho inferior quando ocorrer.
5. Entregar administração do catálogo: cadastro/edição de rascunho, regras versionadas, fontes e calendário, validação, revisão e ativação explícita. Cadastro não executa URL arbitrária nem cria adaptador automaticamente. Uma nova modalidade com fonte suportada pode atravessar o fluxo; formato novo exige qualificação de código específica.
6. Integrar o acompanhamento dos jobs e a aprovação/revogação de usuários na administração, com autorização backend e auditoria das alterações sensíveis.

## Aceitação

| ID | Prova necessária |
|---|---|
| S35-01 | Seis loterias navegáveis com dados reais aprovados, filtros consistentes, gráficos legíveis em desktop/mobile e explicações por teclado/toque |
| S35-02 | Estatísticas conferidas com casos reais conhecidos; sem mistura indevida de regras, séries ou período; snapshot/fronteira e atualidade identificáveis |
| S35-03 | Referências e modelo supervisionado executam avaliação temporal reproduzível para os seis contratos e exibem métricas sem vazamento temporal; resultados experimentais inferiores não são ocultados |
| S35-04 | Previsões respeitam quantidade/intervalo de números, identificam regra/dataset/modelo e ficam preservadas após emissão; métricas ausentes são desconhecidas, não valores fixos inventados |
| S35-05 | Administrador cria rascunho de modalidade, recebe erros úteis para configuração inválida e só ativa fonte/adaptador qualificados; usuário comum e URL não autorizada são recusados |
| S35-06 | Jornadas explorar→entender análise→comparar métodos e administrador→cadastrar→validar são aprovadas por E2E, incluindo falhas e estado desatualizado |

## Validação e evidência

Testar cálculos/features e acesso em camadas pequenas. Usar E2E para jornadas reais, sem reimportar todos os históricos por componente. Registrar snapshots, configurações, splits temporais, métricas e exemplos emitidos; treinos ficam fora do request de página. Repetir um experimento com a mesma configuração deve permitir conferir seu resultado.

O objetivo é buscar a melhor previsão mensurável possível. O aceite do sistema não exige demonstrar que um modelo supera o acaso em quatro dias; exige tentativa real, avaliação válida e apresentação honesta do que foi encontrado. Um método não validado permanece identificado como experimento, sem promoção enganosa.

## Limites e passagem

Adiar laboratório amplo de algoritmos, AutoML, treinamento distribuído e refinamentos visuais sem efeito nas jornadas. Manter gráficos essenciais, acessibilidade, métodos iniciais e cadastro funcional. Nova loteria cadastrável não significa suporte automático a todo formato de provedor.

Ao comprovar os critérios, consolidar os aprendizados científicos e de interface e seguir para **SPEC-0036 — Validação operacional e publicação**.
