# Lotofácil — normalização histórica em memória

## Fonte e método

Fonte local: `data/raw/lotofacil/lotofacil_resultados.xlsx`, primeira planilha, somente leitura. Fonte conhecida pelo inventário: download Caixa; URL efetiva e instante original da captura não estão certificados junto ao arquivo. Nenhuma pesquisa externa ou coleta foi feita nesta etapa.

Hash antes/depois: `0ab2c742f0ae6e3b567af2f99744b6d4071c08427c08941a94087e6bde36918e`.

Leitor redefine dimensões do XLSX, exige colunas essenciais e rejeita cabeçalhos normalizados repetidos e linhas com largura incompatível. Aliases cobrem nomes acentuados e variantes degradadas efetivamente presentes. Normalização seguida de validação do domínio, comparação com baseline e diagnóstico histórico. Candidatos ficam em memória.

## Resultado

| Métrica | Resultado |
| --- | --- |
| Registros, candidatos válidos e chaves únicas | 3.571 |
| Concursos | 1–3571 |
| Datas | 2003-09-29 a 2025-12-24 |
| Inválidos, duplicidades, identidades ausentes e lacunas | 0 |
| Valores principais | 53.565, entre 1 e 25 |
| Cidade / UF ausente | 426 |
| Observação ausente | 2.791 |
| Comparações da baseline | 8 de 8 coincidentes |

Quinze números distintos e ordenados por concurso, sem números especiais. As cinco faixas são `hits_15` a `hits_11`, com ganhadores e rateio individual separados. Não inferir quantidade de pessoas únicas a partir da soma de ganhadores.

## Campos existentes e ausentes

- Existentes: concurso, data, quinze bolas, cinco contagens de ganhadores, cinco rateios, acumulado de 15 acertos, arrecadação, estimativa do próximo prêmio, acumulado especial da Independência, cidades de ganhadores e observações.
- Moeda BRL vem do contexto da exportação `R$`; fuso Brasil é metadado da loteria, não prova de horário do sorteio.
- Ausentes: horário, local do sorteio (cidade de ganhadores não equivale a local do sorteio), origem de coleta verificável completa e regras oficiais historicamente certificadas.
- Não derivado: prêmio principal total. Rateio individual, estimativa e acumulado são conceitos diferentes.

## Dinheiro e ressalvas

Cada uma das nove finalidades monetárias tem 3.571 valores parseáveis, preservados com Decimal, BRL e texto original. `known` significa disponibilizado e parseável, não certificado externamente.

| Finalidade | Valores zero |
| --- | --- |
| Estimativa do próximo prêmio | 218 |
| Rateio de 15 acertos | 426 |
| Rateios de 11–14 acertos | 0 |
| Acumulado de 15 acertos | 3.005 |
| Arrecadação | 428 |
| Acumulado especial | 893 |

Evidência: concurso 1 traz `Arrecadacao Total = R$0,00` e estimativa `R$0,00`, mas a observação menciona R$250.000,00 para o próximo concurso. Não sobrescrever a coluna com interpretação de texto livre nesta etapa. Validar a semântica antes de análises financeiras.

Rateio de 11 acertos é R$2,00 no concurso 1 e R$7,00 no concurso 3571. Não aplicar valores atuais retroativamente. Mudanças de rateio e calendários precisam de referências oficiais. A exceção de domingo registrada na SPEC-0001 permanece pendente e não é rejeitada por uma regra semanal inventada.

## Reprodutibilidade e diagnóstico

```powershell
python -m app.ingestion.lotofacil_history
python -m unittest discover -s tests -p 'test_lotofacil_ingestion.py' -v
```

A CLI escreve somente diagnóstico no stdout; retorna 0 apenas com integridade, conciliação e elegibilidade de todas as linhas. Erros estruturais interrompem a leitura explicitamente. `row_position` conta registros não vazios, não a linha física Excel.

Hash da interpretação: `b74f5a227fec52c05a8151d6ac7465ada4d28bb07b28849e5630ec05eb70466b`. O relógio da captura local é excluído desse hash. Diagnóstico detalhado: [JSON](lotofacil-normalizacao-historica.json).

## Próxima etapa

SPEC-0007 — Normalizador e validação histórica da +Milionária. Seus trevos exercitam o grupo especial do domínio, sem antecipar persistência ou coleta.
