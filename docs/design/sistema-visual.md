# Sistema visual e componentes

Referência da [etapa 4](etapa-4-experiencia-visual.md). O código visual executável está em [styles.css](prototipo/styles.css), sem biblioteca ou serviço externo.

## Direção e tokens

Painel analítico claro, com hierarquia de informação, gráficos legíveis e identificação por modalidade. Fundo discreto, cartões brancos, bordas suaves e uma ação principal azul. Evitar dezenas de indicadores sem propósito e alegações de atualização/previsão sem evidência.

| Token | Valor / uso |
|---|---|
| Fundo / superfície | `#f5f7fb` / `#ffffff` |
| Texto / texto secundário | `#18253e` / `#5d6c83` |
| Ação / ação forte | `#2454c6` / `#173b91` |
| Borda / seleção suave | `#dce3ed` / `#eaf0ff` |
| Positivo / alerta / erro | `#146b4a` / `#825307` / `#a72d42`, sempre acompanhados de texto |
| Mega-Sena / Lotofácil / +Milionária | `#146b4a` / `#793a91` / `#234c98` |
| Powerball / Mega Millions / EuroMillions | `#a73a47` / `#9a5c0c` / `#155e83` |
| Especiais | Fundo `#fff6e6`, texto `#875908`, contorno e título próprio |
| Tipografia | Segoe UI, Arial e alternativas locais; sem download de fontes |
| Hierarquia | Título 26–36 px, seção 16–18 px, corpo 14 px, metadados compactos 10–12 px |
| Espaçamento / curvas | Ritmo aproximado de 4 px, seções 18–24 px, cartões 16 px, controles 8–10 px |

Números usam algarismos tabulares, dois dígitos e círculos que quebram linha. O nome do componente distingue principais/especiais. Não usar o círculo de um especial para representar multiplicador, símbolo ou série complementar.

## Composição responsiva

Desktop: menu de 228 px, conteúdo de até 1440 px, indicadores em quatro colunas, gráficos em duas, visão geral em três. Até 1180 px o menu reduz e a visão geral passa a duas colunas. Até 850 px o menu vira diálogo; até 600 px gráficos/formulários empilham, indicadores ficam em duas colunas e tabelas de resultados/administração viram cartões. Em 320 px o cabeçalho omite o breadcrumb redundante e mantém menu, papel e origem.

As seis loterias têm uma única lista horizontal de seleção, com rolagem própria em telas estreitas. A página inteira não deve rolar horizontalmente. Tabelas densas de valores financeiros podem usar rolagem local. O menu lateral permite rolagem em computadores de pouca altura, preservando ações acessíveis.

## Contratos dos componentes

| Componente previsto | Responsabilidade e reuso do protótipo |
|---|---|
| `AppShell` / `Navigation` | Menu, cabeçalho, conteúdo, contexto privado e versão móvel; não autentica |
| `LotteryTabs` | Seis perfis do catálogo, nome/acento e navegação por modalidade |
| `SectionTabs` | Resumo, concursos, estatísticas e previsões; foco e seleção separados |
| `FreshnessBadge` / `QualityNotice` | Apresentar atualidade e qualidade independentes, sem inferir ambas pelo job |
| `DateRuleFilters` | Datas, janela e regra qualificada; parâmetros conservados em URL |
| `ComponentNumbers` | Quantidades e intervalos do perfil; principais/especiais/séries distintos |
| `DrawTable` / `DrawDetail` | Identidade oficial ou data, paginação, proveniência, financeiros por escopo |
| `AnalysisCard` / `AnalysisInfo` | Valor/gráfico, unidade, janela e explicação por teclado/toque |
| `ChartDataTable` | Alternativa textual/tabular do mesmo conjunto mostrado pelo gráfico |
| `ForecastComparison` | Modelo, corte/orçamento, métricas, ausência e distinção backtest/emissão |
| `AccessRequests` | Estado, motivo, confirmação, aprovação/revogação e retorno acessível |
| `LotteryDraftForm` | Identificador único, componentes, moeda/fonte/fuso/política; rascunho antes de ativar |
| `JobStatus` / `DataReview` | Intenções suportadas, andamento/atualidade, referência/candidato/decisão |
| `Dialog` / `Field` / `Notice` | Primitivos compartilhados, mensagem clara, foco e estado consistente |

Componente visual não acessa banco, segredo, provedor ou coletor. No frontend real, composição de páginas fica em `app`, comportamento em `features`, primitivos em `design-system`, componentes comuns em `components` e cliente tipado em `services`, conforme a arquitetura existente. O módulo `model.js` serve somente aos cálculos locais desta demonstração; não substitui o motor analítico versionado do backend.

## Acessibilidade e linguagem

Alvo de projeto: WCAG 2.2 AA nas jornadas do produto. A validação local conferiu pares principais de contraste com mínimo de 4,97:1; isso não certifica todas as combinações, estados ou tecnologias assistivas.

- Abas: Tab entra na aba ativa; setas/Home/End movem foco, Enter/Espaço ativam. `aria-selected`, `aria-controls` e painel rotulado correspondem à seção visível. Trocar de rota coloca foco no título; trocar de aba conserva o foco nela.
- Diálogos: título recebe foco, Tab fica no diálogo nativo, Escape/fechar devolvem foco ao acionador ainda existente. Botão `i` tem nome acessível, sem depender de hover.
- Atalho “Pular para o conteúdo” move foco para o conteúdo sem trocar a rota. Controles têm foco visível. Movimento reduzido é respeitado.
- Controles principais móveis têm altura de 44 px; o símbolo `i` conserva aparência pequena com área de toque de 44×44 px. Controles de revisão do protótipo têm espaçamento próprio.
- Gráficos têm título, contagem/unidade e tabela expansível. Principais e especiais têm nomes; estado tem texto, além da cor.
- Formulários têm rótulos associados, instruções e erros anunciados; dados vazios e métricas indisponíveis não são preenchidos com zero.
- Textos de demonstração são explícitos. Login não pede senha; MFA orienta usar seis dígitos demonstrativos. Não solicitar dados pessoais reais no protótipo.

Referências de implementação: [WCAG 2.2](https://www.w3.org/WAI/WCAG22/quickref/), [padrão de abas WAI-ARIA](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/) e [padrão de diálogo modal](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/). Teste real com leitor de tela, ampliação, diferentes navegadores e sessões de produção integra o aceite de publicação.
