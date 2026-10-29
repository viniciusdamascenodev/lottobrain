# Contrato do catálogo de loterias

## Finalidade

O catálogo é a camada que responde “quais loterias o sistema conhece e como deve interpretá-las?”. Ele não armazena concursos e não substitui os adaptadores de ingestão.

## Estrutura

```text
LotteryCatalog
└── LotteryCatalogEntry
    ├── Lottery
    │   └── LotteryRuleVersion
    │       └── ResultSeriesDefinition
    │           └── ComponentDefinition
    ├── MarketDefinition
    ├── DataSourceDefinition
    ├── ScheduleDefinition
    ├── ExtensionDefinition
    └── capabilities
```

### O que pertence a cada parte

| Conceito | Exemplos | Local correto |
|---|---|---|
| identidade durável | Mega Millions | `Lottery` |
| matriz que muda no tempo | 5/70 + 1/24 desde 2025 | `LotteryRuleVersion` |
| resultado adicional | Double Play | série adicional da regra e extensão de catálogo |
| recurso do bilhete | Power Play | extensão `bet_feature` |
| produto nacional | My Million | extensão `national_raffle` + mercado FR |
| preço/moeda territorial | € 2,50 na França | futura versão de oferta comercial por mercado |
| horário observado | ter./sex. 21h05, França | `ScheduleDefinition` |
| evidência externa | página oficial ou snapshot | `DataSourceDefinition` |
| possibilidade técnica | possui arrecadação | `capabilities` |

## Autoridade não é prontidão

Uma fonte pode ser oficial e ainda não estar aprovada para automação. Os estados são:

- `research_required`: contrato, termos ou estabilidade ainda precisam de qualificação;
- `contract_observed`: já existe parser e teste do formato observado, sem garantia do fornecedor;
- `approved`: fonte autorizada e operacionalmente qualificada;
- `disabled`: fonte mantida apenas como referência.

Separadamente, a autoridade é `official`, `secondary` ou `manual`. Essa separação impede promover uma página oficial a API estável sem evidência e também permite manter snapshots secundários auditáveis.

## Agenda observada e agenda vigente

Os horários pesquisados em 20/10/2026 estão cadastrados com `observed_at`, porém sem `valid_from`. Isso significa “era o calendário publicado nessa data”, não “este calendário vale desde o início da loteria”. Quando a data de início for comprovada, uma nova versão poderá preencher a vigência sem reescrever o fato observado.

O futuro agendador deverá acrescentar:

- horário de fechamento das apostas;
- horário do sorteio;
- janela esperada de publicação;
- feriados e concursos extraordinários;
- tolerância e política de repetição;
- timezone IANA e tratamento de horário de verão.

## Processo para uma nova loteria

1. Criar `Lottery` em estado `draft`, com slug, nome e jurisdição.
2. Registrar ao menos um mercado e uma fonte de pesquisa.
3. Confirmar matriz e fronteiras históricas; adicionar versões sem sobreposição.
4. Separar série principal, séries vinculadas e recursos de bilhete.
5. Confirmar moeda, timezone, calendário e particularidades territoriais.
6. Qualificar contrato e direito de uso da fonte.
7. Construir fixtures reais e testes de limites, duplicidade, ausência e mudança de formato.
8. Executar reconciliação histórica e incremental.
9. Submeter a ativação à aprovação autorizada.

## Decisões adiadas conscientemente

- Oferta comercial versionada, incluindo preço e opções de pagamento.
- Definições completas de faixas e fórmulas de rateio.
- Persistência e constraints físicas.
- Workflow de aprovação e permissões.
- Serialização pública da configuração.
- Internacionalização de nomes e descrições.
- Herança entre regra global e sobreposição territorial.

Esses elementos foram identificados, mas implementá-los agora criaria decisões físicas antes de validar o primeiro fluxo incremental.

## Previsão como objetivo do produto

O LottoBrain terá como objetivo pesquisar e produzir as melhores previsões possíveis usando matemática, estatística, aprendizado de máquina e IA. Para que melhorias sejam reais e cumulativas, cada experimento deverá registrar dataset, janela temporal, características, algoritmo, parâmetros, semente e métricas contra baselines aleatórios e heurísticos. A ausência de garantia não reduz o objetivo de previsão; define o padrão científico usado para persegui-lo.
