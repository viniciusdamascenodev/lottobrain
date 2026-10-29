# EuroMillions — contrato de extração do JSON

## Escopo

Esta etapa valida leitura e normalização de amostras reais de `data/raw/euro_millions/euro_millions_resultados.json`. Não certifica regras históricas, IDs, moeda ou semântica financeira e não publica um histórico canônico.

Fonte conhecida: API de terceiros `euromillions.api.pedromealha.dev/draws`. O arquivo não preserva URL efetiva completa, resposta HTTP, instante de captura ou versão do coletor. Hash antes/depois: `e4e7f97102c868569e33d54e34e258671cfca98f6872cf21fc0f86b171e57914`.

## Estrutura observada

Lista de 1.906 objetos, de 2004-02-13 a 2025-12-26. Todos possuem exatamente:

- `date`: texto no formato `Fri, 13 Feb 2004 00:00:00 GMT`;
- `draw_id`: inteiro positivo;
- `has_winner`: booleano;
- `id`: inteiro positivo;
- `numbers`: cinco strings inteiras;
- `prize`: número JSON;
- `stars`: duas strings inteiras.

Não há campos ausentes, extras, datas duplicadas, `id` repetido ou `draw_id` repetido. Todos os números e estrelas são distintos e crescentes dentro de seus grupos.

## Contrato semântico

- `numbers` vira `primary.main`; envelope observado: cinco distintos entre 1 e 50.
- `stars` vira `primary.stars`; envelope observado: duas distintas entre 1 e 12.
- `has_winner` vira atributo booleano da série principal.
- `id` e `draw_id` viram referências externas separadas; nenhum vira `official_draw_number` até pesquisa da fonte.
- A data civil vira identidade canônica provisória.
- O horário `00:00:00 GMT` é preservado como texto, mas não é tratado como horário real do sorteio.
- Campos extras/ausentes, coleção com tipo errado e valores de tipo inesperado geram diagnóstico.

O parser usa `Decimal` na leitura de números fracionários para não introduzir ruído binário adicional. Isso preserva a representação JSON sem certificar sua precisão de origem.

## IDs

Há 1.906 valores únicos em ambos os campos. `id` varia de 1 a 4.058 e possui 2.152 lacunas. Uma descontinuidade visível ocorre entre 2024-11-15 (`id=1996`) e 2024-11-19 (`id=3943`). Portanto, ele não é tratado como sequência de concursos.

`draw_id` varia por ano e aparenta concatenar ordinal do sorteio com ano, como `1032025`, mas 1.560 linhas não coincidem com uma fórmula simples de semana do calendário. Sua semântica deve ser confirmada; o contrato só preserva o valor.

## Prêmio e vencedor

`has_winner` é verdadeiro em 440 registros e falso em 1.466. O significado aparente é existência de vencedor do jackpot, mas requer confirmação externa.

`prize` varia de 0 a 250.000.000, com nove zeros e valores fracionários. A fonte não declara moeda nem se o campo é jackpot anunciado, montante pago, pool total ou estimativa. Por isso:

- o texto numérico é preservado como `reported_prize`;
- o status monetário permanece `unknown`;
- valor normalizado e moeda ficam ausentes;
- zero não é convertido em ausência nem explicado artificialmente.

## Fixtures e falhas cobertas

- 2004-02-13: primeiro registro, `id=1`, vencedor verdadeiro.
- 2024-11-19: primeiro registro após a grande descontinuidade, `id=3943`.
- 2025-12-26: último registro do snapshot.

Mutações cobrem raiz/item JSON incorretos, campos extras, datas, IDs, booleano, dinheiro não finito/negativo, tipos de coleção, inteiros, ordem, duplicidade, cardinalidade e limites.

## Dados ausentes e pesquisa necessária

Não estão disponíveis horário confirmado, timezone real, país/jurisdição do prêmio, faixas, ganhadores por país, arrecadação, local do sorteio ou regras vigentes.

Antes da auditoria integral, pesquisar:

- versões históricas dos limites das estrelas e datas exatas;
- semântica oficial de `id`, `draw_id`, `has_winner` e `prize` na API de terceiros;
- moeda e abrangência geográfica do prêmio;
- fonte oficial preferencial e arquivos por país;
- horário/fuso, calendário histórico, Millionaire Maker e outros códigos nacionais;
- correções, cobertura e termos de uso.

## Reprodutibilidade

```powershell
python -m unittest discover -s tests -p 'test_euro_millions_ingestion.py' -v
```

O arquivo é lido somente em memória. Não há rede, banco, coleta ou escrita de candidatos.

## Próxima tarefa

SPEC-0015 — Pesquisar regras históricas oficiais, semântica dos campos e fonte preferencial do EuroMillions antes da auditoria integral.
