# Powerball — contrato de extração do HTML

## Escopo

Esta etapa valida a leitura e a normalização de amostras reais dos três formatos presentes em `data/raw/powerball/powerball_resultados.html`. Não certifica todas as regras históricas e não publica um histórico canônico.

Fonte conhecida: USA Mega, página secundária. O arquivo local não contém resposta HTTP, instante original da coleta ou versão do coletor. Hash antes/depois: `12b1197b080bdf06cd8c944a66167732bb73850e8591b163faf985a3744b4238`.

## Estrutura observada

| Formato | Linhas | Representação |
| --- | ---: | --- |
| Resultado simples | 1.136 | 5 números + Powerball |
| Com Power Play | 1.926 | resultado principal + atributo multiplicador |
| Com Power Play e Double Play | 680 | resultado principal + atributo + série adicional |
| Total | 3.742 | 1992-04-22 a 2025-12-24 |

Todas as 3.742 URLs de sorteio são distintas. O Power Play aparece de 2001-03-07 a 2025-12-24 no snapshot. Double Play aparece de 2021-08-23 a 2025-12-24. Essas são fronteiras observadas na fonte secundária, não datas oficiais de regras.

Distribuição do texto de Power Play: 2x em 1.077 linhas, 3x em 717, 5x em 407, 4x em 353, 1x em 30 e 10x em 22. Ausente em 1.136. O parser exige exatamente um texto `Nx`; não trata multiplicador como bola.

## Contrato semântico

- O primeiro `ul` de `section.results` contém o resultado principal.
- `li` sem classe contém os cinco números principais.
- `li.bonus` contém a Powerball.
- `li.multiplier` contém Power Play.
- `ul.extradraw` contém Double Play: cinco `li.dp` e uma `li.bonus`.
- Outro item com classe, ou um segundo bloco comum de resultados, é desconhecido e causa diagnóstico. Elementos não são achatados em uma lista única.
- A URL `/powerball/drawing/YYYY/M/D` fornece referência externa e identidade provisória pela data. O texto visível é preservado e conciliado; divergência é erro.

Double Play é uma série `double_play` opcional com seus próprios componentes `main` e `powerball`. Power Play é o atributo inteiro `power_play` da série principal. O normalizador preserva a ordem recebida e exige ordem crescente nos cinco números conforme o snapshot.

## Dinheiro

Jackpot anunciado é armazenado como `advertised_jackpot`, Decimal e USD, mantendo o texto. `Million` multiplica por 1.000.000 e `Billion` por 1.000.000.000. Há 3.719 textos Million e 23 Billion. Ausência é `unknown`; escala desconhecida é erro.

Esse campo representa jackpot anunciado, não arrecadação, prêmio efetivamente pago ou valor por ganhador. O arquivo não contém faixas, quantidade de ganhadores ou moeda em código ISO; USD é inferido do símbolo e contexto da modalidade e deve ser confirmado com a fonte oficial.

## Fixtures e evidências

- 2025-12-24: Power Play 2x, Double Play e jackpot `$1.8168 Billion`.
- 2021-08-21: Power Play 2x, sem Double Play.
- 1992-04-22: formato simples e jackpot `$6 Million`.

As fixtures são cópias estruturadas dessas linhas e um teste as reconcilia com as posições atuais do raw. Casos inválidos são mutações somente em memória.

## Limites e pesquisa necessária

O envelope observado é 1–69 para números e 1–45 para Powerball. Ele permite testar as três amostras, mas não deve ser usado como regra histórica oficial. Há 860 resultados com Powerball acima do limite atual aparente 26; classificá-los como inválidos sem versionamento produziria falsos positivos.

Antes da auditoria integral, pesquisar em fontes oficiais:

- versões de intervalos, datas de vigência e mudanças de calendário;
- lançamento e regras de Power Play e Double Play;
- fonte oficial estruturada e estável, inclusive identificador oficial se existir;
- semântica do jackpot e moeda;
- política de correções históricas.

Não disponíveis: número oficial estruturado no HTML, horário, ganhadores, faixas, arrecadação e local do sorteio.

## Reprodutibilidade

```powershell
python -m unittest discover -s tests -p 'test_powerball_ingestion.py' -v
```

O leitor usa somente a biblioteca padrão. Não há download, navegador, escrita de candidatos ou alteração do HTML.

## Próxima tarefa

SPEC-0009 — Pesquisa e especificação das regras históricas oficiais e da fonte preferencial da Powerball, antes de auditar todas as linhas.
