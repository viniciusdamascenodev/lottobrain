# Modelo canônico de dados

## Objetivo

Descrever as entidades conceituais aprovadas pela SPEC-0002. Este documento não é um esquema físico de banco e não determina tabelas, índices ou ORM.

O [detalhamento lógico da SPEC-0023](../database/modelo-logico.md) complementa esta base: separa artefato de captura, coloca data/regra na revisão, distingue ponteiro candidato de publicado e especifica observações e passos de sincronização. O [contrato de persistência](../database/contrato-persistencia.md) define como essas relações serão gravadas de forma transacional. As classes atuais ainda não foram migradas por essa decisão documental.

## Convenções

- Campos `*_id` representam referências internas opacas.
- Datas usam calendário ISO; instantes usam UTC e preservam timezone de origem quando conhecido.
- Intervalos de vigência usam início inclusivo e fim exclusivo: `[valid_from, valid_to)`.
- Campos monetários usam decimal e código ISO 4217.
- Metadados livres não substituem campos essenciais nem invariantes.

## Entidades centrais

### Lottery

Representa uma modalidade ao longo de toda a sua existência.

| Campo | Obrigatório | Significado |
|---|---|---|
| `id` | sim | Identidade interna |
| `slug` | sim | Identificador humano estável e único |
| `display_name` | sim | Nome exibido |
| `jurisdiction_code` | sim | País/região responsável |
| `default_timezone` | não | Timezone IANA quando confirmado |
| `default_currency` | não | Código ISO 4217 quando confirmado |
| `status` | sim | `draft`, `validating`, `active`, `suspended`, `archived` |
| `created_at`, `updated_at` | sim | Auditoria temporal |

### LotteryRuleVersion

Define as regras aplicáveis em um período.

| Campo | Obrigatório | Significado |
|---|---|---|
| `id` | sim | Identidade interna |
| `lottery_id` | sim | Loteria proprietária |
| `version_label` | sim | Rótulo legível da versão |
| `valid_from` | sim | Início inclusivo |
| `valid_to` | não | Fim exclusivo; vazio enquanto vigente |
| `status` | sim | Rascunho, validada ou retirada |
| `source_reference` | não | Evidência documental da regra |

Versões da mesma loteria não podem se sobrepor quando validadas.

### ResultSeriesDefinition

Define uma série de resultado possível dentro da regra, como `primary` ou `double_play`.

| Campo | Obrigatório | Significado |
|---|---|---|
| `id` | sim | Identidade interna |
| `rule_version_id` | sim | Regra proprietária |
| `key` | sim | Chave estável dentro da regra |
| `label` | sim | Nome para exibição |
| `role` | sim | Principal ou adicional |
| `required` | sim | Se deve existir em todo concurso dessa regra |

### ComponentDefinition

Define um grupo semântico dentro de uma série.

| Campo | Obrigatório | Significado |
|---|---|---|
| `id` | sim | Identidade interna |
| `series_definition_id` | sim | Série proprietária |
| `key` | sim | `main`, `stars`, `trevos`, `powerball`, etc. |
| `label` | sim | Nome exibido |
| `value_type` | sim | Inicialmente `integer` ou `text` |
| `min_count`, `max_count` | sim | Cardinalidade permitida |
| `min_value`, `max_value` | condicional | Limites de valores inteiros |
| `unique_values` | sim | Impede repetição dentro do componente |
| `order_semantics` | sim | `draw_order`, `sorted` ou `none` |
| `position` | sim | Ordem de apresentação entre componentes |

### ScheduleVersion

Registra o calendário esperado em um período, separado da regra matemática porque um pode mudar sem o outro.

Campos conceituais: `lottery_id`, vigência, timezone, dias da semana, horário esperado, política de feriados e referência documental. Exceções devem ser registros explícitos, não alterações retroativas no calendário-base.

## Concurso e resultados

### Draw

Representa a identidade durável de um concurso.

| Campo | Obrigatório | Significado |
|---|---|---|
| `id` | sim | Identidade interna |
| `lottery_id` | sim | Loteria |
| `rule_version_id` | para publicação | Regra aplicável |
| `draw_date_local` | sim | Data oficial local |
| `scheduled_at` | não | Instante esperado com timezone |
| `official_draw_number` | não | Número oficial confirmado |
| `status` | sim | Estado atual do concurso |
| `current_revision_id` | não | Revisão atualmente aceita |

### DrawRevision

É uma interpretação versionada do concurso produzida a partir de uma ingestão.

Campos: `draw_id`, número da revisão, `ingestion_run_id`, `raw_artifact_id`, instante, status, motivo da alteração e hash canônico do conteúdo.

Uma revisão publicada não é sobrescrita; pode ser substituída por outra revisão auditável.

### ResultSeries

Instância de uma série definida na regra, ligada a uma revisão. Exemplos: resultado principal ou Double Play.

### ComponentValue

Valor individual de um componente.

| Campo | Obrigatório | Significado |
|---|---|---|
| `result_series_id` | sim | Série concreta |
| `component_definition_id` | sim | Semântica e regra do valor |
| `ordinal` | sim | Posição capturada |
| `integer_value` | condicional | Valor quando tipo inteiro |
| `text_value` | condicional | Valor quando tipo textual |
| `source_text` | não | Representação original para auditoria |

Exatamente um campo tipado de valor deve ser preenchido.

### ResultAttribute

Representa propriedades tipadas que não são bolas, como multiplicador. Possui chave, tipo, valor e referência à série ou revisão. Não deve ser usado para esconder componentes ou dinheiro que possuam modelo próprio.

## Premiação

### PrizeTierDefinition

Define uma faixa dentro de uma versão de regra: chave, rótulo, posição e descrição do critério. Regras combinatórias complexas devem começar como contrato explícito e testado; não será criada nesta fase uma linguagem genérica de expressões.

### PrizeTierResult

Resultado de uma faixa em uma revisão:

- `prize_tier_definition_id`;
- quantidade de ganhadores, admitindo zero;
- valor por ganhador;
- valor total, quando fornecido;
- localizações de ganhadores, quando disponíveis;
- estado de completude.

### MonetaryAmount

Montante associado a concurso, revisão ou faixa.

| Campo | Obrigatório | Significado |
|---|---|---|
| `amount` | sim | Decimal |
| `currency` | para publicação | ISO 4217 |
| `kind` | sim | Finalidade semântica |
| `status` | sim | Conhecido, desconhecido, não aplicável ou rejeitado |
| `source_text` | não | Texto original |

## Fontes e rastreabilidade

### DataSource

Cadastro da origem: loteria, nome, autoridade (`official`, `secondary`, `manual`), formato, URL-base, status e política de uso. Credenciais são apenas referenciadas; nunca ficam no registro ou no repositório.

### IngestionRun

Execução observável de aquisição ou importação: fonte, início/fim, versão do adaptador, status, contagens, erro e identificador de correlação.

### RawArtifact

Evidência imutável: execução, localização, formato, MIME type, SHA-256, tamanho, instante de captura, URL efetiva e metadados HTTP aplicáveis.

### ExternalReference

Preserva identificadores da fonte sem transformá-los em identidade interna: `source_id`, entidade interna, namespace, valor e período/versão quando necessário.

### ValidationIssue

Falha ou alerta ligado a uma revisão ou artefato: código estável, severidade, caminho do campo, valor observado, regra esperada, mensagem e estado de resolução.

## Relações

```text
Lottery 1 ── N LotteryRuleVersion
Lottery 1 ── N ScheduleVersion
Lottery 1 ── N DataSource
Lottery 1 ── N Draw

LotteryRuleVersion 1 ── N ResultSeriesDefinition
ResultSeriesDefinition 1 ── N ComponentDefinition
LotteryRuleVersion 1 ── N PrizeTierDefinition

Draw 1 ── N DrawRevision
DrawRevision 1 ── N ResultSeries
ResultSeries 1 ── N ComponentValue
ResultSeries 1 ── N ResultAttribute
DrawRevision 1 ── N PrizeTierResult
DrawRevision 1 ── N MonetaryAmount
DrawRevision 1 ── N ValidationIssue

DataSource 1 ── N IngestionRun
IngestionRun 1 ── N RawArtifact
IngestionRun 1 ── N DrawRevision
DataSource 1 ── N ExternalReference
```

## Valores derivados

Frequência, soma, paridade, atraso, sequência, estatísticas, scores e previsões não pertencem ao núcleo do concurso. Devem ser calculados a partir de revisões publicadas e guardar versão do método e dataset quando persistidos.

Também são derivados:

- números ordenados para exibição, quando a fonte preserva ordem de extração;
- dia da semana;
- situação de atraso da coleta;
- total de uma faixa quando obtido por multiplicação;
- moeda padrão, que só pode ser aplicada após confirmação contextual.

## Pendências para o esquema físico

- tipo concreto dos IDs internos;
- estratégia de constraints para períodos sem sobreposição;
- representação física de valores tipados;
- política de revisão e promoção de `current_revision_id`;
- índices e particionamento;
- retenção e armazenamento dos artefatos raw;
- expressão física dos estados de ausência;
- política de exclusão, que nunca deverá apagar auditoria histórica indevidamente.

