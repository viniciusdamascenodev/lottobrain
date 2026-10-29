# Mega Millions — contrato de extração do HTML

## Escopo

Esta etapa valida leitura e normalização de amostras reais dos formatos presentes em `data/raw/mega_millions/mega_millions_resultados.html`. Não certifica regras históricas e não publica histórico canônico.

Fonte conhecida: USA Mega, secundária. O arquivo não preserva resposta HTTP, data original de captura ou versão do coletor. Hash antes/depois: `c154cb21ae6381efe53f9735b5704d148156ba9737266de54e8badbf1d92c35c`.

## Estrutura observada

| Formato | Linhas | Representação |
| --- | ---: | --- |
| Sem multiplicador | 757 | 5 números + Mega Ball |
| Com Megaplier | 2.227 | resultado principal + atributo multiplicador |
| Total | 2.984 | 1996-09-06 a 2025-12-23 |

As 2.984 URLs e datas são distintas. Não há segundo sorteio ou bloco adicional no snapshot. Todas as linhas possuem cinco itens comuns, uma `li.bonus` e jackpot.

Megaplier aparece de 2003-12-05 a 2025-04-04 no arquivo: 2x em 446 linhas, 3x em 745, 4x em 838 e 5x em 198. Ele não aparece antes desse período nem a partir de 2025-04-08. Essas são fronteiras observadas na fonte secundária; seu significado oficial e a mudança de 2025 precisam de pesquisa.

## Contrato semântico

- O primeiro `ul` dentro de `section.results` contém o resultado principal.
- `li` sem classe contém os cinco números principais.
- `li.bonus` contém a Mega Ball.
- `li.multiplier` contém Megaplier e vira atributo, nunca bola.
- Classes desconhecidas ou um segundo bloco de resultados geram diagnóstico em vez de serem ignorados.
- A URL `/mega-millions/drawing/YYYY/M/D` é referência externa; a data visível é conciliada com ela.
- A data é identidade provisória porque o HTML não contém número oficial de concurso.
- A ordem recebida é preservada e os cinco números são exigidos em ordem crescente, conforme o snapshot.

## Envelope provisório e dinheiro

O envelope observado é cinco números distintos de 1–75 e uma Mega Ball de 1–52. Esses máximos históricos não são a regra atual nem uma versão certificada; servem somente para testar fixtures antes da pesquisa oficial.

Todos os jackpots são parseáveis: 2.972 em Million e 12 em Billion. O campo é `advertised_jackpot`, Decimal e USD, mantendo texto original. Ele não significa pagamento, arrecadação ou valor em dinheiro.

## Fixtures

- 2025-12-23: forma atual observada sem multiplicador, jackpot de $100 Million.
- 2025-04-04: última linha observada com Megaplier, 2x.
- 1996-09-06: primeiro resultado do snapshot, sem multiplicador.

Mutações somente em teste cobrem datas, divergência entre URL/texto, inteiros, contagem, duplicidade, ordem, limites, dinheiro, multiplicador e estruturas desconhecidas.

## Dados ausentes e pesquisa necessária

O snapshot não possui número oficial, horário, ganhadores, faixas, arrecadação, cash value ou local. USD é inferido do símbolo/contexto e precisa ser confirmado com fonte oficial.

Antes da auditoria integral, pesquisar:

- todas as matrizes, nomes históricos da modalidade e datas exatas de vigência;
- lançamento, mudanças e semântica do Megaplier, especialmente abril de 2025;
- fonte oficial estruturada, cobertura, identificadores e correções;
- calendário histórico, horário/fuso e semântica financeira;
- política para resultados anteriores à adoção do nome Mega Millions.

## Reprodutibilidade

```powershell
python -m unittest discover -s tests -p 'test_mega_millions_ingestion.py' -v
```

Não há download, navegador, banco ou escrita de candidatos. O HTML é lido somente em memória.

## Próxima tarefa

SPEC-0012 — Pesquisar e especificar as versões históricas oficiais, a mudança de 2025 e a fonte preferencial da Mega Millions antes da auditoria completa.
