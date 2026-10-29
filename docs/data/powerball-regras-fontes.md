# Powerball — dossiê de regras históricas e fontes

## Resultado da pesquisa

Pesquisa realizada em 2026-10-14. Datas abaixo são datas de sorteio e limites são inclusivos.

| Versão | Período | Regra | Evidência principal | Confiança |
| --- | --- | --- | --- | --- |
| `pb_1992_45x45` | 1992-04-22–1997-11-01 | 5/45 + PB 1/45 | [Powerball: lançamento em 22/04/1992](https://www.powerball.com/media-center?os=vbf); tabela histórica da [USA Mega](https://www.usamega.com/powerball/statistics/a) e snapshot local para limites/fronteira | Média |
| `pb_1997_49x42` | 1997-11-05–2002-10-05 | 5/49 + PB 1/42 | [Kansas Lottery: versão aprimorada em 02/11/1997](https://www.kslottery.gov/history); relatório oficial de Rhode Island descreve 5/49 + 1/42; USA Mega para fronteiras de sorteio | Alta |
| `pb_2002_53x42` | 2002-10-09–2005-08-27 | 5/53 + PB 1/42 | [regulamento oficial do Kansas de 2002](https://sos.ks.gov/publications/register/2002/Vol_21_No_44_October_31_2002_p_1839-1876.pdf); USA Mega para fronteiras | Alta |
| `pb_2005_55x42` | 2005-08-31–2009-01-03 | 5/55 + PB 1/42 | [Delaware: mudança efetiva em 28/08/2005](https://delottery.com/Media-Center/Press-Releases/2005/08/25); [relatório oficial de Nebraska](https://nelottery.com/media/annualreport06.pdf); USA Mega para primeiro/último sorteio | Alta |
| `pb_2009_59x39` | 2009-01-07–2012-01-14 | 5/59 + PB 1/39 | [Delaware: primeiro sorteio em 07/01/2009 e nova matriz](https://delottery.com/Media-Center/Press-Releases/2009/01/06) | Alta |
| `pb_2012_59x35` | 2012-01-18–2015-10-03 | 5/59 + PB 1/35 | [Delaware: último sorteio antigo em 14/01/2012 e PB reduzida para 35](https://delottery.com/Media-Center/Press-Releases/2011/10/19); [Texas: primeiro sorteio do novo desenho em 18/01/2012](https://www.texaslottery.com/export/sites/lottery/Games/Powerball/Winning_Numbers/index.html_169563092.html) | Alta |
| `pb_2015_69x26` | desde 2015-10-07 | 5/69 + PB 1/26 | [Powerball: matriz atual estreou em 07/10/2015](https://www.powerball.com/media-center?os=vbf); [Delaware: 69/26](https://delottery.com/Media-Center/Press-Releases/2015/09/29) | Alta |

“Evidência principal” não significa que uma única página prove todos os limites. Quando o anúncio oficial usa data de vigência ou início de vendas, a data exata do primeiro/último sorteio foi reconciliada com a tabela secundária e com o snapshot. A primeira versão é a única que ainda carece de texto primário acessível explicitando 45/45; por isso não recebe confiança alta.

## Power Play, Double Play e calendário

| Dimensão | Regra pesquisada | Consequência para os dados |
| --- | --- | --- |
| Power Play | Primeiro sorteio em 2001-03-07, segundo o [histórico oficial do Kansas](https://www.kslottery.gov/history). | Antes dessa data, ausência é “não aplicável”. |
| Power Play de preço fixo | O resultado oficial de [2012-01-14](https://www.powerball.com/draw-result?date=2012-01-14&gc=powerball) ainda mostra 5x. De 2012-01-18 a 2014-01-18, as faixas Power Play eram fixas e não havia multiplicador sorteado; o site oficial mostra as faixas sem `Nx`. | Ausência de `power_play` nesse intervalo é válida, não `missing`. A regra de prêmio não deve ser reconstruída apenas pelo campo multiplicador. |
| Retorno do multiplicador | O resultado oficial de [2014-01-22](https://www.powerball.com/draw-result?date=2014-01-22&gc=powerball) mostra 3x. | Desde essa data, o multiplicador volta a ser atributo do sorteio. |
| Double Play | Primeiro sorteio e nova segunda-feira em 2021-08-23, conforme [comunicado oficial](https://www.powerball.com/powerballr-launch-new-monday-drawing-double-playr-add-feature). | É outra série, com seus próprios números; não deve ser anexada aos cinco números principais. |
| Calendário atual | Segunda, quarta e sábado, 22h59 no horário do leste dos EUA, conforme [Media Center](https://www.powerball.com/media-center?os=vbf). | Persistir fuso e instante separadamente quando a fonte os fornecer; o snapshot local só garante a data. |

O intervalo de Power Play fixo acima é uma conclusão sustentada pela mudança visível nos resultados oficiais nas fronteiras e pelo formato do [CSV oficial do Texas](https://www.texaslottery.com/export/sites/lottery/Games/Powerball/Winning_Numbers/download.html), que separa 2012-01-18–2014-01-18 sem coluna de multiplicador. A especificação de valores de cada faixa histórica ainda deve ser obtida das regras vigentes antes de análises financeiras.

## Avaliação das fontes

| Fonte | Estrutura | Cobertura conhecida | Autoridade | Uso decidido |
| --- | --- | --- | --- | --- |
| Resultado em Powerball.com | Página por data, números, multiplicador quando aplicável, jackpot, cash value, ganhadores/faixas e jurisdições | Resultados antigos localizáveis; cobertura integral ainda não testada | A página afirma que o resultado oficial do sorteio prevalece | Verificação autoritativa e resolução de divergências |
| API MUSL v3 | JSON com data/identificadores, `numbers`, `itemCode`, `ruleCode`, valor e ordem; endpoints de números, relatório, ganhadores e jogos | Não testada; documentação permite consulta por data/game code | Primeira parte, mas [termos](https://api.musl.com/terms) negam caráter oficial do feed | Candidata preferencial para coleta automatizada, após prova técnica e jurídica |
| CSV Texas Lottery | CSV por períodos; números e Power Play quando disponível | Desde 2010, não desde 1992 | Loteria estadual oficial | Reconciliação estruturada parcial |
| USA Mega | HTML/tabela secundária; é a origem provável do raw atual | 1992 em diante no snapshot | Secundária | Fallback e comparação; nunca desempate contra fonte oficial |

### Por que a API MUSL é a candidata preferencial

A [Winning Numbers API](https://api.musl.com/numbers-api) documenta componentes por `itemCode`/`ruleCode`, ordem do sorteio e consultas por data, `DrawId` ou identificador externo. A [consulta por data](https://api.musl.com/numbers-api-by-date-and-game-code) retorna o sorteio anterior quando a data não é dia de desenho — comportamento que o coletor precisa detectar, não aceitar como correspondência exata. O [Games API](https://api.musl.com/games-api) descreve intervalos das regras. Isso é mais estável que interpretar apresentação HTML.

Contudo, a API exige chave, pode impor limites, mudar ou revogar acesso e declara que seu feed não é a informação oficial. Portanto, “preferencial” significa transporte automatizado; a autoridade continua sendo o registro oficial do sorteio. O pipeline deverá registrar proveniência e oferecer verificação amostral/por divergência.

## Prova técnica exigida antes do coletor

Uma SPEC futura de integração deverá responder, sem carga em massa:

1. A chave pode ser usada no ambiente de desenvolvimento, CI e produção sem exposição?
2. Números e relatórios cobrem cada uma das sete versões desde 1992?
3. `DrawId` e `ExternalDrawId` são estáveis e existem no histórico inteiro?
4. Como paginar ou percorrer datas, e quais são os limites e códigos de erro?
5. O retorno de “sorteio anterior” é distinguível da data solicitada?
6. Correções posteriores têm versão, timestamp, ETag ou outra forma de detecção?
7. Os termos permitem armazenar e exibir histórico, faixas e jackpots no LottoBrain?
8. Há diferenças por jurisdição, sobretudo prêmios, impostos ou multiplicadores?
9. Qual política de fallback vale quando API e página oficial divergem?

## Campos e semântica pendentes

- **Identificador oficial:** a API oferece IDs, mas estabilidade e cobertura histórica não foram verificadas. Não converter data em número de concurso.
- **Jackpot:** manter `advertised_jackpot` e USD; `cash_value` é outro campo. Nenhum deles representa arrecadação ou pagamento final.
- **Faixas e ganhadores:** o site exibe totais e, em alguns casos, detalhes por jurisdição. A semântica nacional versus estadual precisa ser definida.
- **Local do sorteio e horário histórico:** não pesquisados em detalhe nesta SPEC.
- **Mudanças do Power Play:** valores fixos, conjunto de multiplicadores e elegibilidade do 10x precisam de versões próprias antes de análises financeiras.
- **Double Play:** jurisdições participantes e regras de prêmio podem variar; a presença do sorteio não implica disponibilidade nacional.
- **Primeira matriz:** localizar regra MUSL/estadual primária que explicite 5/45 + 1/45 elevaria a confiança de média para alta.

## Impacto na auditoria local

A próxima auditoria deve selecionar regra pela data, validar cinco números principais distintos e crescentes, validar a Powerball em componente separado e aplicar ao Double Play a regra vigente de 2021. Deve classificar Power Play como `not_applicable`, `fixed_prize_no_multiplier`, `observed` ou `missing` conforme a data e estrutura — nunca interpretar ausência genericamente.

O snapshot local continua sendo evidência secundária imutável. Uma divergência futura deve gerar diagnóstico com ambas as proveniências, não reescrever o raw.
