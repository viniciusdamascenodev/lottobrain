# Inventário de fontes e arquivos históricos

## Finalidade

Catalogar o que existe no repositório e o que se sabe sobre sua origem. As URLs são as registradas em `app/core/config.py`; não houve acesso externo nesta tarefa.

## Catálogo

| Loteria | Arquivo bruto | Formato | Fonte registrada | Método atual | Cobertura do arquivo | Risco preliminar |
|---|---|---|---|---|---|---|
| Mega-Sena | `data/raw/mega_sena/mega_sena_resultados.xlsx` | XLSX, 1 planilha | Caixa (`servicebus2.caixa.gov.br/...modalidade=Mega-Sena`) | Download direto | concursos 1–2954 | Endpoint oficial aparente, mas contrato e estabilidade não documentados |
| Lotofácil | `data/raw/lotofacil/lotofacil_resultados.xlsx` | XLSX, 1 planilha | Caixa (`servicebus2.caixa.gov.br/...modalidade=Lotof%C3%A1cil`) | Download direto | concursos 1–3571 | Mesmo risco de contrato; cabeçalhos podem mudar |
| +Milionária | `data/raw/mais_milionaria/mais_milionaria_resultados.xlsx` | XLSX, 1 planilha | Caixa (`servicebus2.caixa.gov.br/...modalidade=+Milion%C3%A1ria`) | Download direto | concursos 1–314 | Mesmo risco; estrutura de muitas faixas exige mapeamento cuidadoso |
| Powerball | `data/raw/powerball/powerball_resultados.html` | HTML, tabela consolidada | USA Mega (`usamega.com/powerball/results`) | Scraping com navegador | 1992-04-22 a 2025-12-24 | Fonte secundária, HTML instável e dependência de navegador |
| Mega Millions | `data/raw/mega_millions/mega_millions_resultados.html` | HTML, tabela consolidada | USA Mega (`usamega.com/mega-millions/results`) | Scraping com navegador | 1996-09-06 a 2025-12-23 | Fonte secundária, HTML instável e dependência de navegador |
| EuroMillions | `data/raw/euro_millions/euro_millions_resultados.json` | JSON, lista | API de terceiros (`euromillions.api.pedromealha.dev/draws`) | Download direto | 2004-02-13 a 2025-12-26 | Contrato, manutenção, moeda e proveniência precisam confirmação |

## Estruturas encontradas

### Mega-Sena

- 20 colunas.
- Concurso, data e seis bolas.
- Ganhadores e rateio para sena, quina e quadra.
- Cidade/UF, acumulado, arrecadação, estimativa, acumulado especial e observação.
- Valores monetários estão armazenados como texto brasileiro com `R$`.

### Lotofácil

- 33 colunas.
- Concurso, data e quinze bolas.
- Ganhadores e rateio de 15 a 11 acertos.
- Cidade/UF, acumulado, arrecadação, estimativa, acumulado especial e observação.
- Valores monetários também são texto localizado.

### +Milionária

- 35 colunas.
- Concurso, data, seis bolas e dois trevos.
- Ganhadores e rateios para diversas combinações de acertos e trevos.
- Cidade/UF, indicador de acumulação, arrecadação, estimativa e observação.
- A coluna de acumulação usa `Sim`, ao contrário dos valores monetários de colunas semelhantes nas outras planilhas.

### Powerball

- 3.742 linhas de sorteio em uma tabela HTML.
- Cada linha contém data, cinco números, Powerball e jackpot anunciado.
- 1.136 linhas têm 6 elementos de bola; 1.926 têm 7; 680 têm 13.
- Os elementos extras representam, conforme o conteúdo observado, multiplicador e, nas linhas mais recentes, um segundo resultado Double Play.
- Não há identificador explícito de concurso, faixas de prêmio, ganhadores, arrecadação, local ou moeda estruturada.

### Mega Millions

- 2.984 linhas de sorteio em uma tabela HTML.
- Cada linha contém data, cinco números, Mega Ball e jackpot anunciado.
- 757 linhas têm 6 elementos de bola e 2.227 têm 7; o elemento adicional corresponde aparentemente ao multiplicador.
- Não há identificador explícito de concurso, faixas, ganhadores, arrecadação, local ou moeda estruturada.

### EuroMillions

- Lista JSON com 1.906 objetos.
- Campos: `date`, `draw_id`, `has_winner`, `id`, `numbers`, `prize` e `stars`.
- Cinco números e duas estrelas estão separados corretamente.
- O arquivo não informa moeda, faixas, número de ganhadores, arrecadação, local ou regra vigente.

## Matriz de disponibilidade

Legenda: **Sim** = presente; **Parcial** = presente sem semântica completa ou apenas em parte do conjunto; **Derivável** = pode ser calculado do dado bruto; **Coletar/Pesquisar** = não presente e depende de fonte.

| Informação | Mega-Sena | Lotofácil | +Milionária | Powerball | Mega Millions | EuroMillions |
|---|---|---|---|---|---|---|
| Identificador do concurso | Sim | Sim | Sim | Coletar/Pesquisar | Coletar/Pesquisar | Parcial (`id`/`draw_id`) |
| Data | Sim | Sim | Sim | Sim | Sim | Sim |
| Horário/timezone | Pesquisar | Pesquisar | Pesquisar | Pesquisar | Pesquisar | Pesquisar |
| Números principais | Sim | Sim | Sim | Sim | Sim | Sim |
| Elementos especiais | Não aplicável | Não aplicável | Sim, trevos | Sim, Powerball | Sim, Mega Ball | Sim, estrelas |
| Multiplicador/sorteio adicional | Não aplicável | Não aplicável | Não aplicável | Parcial | Parcial | Não identificado |
| Regra vigente | Pesquisar | Pesquisar | Pesquisar | Pesquisar | Pesquisar | Pesquisar |
| Prêmio/jackpot principal | Sim | Sim | Sim | Parcial, texto | Parcial, texto | Sim, sem moeda documentada |
| Faixas de premiação | Sim | Sim | Sim | Coletar/Pesquisar | Coletar/Pesquisar | Coletar/Pesquisar |
| Quantidade de ganhadores | Sim | Sim | Sim | Coletar/Pesquisar | Coletar/Pesquisar | Apenas booleano agregado |
| Arrecadação | Sim | Sim | Sim | Coletar/Pesquisar | Coletar/Pesquisar | Coletar/Pesquisar |
| Moeda | Derivável como BRL | Derivável como BRL | Derivável como BRL | Derivável como USD, confirmar | Derivável como USD, confirmar | Pesquisar |
| Cidade/local | Parcial | Parcial | Quase ausente | Coletar/Pesquisar | Coletar/Pesquisar | Coletar/Pesquisar |
| Próximo prêmio estimado | Sim | Sim | Sim | Não separado do jackpot | Não separado do jackpot | Coletar/Pesquisar |
| Frequência histórica | Derivável | Derivável | Derivável | Derivável | Derivável | Derivável |

## Integridade dos arquivos brutos

| Arquivo | Bytes | SHA-256 |
|---|---:|---|
| Mega-Sena XLSX | 221.261 | `0e1936e3ac94a35a89c13ef31d705d3fb363239779ad6224b5e41171a3238686` |
| Lotofácil XLSX | 364.587 | `0ab2c742f0ae6e3b567af2f99744b6d4071c08427c08941a94087e6bde36918e` |
| +Milionária XLSX | 47.985 | `69e9050a3528c7e8d8b944ca904044013e00a66648372183ce4dc5e4531a41fa` |
| Powerball HTML | 1.242.724 | `12b1197b080bdf06cd8c944a66167732bb73850e8591b163faf985a3744b4238` |
| Mega Millions HTML | 918.746 | `c154cb21ae6381efe53f9735b5704d148156ba9737266de54e8badbf1d92c35c` |
| EuroMillions JSON | 304.627 | `e4e7f97102c868569e33d54e34e258671cfca98f6872cf21fc0f86b171e57914` |

