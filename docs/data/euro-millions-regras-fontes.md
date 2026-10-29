# EuroMillions — dossiê de regras, campos e fontes

## Resultado da pesquisa

Pesquisa realizada em 2026-10-14. Datas abaixo são datas de sorteio e limites inclusivos.

| Versão | Período | Regra | Evidência | Confiança |
| --- | --- | --- | --- | --- |
| `em_2004_50x9` | 2004-02-13–2011-05-06 | 5/50 + 2 estrelas de 1–9 | [Arquivo oficial FDJ](https://www.fdj.fr/jeux-de-tirage/euromillions-my-million/historique) separa fevereiro/2004–maio/2011; snapshot tem 378 linhas e máximo 9 | Alta |
| `em_2011_50x11` | 2011-05-10–2016-09-23 | 5/50 + 2 estrelas de 1–11 | FDJ separa maio/2011–fevereiro/2014 e fevereiro/2014–setembro/2016; snapshot tem 562 linhas e máximo 11 | Alta |
| `em_2016_50x12` | desde 2016-09-27 | 5/50 + 2 estrelas de 1–12 | FDJ inicia novo arquivo em setembro/2016; [Irish National Lottery](https://www.lottery.ie/game-information/euromillions) e seu [regulamento](https://cdn1.lottery.ie/uploads/Issue_5_EUROMILLIONS_RULES_OCT_2024_29_10_2a527d4c18.pdf) confirmam a matriz atual; snapshot tem 966 linhas e máximo 12 | Alta |

Nas quatro linhas de fronteira, o snapshot registra:

| Data | Versão | Estrelas |
| --- | --- | --- |
| 2011-05-06 | `em_2004_50x9` | 4, 9 |
| 2011-05-10 | `em_2011_50x11` | 5, 7 |
| 2016-09-23 | `em_2011_50x11` | 3, 9 |
| 2016-09-27 | `em_2016_50x12` | 2, 12 |

Os quatro resultados de fronteira não provam sozinhos todo o intervalo; eles conciliam a segmentação da fonte oficial com o arquivo local. Todas as 1.906 linhas respeitam sua versão e os números principais permanecem em 1–50.

## Proveniência real do JSON legado

O [repositório público da API Pedro Mealha](https://github.com/pedro-mealha/euromillions-api) declara que raspa `euro-millions.com`, um site não oficial. Logo, o encadeamento do snapshot é:

`euro-millions.com → parser Pedro Mealha → banco PostgreSQL da API → /draws → arquivo local`

Isso é proveniência útil, mas não uma cadeia oficial. O README também informa coleta às terças e sextas entre 21h e 23h; esse agendamento não certifica horário de sorteio.

### Identificadores

- [`id`](https://github.com/pedro-mealha/euromillions-api/blob/550f0635a81a8a8e96268fdfc62c394327549f8a/db/migrations/0000.initial-schema.sql) é `SERIAL`, chave primária interna. Não é concurso.
- [`draw_id`](https://github.com/pedro-mealha/euromillions-api/blob/550f0635a81a8a8e96268fdfc62c394327549f8a/scripts/setup.py) é criado concatenando `draw_id_index` anual com o ano. Exemplo: o 26º sorteio de 2021 vira `262021`.
- A rotina incremental reinicia o ordinal em 1 quando muda o ano. O snapshot tem zero divergências dessa fórmula.
- A identidade canônica deve continuar sendo loteria + data civil enquanto nenhuma fonte oficial fornecer um identificador estável comum aos operadores.

### Vencedor e valor

O [parser de detalhes](https://github.com/pedro-mealha/euromillions-api/blob/550f0635a81a8a8e96268fdfc62c394327549f8a/api/external.py) procura primeiro o quadro `PrizePT` e usa `PrizeES` como fallback. Em cada faixa, lê “Prize Per Winner”, remove o símbolo `€` e lê “Total Winners”.

- `has_winner=true` significa que a faixa 5+2 tem mais de zero ganhadores.
- `prize` é o valor por ganhador da faixa 5+2, em EUR, segundo o quadro PT/ES raspado.
- `prize` não significa arrecadação, soma distribuída, próximo prêmio nem necessariamente o jackpot integral anunciado: com vários ganhadores, é a parcela individual.
- O endpoint antigo não conserva qual dos dois quadros nacionais foi usado em cada linha; a jurisdição exata fica `PT_or_ES` até reconciliação.
- Nove zeros no fim de 2025 são ausência/falha do dado financeiro, não jackpot de EUR 0: nenhum coincide com `has_winner=true`.

A [especificação OpenAPI da API](https://github.com/pedro-mealha/euromillions-api/blob/550f0635a81a8a8e96268fdfc62c394327549f8a/docs/api.yaml) marca `/draws` como legado e o schema novo expõe `prizes` por faixa. Isso reforça que o campo agregado deve ser mantido apenas por compatibilidade e proveniência.

## Fatos comuns versus fatos nacionais

| Categoria | Escopo correto |
| --- | --- |
| Data, cinco números e duas estrelas | Sorteio EuroMillions comum aos países participantes |
| Matriz numérica e categorias 5+2 etc. | Regra comum, com vigência |
| Jackpot do sorteio | Comum em EUR na organização do jogo, mas exibição/conversão pode variar por operador |
| Prêmio por ganhador e contagem de ganhadores | Exige definição de total pan-europeu versus subconjunto nacional |
| My Million | França/Monaco; extensão nacional |
| Ireland Only Raffle e EuroMillions Plus | Irlanda; extensões nacionais |
| UK Millionaire Maker e valores em GBP | Reino Unido; extensão/conversão nacional |

A [página oficial irlandesa de resultados](https://www.lottery.ie/results/euromillions/history) demonstra a diferença ao publicar jackpot em EUR, ganhadores totais, ganhadores irlandeses, prêmios por faixa e códigos locais na mesma página. O modelo futuro não deve achatar esses níveis em um único `prize` ou `winner_count`.

## Avaliação das fontes

| Fonte | Estrutura/cobertura | Autoridade | Uso decidido |
| --- | --- | --- | --- |
| [Arquivos históricos FDJ](https://www.fdj.fr/jeux-de-tirage/euromillions-my-million/historique) | ZIPs oficiais desde fevereiro de 2004, particionados por períodos | Operador oficial francês | Preferência para prova técnica e futura coleta histórica comum |
| [Histórico Irish National Lottery](https://www.lottery.ie/results/euromillions/history) | Página com combinação, jackpot, faixas, totais e dados irlandeses | Operador oficial irlandês | Verificação cruzada e possível fonte financeira com escopo explícito |
| Regulamentos de operadores | Regras correntes e categorias | Primária | Certificação de regra; não feed histórico |
| API Pedro Mealha | JSON conveniente desde 2004; endpoint legado e base raspada | Terceira parte | Baseline local, rastreabilidade e fallback temporário |
| euro-millions.com | HTML histórico usado pela API | Não oficial | Nunca autoridade; comparação apenas |

## Prova técnica exigida antes de coleta

1. Baixar amostras de cada ZIP FDJ e documentar CSV, delimitador, encoding, nomes de campo e mudanças de schema.
2. Confirmar que a cobertura é contínua desde 2004 e que datas de fronteira aparecem uma única vez.
3. Identificar campos compartilhados e campos franceses, sobretudo My Million.
4. Registrar termos de uso, licença, frequência de atualização e URL estável.
5. Verificar como a FDJ publica correções e se arquivos passados são substituídos.
6. Reconciliar amostras com outro operador oficial e definir política para divergências.
7. Determinar se jackpot, faixas e ganhadores são pan-europeus ou nacionais em cada coluna.
8. Manter `source`, jurisdição, moeda, instante de coleta e hash em todo registro financeiro.

## Impacto na próxima auditoria

O normalizador deverá selecionar uma das três regras pela data e rejeitar datas nas lacunas. `id` e `draw_id` permanecem referências externas da fonte, sem ocupar `draw_identifier` oficial. `has_winner` pode ser mapeado para uma indicação de ganhador do jackpot, acompanhada de proveniência. `prize` pode ser preservado como prêmio individual 5+2 em EUR com jurisdição indeterminada PT/ES, mas zeros devem gerar diagnóstico de ausência, não montante válido.

Horário continua desconhecido: `00:00:00 GMT` não deve alimentar agenda. Extensões nacionais ficam fora do resultado comum até contrato próprio.
