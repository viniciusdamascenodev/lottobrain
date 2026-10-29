# Dossiê oficial das loterias

## Escopo e validade

Pesquisa verificada em **20/10/2026**. Este documento complementa os históricos locais; não substitui regulamentos nem certifica concursos passados linha a linha. Preços, horários, calendários, jackpots e percentuais são fatos versionáveis e devem ser reconfirmados antes de uma coleta produtiva.

## Resumo comparativo vigente

| Loteria | Combinação principal | Especial | Dias/horário publicados | Aposta simples | Moeda | Chance do prêmio principal |
|---|---|---|---|---:|---|---:|
| Mega-Sena | 6 de 60 | — | ter./qui. 21h; dom. 11h | R$ 6,00 | BRL | 1 em 50.063.860 |
| Lotofácil | 15 de 25 | — | seg.–sex. 21h; dom. 11h | R$ 3,50 | BRL | 1 em 3.268.760 |
| +Milionária | 6 de 50 | 2 trevos de 6 | qua. 21h; dom. 11h | R$ 6,00 | BRL | 1 em 238.360.500 |
| Powerball | 5 de 69 | 1 Powerball de 26 | seg./qua./sáb. 22h59 ET | US$ 2 | USD | 1 em 292.201.338 |
| Mega Millions | 5 de 70 | 1 Mega Ball de 24 | ter./sex. 23h ET | US$ 5 | USD | 1 em 290.472.336 |
| EuroMillions | 5 de 50 | 2 estrelas de 12 | ter./sex.; aprox. 21h05 na França | € 2,50 na França | EUR | 1 em 139.838.160 |

Os horários da CAIXA são horários locais publicados pelo operador; Powerball e Mega Millions publicam `ET`; a FDJ publica hora da França metropolitana. O futuro agendador deve guardar timezone IANA e não apenas uma hora textual.

## Mega-Sena

### Confirmado oficialmente

- Aposta de 6 a 20 números dentre 60; a aposta mínima de seis números custa R$ 6,00.
- Três sorteios semanais: terça e quinta a partir das 21h e domingo a partir das 11h.
- Premia 6, 5 e 4 acertos. Do prêmio bruto, declarado como 43,79% da arrecadação, a página vigente destina 40% à Sena, 13% à Quina, 15% à Quadra, 22% aos concursos de final 0 ou 5 e 10% à Mega da Virada.
- A aposta simples tem chance de 1 em 50.063.860 para a Sena.
- Prêmios prescrevem após 90 dias.
- Sorteios da CAIXA ocorrem normalmente no Espaço da Sorte, em São Paulo, com locais excepcionais previstos e dois representantes do público na validação.

### Consequências para o sistema

- `Mega da Virada` e acumulações de final 0/5 são tipos especiais de concurso/reserva, não novas bolas.
- O resultado precisa separar valor estimado seguinte, valor acumulado e fundo especial.
- Preço, calendário e rateio devem possuir `valid_from`/`valid_to`.

Fontes: [Mega-Sena — CAIXA](https://loterias.caixa.gov.br/Paginas/mega-sena.aspx) e [Regras dos sorteios — CAIXA](https://loterias.caixa.gov.br/Paginas/regras-sorteios.aspx).

## Lotofácil

### Confirmado oficialmente

- O jogador marca de 15 a 20 números dentre 25; a aposta simples custa R$ 3,50.
- Calendário vigente: segunda a sexta a partir das 21h e domingo a partir das 11h.
- Premia 11, 12, 13, 14 ou 15 acertos. As três primeiras faixas têm pagamentos fixos publicados de R$ 7, R$ 14 e R$ 35.
- Após os pagamentos fixos, a página destina 62% do saldo à faixa de 15, 13% à de 14, 10% a concursos de final 0 e 15% à Lotofácil da Independência.
- A chance da aposta simples é 1 em 3.268.760 para 15 acertos e 1 em 11 para 11 acertos.

### Consequências para o sistema

- A estrutura de prêmio é híbrida: faixas fixas e faixas rateadas convivem no mesmo concurso.
- Concurso de final 0 e Lotofácil da Independência requerem classificação especial e reservas próprias.
- Uma tela de “probabilidade” deve distinguir aposta simples de apostas combinadas de 16 a 20 números.

Fontes: [Lotofácil — CAIXA](https://loterias.caixa.gov.br/Paginas/LOTOFACIL.aspx) e [Regras dos sorteios — CAIXA](https://loterias.caixa.gov.br/Paginas/regras-sorteios.aspx).

## +Milionária

### Confirmado oficialmente

- Aposta simples: seis números de 1 a 50 e dois trevos de 1 a 6, por R$ 6,00.
- Sorteios quarta a partir das 21h e domingo a partir das 11h.
- Dez faixas de premiação; prêmio principal mínimo anunciado de R$ 10 milhões.
- Chance de 6+2 na aposta simples: 1 em 238.360.500.
- O prêmio bruto corresponde a 43,79% da arrecadação e 5% dessa parcela compõe a Reserva Garantidora de Prêmios (RGP).
- Há valores fixos vigentes para 3+2, 3+1, 2+2 e 2+1; o resultado oficial também publica o saldo da RGP.

### Consequências para o sistema

- Números e trevos são dois componentes independentes, ambos sem repetição interna.
- `acumulou`, `valor acumulado` e `saldo RGP` são três conceitos, não uma única coluna.
- A RGP é um mecanismo de garantia e deve ser modelada separadamente das faixas ganhadoras.

Fonte: [+Milionária — CAIXA](https://loterias.caixa.gov.br/paginas/mais-Milionaria.aspx).

## Powerball

### Confirmado oficialmente

- Cinco bolas brancas de 1 a 69 e uma Powerball de 1 a 26; US$ 2 por aposta. Idaho e Montana vendem a combinação com Power Play por preço mínimo de US$ 3.
- Sorteios às segundas, quartas e sábados, 22h59 no horário do leste dos EUA, no estúdio da Florida Lottery em Tallahassee.
- Nove formas de ganhar. Chance do jackpot: 1 em 292.201.338; chance de qualquer prêmio: aproximadamente 1 em 24,87.
- O jackpot pode ser pago em parcela única ou anuidade de 30 pagamentos graduais ao longo de 29 anos.
- Power Play é opcional e multiplica prêmios não jackpot; a faixa de cinco bolas sem Powerball passa a US$ 2 milhões. Na Califórnia, pagamentos são pari-mutuel.
- Double Play é uma extração adicional opcional, posterior ao sorteio principal, com prêmio máximo de US$ 10 milhões em jurisdições participantes.
- O jogo é oferecido pelas 48 loterias dos EUA (45 estados, DC, Porto Rico e Ilhas Virgens Americanas). A fonte oficial informa expansão da venda no Reino Unido em 21/07/2026, compartilhando apenas o jackpot; as demais premiações permanecem locais.

### Consequências para o sistema

- Jackpot comum e prêmios locais precisam de escopos geográficos diferentes.
- Power Play pertence à aposta; Double Play produz outro resultado. Nenhum deles deve ser anexado como números principais.
- Exceções por estado, opção anuidade/caixa, impostos e limite de venda exigem jurisdição.
- A página institucional ainda contém textos prospectivos sobre uma data já passada; o coletor deve registrar `observed_at` e monitorar inconsistências editoriais.

Fontes: [Powerball oficial](https://www.powerball.com/), [tabela de prêmios e probabilidades](https://www.powerball.com/powerball-prize-chart), [central de mídia](https://www.powerball.com/media-center) e [FAQ da expansão ao Reino Unido](https://www.powerball.com/faqs).

## Mega Millions

### Confirmado oficialmente

- Desde o sorteio de 08/04/2025, a aposta custa US$ 5 e inclui multiplicador de 2x, 3x, 4x, 5x ou 10x para prêmios não jackpot.
- Matriz vigente: cinco bolas diferentes de 1 a 70 e uma Mega Ball de 1 a 24.
- Nove formas de ganhar; chance do jackpot 1 em 290.472.336 e chance geral 1 em 23.
- Sorteios terça e sexta às 23h ET, em Atlanta, Geórgia.
- Disponível em 45 estados, Washington DC e Ilhas Virgens Americanas.
- O jackpot oferece opção em dinheiro ou anuidade: uma parcela imediata e 29 anuais, cada uma 5% maior que a anterior.
- A Califórnia aplica pagamentos pari-mutuel. O jackpot inicial vigente foi elevado a US$ 50 milhões na reforma de 2025.

### Mudança estrutural de 2025

A versão anterior custava US$ 2, usava 25 Mega Balls e oferecia Megaplier opcional. A versão atual usa 24 Mega Balls e multiplicador embutido. Essa fronteira já afeta os dados históricos locais e prova que preço, matriz e multiplicador devem ser versionados em conjunto.

Fontes: [Como jogar — Mega Millions](https://www.megamillions.com/How-To-Play.aspx), [FAQ oficial](https://www.megamillions.com/faqs) e [matriz introduzida em 2025](https://www.megamillions.com/Media-Center/MegaMillions_New_Prize_Matrix.aspx).

## EuroMillions

### Confirmado oficialmente

- Matriz vigente comum: cinco números de 1 a 50 e duas Lucky Stars de 1 a 12.
- Sorteios às terças e sextas. A FDJ informa, para a França, encerramento de apostas às 20h15, My Million por volta de 20h20, EuroMillions por volta de 21h05 e publicação na página por volta de 21h45.
- Na França, uma grade simples custa € 2,50 e inclui um código My Million; o jackpot mínimo publicado é € 17 milhões.
- Chance do jackpot: 1 em 139.838.160; chance de qualquer prêmio: aproximadamente 1 em 13.
- Os valores das 13 faixas são rateados e dependem da reserva e do número de ganhadores.
- A FDJ disponibiliza arquivos oficiais em ZIP desde fevereiro de 2004, separados em períodos que coincidem com mudanças de matriz.
- EuroMillions é uma loteria multinacional. Complementos nacionais diferem: My Million na França/Monaco e Ireland Only Raffle na Irlanda, por exemplo.

### Consequências para o sistema

- O resultado de números e estrelas é pan-europeu, mas preço, raffle, ganhadores locais, prazo de resgate e operador são territoriais.
- Não existe um “preço EuroMillions” universal; € 2,50 é o produto francês consultado.
- My Million e Ireland Only Raffle são extensões nacionais, não números especiais do EuroMillions.
- A fonte histórica oficial da FDJ é candidata forte para reconciliação, porém seus arquivos devem ser avaliados por período e jurisdição antes de substituir o snapshot atual.

Fontes: [Como jogar — FDJ](https://www.fdj.fr/jeux-de-tirage/euromillions-my-million/comment-jouer), [histórico oficial — FDJ](https://www.fdj.fr/jeux-de-tirage/euromillions-my-million/historique) e [EuroMillions — Irish National Lottery](https://www.lottery.ie/game-information/euromillions).

## Dados novos que passam a integrar a base de conhecimento

| Informação | Situação após a pesquisa | Uso futuro |
|---|---|---|
| matriz vigente e versões conhecidas | confirmada para as seis | validação por data e cálculo de probabilidades |
| dias e horários atuais | confirmados; timezone ainda deve ser explicitado nos dados | agendamento e detecção de atraso |
| preço simples e moeda | confirmado, com exceções territoriais | exibição versionada, nunca constante global |
| chance do prêmio principal | confirmada | conteúdo explicativo e teste de regra |
| modelo de premiação | confirmado em alto nível | catálogo de faixas e análises financeiras |
| jogos/extensões adicionais | identificados | entidades/capacidades separadas |
| local operacional | confirmado em alto nível | proveniência; não assumir local para todo concurso histórico |
| fonte histórica oficial | disponível para CAIXA e FDJ; parcial/distribuída nos EUA | desenho da coleta e reconciliação |
| jurisdições e exceções | confirmadas em parte | escopo territorial e regras locais |

## Questões que ainda exigem pesquisa técnica

1. Qual é o contrato, limite de uso e política de estabilidade dos endpoints JSON usados internamente pelas páginas da CAIXA?
2. Qual fonte oficial fornece histórico completo e reutilizável de Powerball e Mega Millions sem depender de páginas estaduais ou scraping frágil?
3. Como obter, de forma oficial e consistente, ganhadores e prêmios por estado/jurisdição nos jogos dos EUA?
4. Qual operador europeu será a autoridade primária para o resultado comum do EuroMillions e quais operadores serão fontes complementares nacionais?
5. Quais calendários de feriado e concursos extraordinários alteram os agendamentos normais?
6. Quais termos de uso, robots, licenças e limites de requisição permitem coleta automatizada em cada fonte?
7. Como representar correções posteriores do operador, adiamentos e concursos cancelados?
8. Quais preços e calendários históricos devem ser recuperados para análises temporais, além das matrizes já conhecidas?

## Objetivo de previsão e comunicação responsável

Prever da melhor forma possível é um objetivo explícito do LottoBrain. Serão pesquisados métodos matemáticos, estatísticos, de aprendizado de máquina e IA, inclusive combinações entre eles. Como as fontes oficiais tratam essas modalidades como jogos de acaso, toda melhoria alegada deverá ser demonstrada fora da amostra, contra baselines aleatórios e heurísticos, sem vazamento temporal. A ausência de garantia não reduz o objetivo de previsão: exige medição rigorosa. A interface deverá comunicar probabilidade, incerteza, limitações e jogo responsável.
