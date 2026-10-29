# SPEC-0015 — Regras históricas, campos e fontes do EuroMillions

## Estado

Concluída em 2026-10-14.

## Objetivo

Substituir o envelope provisório da SPEC-0014 por regras históricas pesquisadas, esclarecer a semântica dos campos do JSON legado e definir uma hierarquia de fontes para a futura auditoria e coleta.

Esta é uma tarefa de pesquisa e documentação. Não altera normalizador, testes, dados brutos, banco, coleta ou interface.

## Critérios definidos

- Preferir operadores oficiais participantes do EuroMillions.
- Usar data de sorteio e limites inclusivos para selecionar a regra.
- Distinguir fatos comuns do sorteio de prêmios, moedas e promoções nacionais.
- Tratar código aberto da API como autoridade apenas sobre a semântica produzida por ela, nunca sobre a oficialidade do resultado.
- Separar identificador interno, identificador criado pelo provedor e identidade canônica.
- Classificar claramente confirmação, inferência e pendência.

## Matrizes versionadas

| Versão | Vigência inclusiva | Números principais | Estrelas | Linhas no snapshot | Confiança |
| --- | --- | --- | --- | ---: | --- |
| `em_2004_50x9` | 2004-02-13 a 2011-05-06 | 5 de 1–50 | 2 de 1–9 | 378 | alta |
| `em_2011_50x11` | 2011-05-10 a 2016-09-23 | 5 de 1–50 | 2 de 1–11 | 562 | alta |
| `em_2016_50x12` | desde 2016-09-27 | 5 de 1–50 | 2 de 1–12 | 966 | alta |

A página oficial da FDJ oferece arquivos separados justamente nos limites maio de 2011 e setembro de 2016. O snapshot confirma, sem exceções, máximos 9, 11 e 12 nesses três períodos. As lacunas entre versões são dias sem sorteio, não intervalos de regra indefinida.

## Semântica dos campos legados

| Campo | Decisão | Evidência |
| --- | --- | --- |
| `id` | Chave técnica da base de terceiros; não promover a concurso | A migration da API declara `SERIAL` como chave primária. O salto 1.996→3.943 é compatível com estado interno/reimportação e não muda o resultado. |
| `draw_id` | Identificador derivado do provedor; preservar com namespace, não tratar como oficial | O código concatena o ordinal anual com o ano; as 1.906 linhas seguem essa fórmula. |
| `has_winner` | Indica ao menos um ganhador da faixa 5+2 no quadro raspado pela API | O parser só ativa o booleano quando `combination == "5+2"` e `winners > 0`. Não é “houve qualquer ganhador”. |
| `prize` | Prêmio por ganhador da faixa 5+2, em EUR, no quadro Portugal ou, como fallback, Espanha | O parser seleciona `PrizePT`, senão `PrizeES`, remove `€` de “Prize Per Winner” e copia a faixa 5+2. Não é arrecadação nem, necessariamente, jackpot anunciado integral. |
| `date` | Data civil do sorteio | A meia-noite GMT é serialização da API; não comprova horário oficial. |
| `numbers`/`stars` | Combinação sorteada | São extraídos das bolas do resultado secundário; precisam de reconciliação com operador oficial. |

O endpoint legado `/draws` usado pelo projeto foi descontinuado pela própria API em favor de `/v1/draws`. No modelo novo, o `prize` agregado também foi substituído por uma lista de faixas. Portanto, o campo legado pode ser semanticamente promovido para `top_tier_prize_per_winner` com moeda EUR e jurisdição PT/ES **somente como dado atribuído à fonte secundária**, não como fato financeiro oficial certificado.

## Hierarquia de fontes

1. **Resultados históricos comuns:** arquivos ZIP oficiais da FDJ, disponíveis desde fevereiro de 2004 e segmentados nas transições relevantes.
2. **Verificação cruzada:** páginas oficiais de resultados de outro operador participante, prioritariamente Irish National Lottery, para números, estrelas, jackpot e quadro de prêmios.
3. **Regras vigentes:** regulamentos do operador oficial aplicável; a regra irlandesa atual e a página de jogo confirmam 5/50 + 2/12.
4. **Dados financeiros:** manter operador/jurisdição, moeda e definição da métrica. Quadros locais, raffles e códigos nacionais não são fatos pan-europeus automaticamente.
5. **API Pedro Mealha:** baseline secundário e rastreabilidade do snapshot; não será a fonte de autoridade nem a única fonte futura.

A FDJ é a fonte automatizada preferencial para uma prova técnica, porque publica arquivos estruturados oficiais e cobertura desde o primeiro sorteio. A adoção ainda depende de examinar layout, estabilidade, licença/termos, correções retroativas e diferenças francesas como My Million.

## Resultado

As três versões numéricas estão prontas para implementação. `id` foi rebaixado corretamente a chave interna; `draw_id` foi explicado como código derivado; `has_winner` e `prize` ganharam semântica precisa, proveniência e limitações.

Nenhum código, teste, dependência, relatório histórico ou dado bruto foi alterado por esta SPEC.

## Riscos e pendências

- Obter regulamentos históricos primários que descrevam formalmente as matrizes 2/9 e 2/11; os limites já são sustentados pelos arquivos oficiais segmentados e pelo snapshot.
- Fazer a prova técnica dos ZIPs FDJ: formatos por período, encoding, campos, identificador, licença, atualização e correção.
- Definir qual operador será a autoridade financeira do produto ou armazenar valores por jurisdição.
- Confirmar se os arquivos FDJ distinguem jackpot anunciado, prêmio por ganhador, número total de ganhadores e rollover.
- Modelar My Million, Ireland Only Raffle, UK Millionaire Maker e outras extensões como produtos/atributos nacionais separados.
- Pesquisar horário oficial e timezone; continuar armazenando apenas a data civil até então.
- Definir reconciliação quando dois operadores oficiais divergirem ou publicarem correções em tempos diferentes.

## Próxima tarefa recomendada

**SPEC-0016 — Implementar as três matrizes e auditar integralmente o snapshot EuroMillions.**

Justificativa: as regras numéricas e a semântica dos campos agora estão definidas. A próxima redução de risco é validar as 1.906 linhas por vigência, produzir relatório reproduzível e manter os campos financeiros com a proveniência secundária correta antes de criar qualquer coletor.
