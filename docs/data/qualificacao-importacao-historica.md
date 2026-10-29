# Qualificação da importação histórica — SPEC-0026

## Resultado e limites

Leitura offline em 21/10/2026: **15.471 registros representáveis, zero rejeições, zero identidades/referências externas duplicadas dentro de cada histórico**. As 20 versões de regras possuem vetores reais de início e fim. Não houve escrita SQL, importação histórica, consulta de rede, alteração de raw ou normalizador existente.

“Qualificado” significa que a transformação em memória foi comprovada para estes arquivos e contratos. Não certifica a veracidade econômica de todo prêmio, a completude perante todas as fontes oficiais, a atualização até hoje, o roundtrip SQL das seis fontes ou sua publicação. Os históricos continuam terminando em dezembro de 2025.

| Histórico | Registros | Período observado | Identidade | Regras / vetores |
|---|---:|---|---|---:|
| Mega-Sena XLSX | 2.954 | 11/03/1996–20/12/2025 | oficial 1–2954 | 1 / 2 |
| Lotofácil XLSX | 3.571 | 29/09/2003–24/12/2025 | oficial 1–3571 | 1 / 2 |
| +Milionária XLSX | 314 | 28/05/2022–24/12/2025 | oficial 1–314 | 1 / 3 |
| Powerball HTML | 3.742 | 22/04/1992–24/12/2025 | provisória por data | 7 / 15 |
| Mega Millions HTML | 2.984 | 06/09/1996–23/12/2025 | provisória por data | 7 / 15 |
| EuroMillions JSON | 1.906 | 13/02/2004–26/12/2025 | provisória por data | 3 / 8 |

Evidência computável: [relatório fixado](qualificacao-importacao-spec-0026.json). Contém hashes raw antes/depois, receitas, fingerprint de catálogo, contagens por regra, estados financeiros e manifestos dos mapeamentos. Nenhum relatório anterior foi atualizado para aparentar uma nova execução.

## Componentes e políticas por fonte

| Fonte | Representação qualificada | Cuidado obrigatório |
|---|---|---|
| `caixa_mega_sena_xlsx` | main 6/60; três faixas; quatro medidas BRL | não possui ordem de extração nem fundo final 0/5 separado |
| `caixa_lotofacil_xlsx` | main 15/25; cinco faixas; quatro medidas BRL | valores históricos observados, sem recalcular com tabela de prêmios atual |
| `caixa_mais_milionaria_xlsx` | main 6/50, clovers 2/6; dez faixas; duas medidas BRL; rolled_over booleano | faixas 0 ou 1 trevo continuam agregadas; flag não é dinheiro |
| `usamega_powerball_html` | main + powerball por regra; jackpot anunciado USD; Power Play inteiro; Double Play separado | multiplicador não é bola; séries não viram dois concursos |
| `usamega_mega_millions_html` | main + mega_ball por regra; jackpot anunciado USD; Megaplier histórico inteiro | desde a matriz de 2025, multiplicador de bilhete não é um número sorteado ausente |
| `pedromealha_euromillions_api_json` | main 5/50 + stars 2/9, 11 ou 12; prêmio individual EUR; has_jackpot_winner booleano | escopo `provider_pt_or_es`; IDs privados não são concurso oficial; true não significa um ganhador |

Powerball: 680 séries Double Play, 2.606 resultados com Power Play observado, 926 anteriores à aplicabilidade e 210 com política de prêmios fixos sem multiplicador. Mega Millions: 682 sem aplicabilidade, 2.227 com Megaplier sorteado e 75 com multiplicador individual de bilhete. EuroMillions: 1.897 valores conhecidos e **nove desconhecidos**, preservando o zero original na evidência; nenhuma quantidade de ganhadores foi inferida.

`ordinal` segue a tupla normalizada, não a extração. No caso dos trevos, conserva a ordem das colunas, mesmo que não seja crescente. Nos 45 vetores históricos, `extraction_ordinal` permanece nulo. Apenas o JSON Mega-Sena qualificado fornece ordem de extração explícita. A ordem das séries/componentes no JSON canônico é por chave: `primary` deve ser identificado pela chave/definição, nunca pela posição da lista.

As regras vigentes vêm do catálogo já qualificado; lacunas entre vigências não são preenchidas por conveniência. Campos de símbolos/bilhetes nacionais e novas modalidades não são inventados: exigem novo contrato e evidência antes de ampliar os perfis.

## Contrato, hashes e evidência

Implementação pura: `app/application/historical_content.py`. Versão `lottobrain.historical.result.v1`, código `spec-0026-v1` e política `spec-0026-observed-sources-v1`.

- Perfis explícitos vinculam fonte, loteria, medidas, faixas, atributos e moeda observada. Não se deduz moeda do default do catálogo. Fonte, campo, moeda ou contexto inesperados são recusados, não descartados silenciosamente.
- A entrada é um candidato **já aprovado pelo normalizador específico**; o mapper também revalida a regra/domínio e compatibilidade com o envelope relacional. Não substitui a validação estrutural do raw.
- Conteúdo inclui alias com namespace/assurance, data, versão da regra, séries/componentes, atributos tipados, faixas, medidas e metadados semânticos. Atributos atuais são booleanos/inteiros; não se proclama qualificada toda extensão textual/decimal possível no schema.
- Ausências seguem unknown/not_applicable/rejected com amount/currency nulos; known conserva zero e moeda. Ganhadores têm estado independente. Ausência de uma faixa inteira não é convertida em zero ganhador.
- Valores usam Decimal exato, sem float; decimais normalizados sem zeros fracionários insignificantes, zero negativo convertido em zero. Envelope SQL: finito, não negativo, até 10¹⁸ e seis casas significativas fracionárias. Isto não amplia a política de duas casas do normalizador JSON BRL.
- Escopo financeiro e forma de pagamento entram no hash. Forma é `unspecified`: não afirmar cash/annuity sem evidência. Jackpot anunciado, prêmio individual, arrecadação e estimativa seguinte continuam medidas distintas.
- Serialização UTF-8, chaves ordenadas, JSON compacto, Unicode preservado, sem NaN/Infinity; SHA-256 desses bytes. IDs SQL, relógio da leitura, estado operacional e proveniência não integram o hash de conteúdo.
- Referências privadas, textos de moeda/local/observação e texto da data ficam em `source_evidence`, com hash próprio. A evidência não pode ser descartada ao deduplicar conteúdo. O manifesto agrega receita + raw SHA + ordinal do registro + hashes de conteúdo/evidência, em ordem cronológica determinística.
- `data_record_ordinal` é 1-based sobre os registros emitidos pelo leitor aprovado. Não é o ID do provedor nem necessariamente a linha física do Excel; cabeçalho/linhas vazias seguem o leitor. Raw SHA, leitor versionado e ordinal juntos permitem localizar o caso.
- `observed_at` é o instante de inspeção local, não o instante original de download. Não fabricar timestamp de captura histórica ao importar.

Vetores fixos: `tests/fixtures/historical_relational_v1.json`, 45 casos com conteúdo/hash, evidência/hash, arquivo, raw SHA, localizador e motivo de cobertura. Seleção determinística: primeiro/último resultado de cada regra e primeiro caso dos estados semânticos relevantes. Não são dados fictícios nem uma amostra aleatória.

## Mega-Sena 2954: XLSX versus JSON

A fixture JSON existente é uma transcrição formatada, **não os bytes originais HTTP**. Seu SHA é `b248665f1736f655b190f1ce143371108781aaf90bd2150ea7832522f072ec85`; o receipt real continua com seu hash raw próprio e não foi reescrito.

Há 12 grupos de fatos compartilhados iguais: identidade, data, loteria, regra, combinação, três faixas completas e quatro medidas. Não há divergência nesses grupos. Há cinco grupos presentes apenas no JSON: ordem de extração, local, município/UF do sorteio, indicador de acumulação e fundo final 0/5. Cidade de ganhadores do XLSX não deve ser confundida com cidade do sorteio.

| Representação | SHA-256 do conteúdo |
|---|---|
| JSON relacional da SPEC-0025, mantido | `62755ae7c8057839aa4fcb97c2840afbc6e0a296844f7b02fb6d66f81bbe6477` |
| XLSX no contrato histórico v1 | `62b57bf0ba64c0e65431a5078dd8c85e4ceb8dc59556e27b03daad1435b6a0f8` |
| JSON comparado no contrato histórico v1 | `52f1934a2707b46a29dc55572ce82438fb32d371aceb2bdbd327ad2dadec7a41` |

Esses hashes diferentes são esperados, não corrupção. A comparação distingue compartilhado igual, compartilhado divergente e exclusivo de cada fonte. É ferramenta de diagnóstico, **não merge ou autorização de substituir head**. Valores unknown comparados a known são diferenças de estado, não autorização para apagar um valor conhecido.

## Correspondência com o schema existente

| Contrato / evidência | Destino relacional planejado |
|---|---|
| arquivo integral, SHA e tamanho | raw_artifact + capture_receipt legacy_import, com referência de origem e instante honesto de registro |
| normalizador, código, canonicalização, política, catálogo | processing_run; tentativas de execução em processing_attempt |
| ordinal + conteúdo/hash + source_evidence | candidate_observation com row_locator estável e diagnostic_payload versionado; referência ao raw permanece no receipt |
| alias oficial/provisório | draw_identity, relacionado ao UUID durável de draw e à observação de suporte |
| IDs/path da fonte | external_draw_reference por source_id/namespace/value, nunca PK do concurso |
| data/regra/hash/metadados semânticos | draw_revision; identidade canônica reconstruível sem depender de alias posteriormente alterado |
| série/componente/ordinal/extração | result_series + component_value, ligados às definições da mesma regra |
| atributo/value_type/value | result_attribute, escolhendo exatamente a coluna do tipo correspondente |
| faixa/escopo/variante/estado de ganhadores | prize_tier_result, com definição qualificada e variant_key=base |
| medida/estado/valor/moeda/source_text | monetary_fact, com escopo/faixa/forma explícitos |

O conteúdo selado não recebe textos de outra captura depois. Para uma observação de apoio sem nova revisão, sua evidência continua no raw/diagnostic_payload, sem tentar atualizar monetary_fact/source_text imutável. O futuro writer deve testar tamanho e roundtrip desse payload; não duplicar o arquivo inteiro nele.

Não foi necessária migration para o **contrato de mapeamento**. Isso não prova que todos os requisitos operacionais de batch já cabem sem DDL novo.

## Bloqueios antes da importação

1. O adaptador SQL atual é específico do JSON Mega-Sena e recusa outra canonicalization_version. Não receberá estes conteúdos por troca de constante ou reaproveitamento forçado.
2. É preciso uma ponte explícita entre contratos/fontes: comparar fatos sob a mesma representação transitória, manter versão/hash original da revisão e registrar diferenças/apoios. JSON mais completo não pode ser rebaixado pelo XLSX. Sem política/prova da ponte, falhar fechado.
3. Aprovar catálogo físico por regra/fonte/escopo/faixa, permissões e fingerprint antes da escrita. O seed dos testes não é provisionamento de produção.
4. Definir proveniência de importação legada: não há timestamp confiável do download original dos seis arquivos. Registrar inspeção/importação como tal, com referência explícita, sem falsificar HTTP.
5. Implementar roundtrip SQL, T3 por registro/lote limitado, idempotência e retomada por localizador. Os testes desta SPEC são de transformação em memória; não substituem essas provas.
6. Comprovar cobertura materializada antes de promover baseline. O schema atual torna baseline referenciada imutável; mudar estado requer fluxo/migration dedicado, nunca UPDATE ad hoc. Checkpoint numérico Mega-Sena não serve para IDs privados estrangeiros.

## Plano de importação auditada, ainda não executado

1. Começar por **piloto Mega-Sena limitado**, em PostgreSQL descartável, com linhas reais identificadas e sobreposição JSON 2954. Sem banco operacional e sem carga integral.
2. Fixar input manifest, versões, catálogo e plano de linhas; validar hashes e normalizar fora de transação. Intenção repetida com outra entrada deve ser conflito explícito.
3. Registrar o arquivo como evidência legada sem inventar GET; vincular receita e localizador. Preservar evidência distinta mesmo quando não se cria revisão.
4. Reconhecer alias e versão existente sob lock; aplicar política explícita da ponte. Divergência real entra em revisão/quarentena, não merge silencioso. Apoio parcial não remove fatos do head mais completo.
5. Confirmar observação/revisão/filhos de cada unidade atomicamente; retomar sem duplicar efeito, sem regredir head. Erro SQL abortado pode repetir SQL, não aquisição. Uma linha problemática não permite anunciar todo o arquivo concluído.
6. Relê-lo do SQL e reconstruir hash no contrato declarado. Conferir contagens, faixas, escopos, ordinais, ganhos/ausências, recibos e proveniência. Simular interrupção e repetir o mesmo plano/chave.
7. Só após esse piloto, especificar importação completa por modalidade, cobertura e eventual promoção de baseline. Publicação, atualização online e API permanecem tarefas posteriores.

## Reprodução

No ambiente virtual, a partir da raiz:

```powershell
.venv\Scripts\python -m app.ingestion.historical_qualification
.venv\Scripts\python -m app.ingestion.historical_qualification --vectors
.venv\Scripts\python -m pytest tests/test_historical_qualification.py -q
```

As duas CLIs escrevem apenas stdout; não salvam candidatos, relatórios nem dados. Código 0 indica transformação qualificada; código 1 indica diagnóstico reprovado. Falha de leitura/parsing aborta a execução, sem afirmar qualificação. Requer os arquivos locais e openpyxl já usado pelo projeto; não precisa de PostgreSQL nem de novas dependências.

A saída CLI usa escapes Unicode para atravessar pipes Windows sem depender de cp1252/UTF-8 do terminal. Depois de ler o JSON, os textos originais são restaurados; os hashes canônicos continuam sobre UTF-8 com Unicode preservado.

## Verificação final

Verificação final desta etapa: **244 testes aprovados** (181 comuns, incluindo 24 novos; 63 de regressão isolada, dos quais 58 PostgreSQL reais e cinco de UoW simulado). Hashes dos 30 arquivos protegidos mantidos; auditoria local anterior idêntica/healthy. Cluster descartável desligado, serviços existentes preservados. Nenhuma dessas verificações executou o novo contrato histórico como importador SQL.

## Próxima tarefa recomendada

**SPEC-0027 — Importação histórica piloto da Mega-Sena, com reconciliação XLSX/JSON e retomada.**

Justificativa: provar em SQL, com poucas linhas reais e interrupções controladas, os pontos que esta qualificação não cobre — ponte de contratos, apoio parcial, preservação da evidência e retomada — antes de ampliar para 15.471 registros. A política e os testes do piloto devem ser especificados antes de implementar seu writer. Não executada nesta SPEC.
