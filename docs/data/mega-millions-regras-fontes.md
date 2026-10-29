# Mega Millions — dossiê de regras históricas e fontes

## Resultado da pesquisa

Pesquisa realizada em 2026-10-14. Períodos usam datas de sorteio e limites inclusivos.

| Versão | Período | Regra | Evidência principal | Confiança |
| --- | --- | --- | --- | --- |
| `mm_1996_50x25` | 1996-09-06–1999-01-12 | 5/50 + MB 1/25 | [Regulamento da Virginia](https://register.dls.virginia.gov/vol13/iss06/v13i06.pdf) registra 5/50 + 1/25; [história oficial](https://www.megamillions.com/about.aspx) confirma origem como Big Game em 1996 | Alta |
| `mm_1999_50x36` | 1999-01-15–2002-05-14 | 5/50 + MB 1/36 | [Tabela histórica da USA Mega](https://www.usamega.com/mega-millions/statistics) e snapshot local | Média |
| `mm_2002_52x52` | 2002-05-17–2005-06-21 | 5/52 + MB 1/52 | Regulamento oficial de Washington de 2005 descreve esta como matriz substituída; [Mega Millions](https://www.megamillions.com/FAQs.aspx) confirma a transição de nome em maio de 2002 | Alta |
| `mm_2005_56x46` | 2005-06-24–2013-10-18 | 5/56 + MB 1/46 | [Georgia Lottery](https://www.galottery.com/en-us/media-center/pressreleaseinput/2005/june/mega-millions-gets-bigger-bigger-jackpots-bigger-possibilities.html); [Texas Lottery](https://www.texaslottery.com/export/sites/lottery/Games/Mega_Millions/Winning_Numbers/index.html_1957071679.html) confirma primeiro sorteio | Alta |
| `mm_2013_75x15` | 2013-10-22–2017-10-27 | 5/75 + MB 1/15 | [Comunicado oficial Mega Millions](https://www.megamillions.com/news/2013/mega-millions-to-become-even-more-mega-beginning.aspx) | Alta |
| `mm_2017_70x25` | 2017-10-31–2025-04-04 | 5/70 + MB 1/25 | [História oficial](https://www.megamillions.com/about.aspx); [Texas Lottery](https://www.texaslottery.com/export/sites/lottery/Games/Mega_Millions/Winning_Numbers/print.html_1126924382.html) confirma primeiro sorteio | Alta |
| `mm_2025_70x24` | desde 2025-04-08 | 5/70 + MB 1/24 | [Mega Millions: novo jogo](https://www.megamillions.com/How-to-Play/The-NEW-Mega-Millions.aspx); [regras oficiais de New Jersey](https://www.njlottery.com/content/dam/portal/pdfs/drawgames/megamillions/Mega_Millions_Rules_effective_4.5.2025.pdf) | Alta |

As datas exatas de primeiro/último desenho foram conciliadas com o snapshot e arquivos oficiais quando disponíveis. A tabela secundária não conta como confirmação independente do raw USA Mega; por isso a versão de 1999 permanece pendente de fonte primária.

## Nome e calendário

O jogo começou como The Big Game. O [site oficial](https://www.megamillions.com/FAQs.aspx) registra que New York e Ohio se juntaram aos participantes em maio de 2002 para criar Mega Millions. Isso é continuidade histórica, não uma loteria independente: manter um único `lottery_slug` e versionar nome/regra.

O [histórico oficial](https://www.megamillions.com/about.aspx) informa que a terça-feira foi adicionada em fevereiro de 1998. O snapshot tem 1.529 sextas e 1.455 terças. Calendários precisam de vigência própria; não são deduzidos dos limites numéricos.

## Megaplier e multiplicador incorporado

| Estado | Vigência do sorteio | Semântica |
| --- | --- | --- |
| `not_applicable` | até 2003-12-02 | Não há Megaplier no resultado. |
| `drawn_optional_megaplier` | 2003-12-05 a 2025-04-04 | Um fator 2x–4x, posteriormente 2x–5x, é sorteado; aplica-se às apostas que compraram a opção, sujeito à jurisdição/regra. |
| `ticket_assigned_multiplier` | desde 2025-04-08 | Cada aposta recebe 2x, 3x, 4x, 5x ou 10x; não existe fator único do sorteio. |

O [site oficial](https://www.megamillions.com/About/Mega-Millions-Trivia.aspx) informa que o Texas introduziu o Megaplier ao entrar no jogo em dezembro de 2003. O [comunicado de 2013](https://www.megamillions.com/news/2013/mega-millions-to-become-even-more-mega-beginning.aspx) registra a inclusão do fator 5x. A [FAQ atual](https://www.megamillions.com/FAQs.aspx) confirma sua aposentadoria e distingue a antiga opção do novo multiplicador incorporado.

A ausência do campo no HTML depois de 2025-04-04 é correta: o resultado não possui um fator único. Valores por multiplicador aparecem nas faixas/ganhadores e o fator individual aparece no bilhete, não na combinação sorteada. O futuro domínio deve evitar chamar ambos simplesmente de `megaplier`.

## Avaliação das fontes

| Fonte | Estrutura/cobertura | Autoridade | Uso decidido |
| --- | --- | --- | --- |
| [Mega Millions Previous Drawings](https://www.megamillions.com/Winning-Numbers/Previous-Drawings.aspx) | HTML paginado e filtrável; cobertura integral ainda precisa ser provada | Site oficial do consórcio | Preferência para coleta e verificação nacional, após prova técnica |
| [Texas Lottery CSV](https://www.texaslottery.com/export/sites/lottery/Games/Mega_Millions/Winning_Numbers/download.html) | CSV desde 2003; inclui Megaplier até 04/04/2025 e muda schema em 08/04/2025 | Loteria estadual oficial | Reconciliação automatizada parcial e detecção de mudança estrutural |
| Páginas estaduais de detalhes | Números e ganhadores/faixas da jurisdição | Oficial para a jurisdição | Auditoria de prêmios locais, não total nacional automaticamente |
| Regulamentos/comunicados | Regras e datas de vigência | Primária | Certificação de versão, não ingestão de sorteios |
| USA Mega | HTML secundário completo no snapshot | Não oficial | Fallback e baseline local |

O CSV do Texas documenta explicitamente dois layouts: com `Megaplier` entre 2003-12-05 e 2025-04-04 e sem essa coluna a partir de 2025-04-08. Essa é evidência forte para não tratar a ausência atual como perda de dados.

## Prova técnica exigida antes de coleta

1. O arquivo central retorna todos os resultados desde 1996 com paginação determinística?
2. Há endpoint JSON ou API oficial por trás da página, e seu uso/armazenamento é permitido?
3. Filtros de data são estáveis e dias sem sorteio não devolvem outro desenho silenciosamente?
4. Existe identificador externo persistente além da data?
5. Como detectar correções e alterações retroativas?
6. Os resultados pós-2025 expõem apenas distribuição de multiplicadores nas faixas, sem fator único?
7. Como conciliar totais nacionais com ganhadores e regras de cada jurisdição?
8. Qual fallback oficial cobre 1996–2003 se o arquivo central não oferecer todos os desenhos?

## Impacto na próxima auditoria

A próxima implementação deverá selecionar uma das sete regras pela data. Megaplier deve ser exigido apenas no período `drawn_optional_megaplier`; antes dele e depois de 2025-04-04 sua ausência é válida por motivos diferentes. A versão pós-2025 não deve fabricar `multiplier` a partir da lista 2x–10x, pois essa lista descreve possibilidades por aposta, não o resultado.

Datas nas lacunas entre matrizes devem produzir `rule_not_found`. Identidade permanece provisória por data até que fonte oficial demonstre ID estável.
