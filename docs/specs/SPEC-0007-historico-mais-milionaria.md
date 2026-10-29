# SPEC-0007 — Normalizador e validação histórica da +Milionária

## Estado

Concluída em 2026-09-15.

## Objetivo e limites

Normalizar o XLSX local em candidatos somente em memória e gerar diagnóstico separado. Sem banco, coleta, interface, alterações de dados brutos, pipeline legado ou relatórios anteriores. Preservar alterações preexistentes.

## Critérios definidos antes da implementação

- Conciliar 314 concursos (1–314), de 2022-05-28 a 2025-12-24, com hash da SPEC-0001.
- Validar seis números distintos e ordenados entre 1 e 50 e dois trevos distintos entre 1 e 6, em componentes separados. Não ordenar trevos silenciosamente nem presumir sua ordem.
- Mapear as dez faixas com combinação de acertos/trevos, incluindo grupos “1 ou nenhum trevo” sem separá-los artificialmente.
- Preservar arrecadação, estimativa, moeda BRL, cidade de ganhadores e observação. Tratar “Acumulado” como categoria, não dinheiro, mantendo texto original e distinguindo ausência de “Não”.
- Rejeitar cabeçalhos essenciais ausentes, colisões de nomes e largura incompatível. Diagnosticar números, trevos, datas, valores e contagens inválidos com campo/posição.
- Detectar duplicidades, identidade ausente e lacunas sem descartar linhas. Comparar cidades ausentes (312) e observações ausentes (314).
- Usar três fixtures reais (início/meio/fim), testes de casos inválidos e duas auditorias completas com diagnóstico idêntico.
- Salvar somente relatório diagnóstico, confirmar hashes dos seis arquivos brutos e registrar aprendizados reutilizáveis.

## Limitações

Regra baseline numérica observada, não certificação oficial histórica. Calendários, significado de categorias/zeros e proveniência original exigem pesquisa futura. Reutilizar somente primitivas e agregação já testadas, sem criar framework genérico.

## Entregas e decisões

- `app/ingestion/mais_milionaria.py`: leitor e normalizador específicos, definição numérica baseline e mapeamento das dez faixas.
- `app/ingestion/mais_milionaria_history.py`: conciliação, auditoria em memória e contagem separada de trevos/categorias.
- `tests/fixtures/mais_milionaria_rows.json`: concursos reais 1, 158 e 314; mutações de teste não são inseridas no histórico.
- `tests/test_mais_milionaria_ingestion.py`: dez testes, incluindo estrutura, trevos, números, categorias e auditoria completa.
- [Relatório](../data/mais-milionaria-normalizacao-historica.md), [diagnóstico JSON](../data/mais-milionaria-normalizacao-historica.json) e aprendizados L-029 a L-031.

Primitivas internas da Lotofácil e agregação da SPEC-0005 foram reutilizadas, sem alterar esses módulos. Nenhum framework genérico foi criado. Validação de negativos ocorre antes dos construtores de domínio para acumular problemas em vez de interromper o lote. Trevos usam semântica de ordem `NONE`, preservando a ordem recebida; não são ordenados nem misturados com bolas.

## Verificação final

- 314 candidatos válidos e únicos, zero duplicidades/lacunas/problemas, 1.884 números e 628 trevos. Todas as oito comparações da baseline coincidiram.
- Duas execuções com capturas locais diferentes coincidiram e o diagnóstico salvo foi conciliado por teste.
- 44 testes unittest passaram, dez novos; duas verificações legadas passaram por execução direta, não via pytest. Compilação e verificação de whitespace passaram.
- Os seis hashes brutos mantiveram os valores da SPEC-0001. Pipeline, dados, dependências, relatórios anteriores e normalizadores existentes não foram modificados. Aprendizados foram incrementados.
- Nenhum candidato foi gravado; somente diagnóstico. Sem banco, coleta ou interface.
- Permanecem dúvidas externas de calendários, certificação histórica de regras, proveniência original e interpretação oficial de campos.

## Próxima tarefa recomendada

SPEC-0008 — Contrato de extração e normalização da Powerball com fixtures históricas reais. Validar a separação de bolas, Power Play e Double Play antes de auditar todo o HTML.
