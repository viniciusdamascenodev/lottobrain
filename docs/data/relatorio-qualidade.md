# Relatório de qualidade dos dados históricos

## Critérios

A avaliação é preliminar e considera: completude estrutural, unicidade, validade aparente, consistência, rastreabilidade, semântica dos campos e atualidade. “Alta” não significa que o conjunto foi conciliado com uma fonte oficial externa.

## Mega-Sena

**Avaliação:** alta para concurso/data/números; média para metadados.

- 2.954 registros, concursos consecutivos de 1 a 2954.
- Período: 1996-03-11 a 2025-12-20.
- Nenhum concurso ausente no intervalo, duplicado ou linha integral duplicada.
- Nenhuma data inválida.
- Todos os registros têm seis números distintos, ordenados e entre 1 e 60.
- `Cidade / UF` está ausente em 2.331 registros (78,9%). Isso é frequentemente compatível com ausência de ganhador principal, mas precisa ser validado semanticamente.
- `Observação` está ausente em 2.059 registros (69,7%).
- Há 2.308 concursos com zero ganhadores de seis acertos; zero é valor válido, não ausência.
- Prêmios, acumulados e arrecadação estão presentes como texto localizado e exigirão conversão monetária explícita.

## Lotofácil

**Avaliação:** alta para concurso/data/números; média para metadados.

- 3.571 registros, concursos consecutivos de 1 a 3571.
- Período: 2003-09-29 a 2025-12-24.
- Nenhum concurso ausente no intervalo, duplicado ou linha integral duplicada.
- Nenhuma data inválida.
- Todos os registros têm quinze números distintos, ordenados e entre 1 e 25.
- `Cidade / UF` está ausente em 426 registros (11,9%), o mesmo número de concursos com zero ganhadores de 15 acertos; a relação deve ser confirmada, não assumida.
- `Observação` está ausente em 2.791 registros (78,2%).
- Existe um sorteio registrado em domingo. Pode ser evento especial ou exceção de calendário e requer confirmação externa.
- Valores financeiros são texto localizado.

## +Milionária

**Avaliação:** alta para concurso/data/números/trevos; média para metadados.

- 314 registros, concursos consecutivos de 1 a 314.
- Período: 2022-05-28 a 2025-12-24.
- Nenhum concurso ausente no intervalo, duplicado ou linha integral duplicada.
- Nenhuma data inválida.
- Todos os registros têm seis números distintos e ordenados entre 1 e 50.
- Todos têm dois trevos distintos entre 1 e 6.
- `Cidade / UF` está ausente em 312 registros (99,4%); somente dois concursos possuem ganhador da faixa principal, o que sugere uma ausência condicional a validar.
- `Observação` está vazia nos 314 registros.
- Foram observados sorteios em quarta, sábado e oito ocorrências em quinta/sexta. Mudanças ou exceções de calendário precisam ser confirmadas.
- A coluna `Acumulado 6 acertos + 2 Trevos` usa valor categórico (`Sim`), não valor monetário.

## Powerball

**Avaliação:** média para o resultado básico; baixa para metadados e estabilidade da ingestão.

- 3.742 registros, de 1992-04-22 a 2025-12-24.
- Todas as linhas possuem ao menos os seis elementos necessários ao resultado principal.
- Não foram detectadas datas inválidas, duplicidades de resultado ou repetição entre os cinco números principais.
- Números principais observados: 1 a 69; Powerball observado: 1 a 45.
- 860 linhas ultrapassam o limite atual aparente de 26 para Powerball. Como pertencem a períodos históricos, são evidência de versões de regras, não erro confirmado.
- A quantidade de elementos varia: 6 em 1.136 linhas, 7 em 1.926 e 13 em 680. O HTML mistura resultado principal, multiplicador e Double Play na mesma linha.
- O jackpot é texto (`Million`/`Billion`) e exige moeda, escala e precisão explícitas.
- Não há identificador estruturado do concurso, faixas, ganhadores, arrecadação ou local.
- A origem é uma página de terceiro e o formato HTML é vulnerável a mudanças visuais.

## Mega Millions

**Avaliação:** média para o resultado básico; baixa para metadados e estabilidade da ingestão.

- 2.984 registros, de 1996-09-06 a 2025-12-23.
- Todas as linhas possuem ao menos seis elementos para o resultado principal.
- Não foram detectadas datas inválidas, duplicidades de resultado ou repetição entre os cinco números principais.
- Números principais observados: 1 a 75; Mega Ball observado: 1 a 52.
- 119 linhas têm número principal acima do limite atual aparente de 70 e 658 têm Mega Ball acima de 25. Os valores são compatíveis com a necessidade de regras históricas e não devem ser corrigidos sem pesquisa.
- A quantidade de elementos varia: 6 em 757 linhas e 7 em 2.227, aparentemente pela presença de multiplicador.
- Jackpot é texto e não há identificador estruturado, faixas, ganhadores, arrecadação ou local.
- Mesmos riscos de fonte secundária e alteração do HTML observados no Powerball.

## EuroMillions

**Avaliação:** alta estrutural; média quanto à proveniência e semântica.

- 1.906 objetos, de 2004-02-13 a 2025-12-26.
- Nenhuma data, `id`, `draw_id` ou linha integral duplicada.
- Nenhum campo ausente entre os sete campos observados.
- Todos os registros possuem cinco números distintos entre 1 e 50 e duas estrelas distintas entre 1 e 12.
- Há 440 registros com `has_winner=true` e 1.466 com `false`.
- `prize` varia de 0 a 250.000.000; nove registros têm valor zero. A moeda e o significado exato do valor não estão documentados no arquivo.
- `id` varia de 1 a 4058, com 2.152 valores ausentes na sequência. Isso não representa necessariamente concursos ausentes: o identificador pode pertencer a uma tabela maior da API.
- `draw_id` não possui semântica documentada e não deve ser usado como chave canônica antes de confirmação.
- Não existem faixas, número de ganhadores, arrecadação ou local.

## Problemas transversais

1. **Atualidade:** os arquivos terminam em dezembro de 2025 e estão desatualizados em 2026-09-01.
2. **Proveniência:** não há manifesto junto aos arquivos com URL efetiva, horário, status HTTP, hash na coleta e versão do coletor.
3. **Regras históricas:** nenhuma fonte inclui uma versão explícita das regras aplicável a cada concurso.
4. **Moeda:** BRL é inferível pelo `R$`; USD é inferível nas fontes americanas; EuroMillions não declara moeda no registro.
5. **Datas:** não há horário nem timezone.
6. **Financeiro:** planilhas brasileiras e HTMLs usam textos localizados; o JSON usa número sem unidade documentada.
7. **Semântica desigual:** “prêmio” pode significar jackpot anunciado, prêmio pago ou estimativa, dependendo da fonte.
8. **Cobertura internacional:** dados de prêmio e ganhadores são muito menos completos do que nas planilhas brasileiras.
9. **Encoding:** nomes de planilhas e alguns cabeçalhos aparecem com caracteres acentuados degradados no leitor usado, exigindo mapeamento por significado e testes com amostras, não correspondência textual frágil.

## Dados prioritários ainda necessários

| Prioridade | Dado | Motivo |
|---|---|---|
| Alta | Versões históricas das regras | Evitar marcar resultados antigos válidos como inválidos |
| Alta | Origem e metadados de cada coleta | Auditoria, reprocessamento e confiabilidade |
| Alta | Identificador oficial das loterias americanas | Idempotência e conciliação |
| Alta | Timezone e horário oficial | Agendamento e ordenação temporal corretos |
| Alta | Moeda e semântica de cada campo financeiro | Evitar análises monetárias incorretas |
| Média | Faixas e ganhadores internacionais | Igualar profundidade analítica entre loterias |
| Média | Arrecadação internacional | Análises financeiras e de participação |
| Média | Calendários e exceções históricas | Detectar concursos realmente ausentes |
| Baixa | Local do sorteio | Contexto e filtros, sem impedir análise principal |

