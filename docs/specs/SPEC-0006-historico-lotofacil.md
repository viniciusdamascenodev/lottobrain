# SPEC-0006 — Normalizador e validação histórica da Lotofácil

## Estado

Concluída em 2026-09-15.

## Objetivo e escopo

Transformar o XLSX existente em candidatos do domínio, somente em memória, e produzir diagnóstico reproduzível. Não criar banco, coletores, interface ou corrigir arquivos brutos e relatórios anteriores.

## Critérios definidos antes da implementação

- Ler e conciliar 3.571 concursos, 1–3571, de 2003-09-29 a 2025-12-24, com o hash da SPEC-0001.
- Validar quinze inteiros distintos e ordenados entre 1 e 25, sem bolas especiais.
- Mapear as cinco faixas de 11 a 15 acertos, valores BRL e metadados, preservando zero, ausência e texto original.
- Exigir cabeçalhos essenciais e rejeitar colisões de nomes normalizados, evitando truncamento silencioso.
- Diagnosticar duplicidades, lacunas, datas e números inválidos, ausência de identidade e problemas financeiros com campo e posição.
- Comparar ausência de cidades (426) e observações (2.791) com a baseline.
- Testar amostras reais do início, meio e fim e auditar o histórico completo duas vezes.
- Salvar somente diagnóstico separado, nunca candidatos. Confirmar integridade dos seis arquivos brutos e preservar alterações anteriores.

## Regra e limites

A regra numérica baseline inicia na primeira data observada. Não representa pesquisa oficial de todas as regras históricas. Faixas inferiores têm valores diferentes em períodos distintos: preservar o rateio de cada concurso, sem fixar valores atuais. Calendário, horário original da coleta, semântica de zeros financeiros e exceções de domingo continuam pendentes de pesquisa externa.

## Entregas

Normalizador específico, auditoria histórica, três fixtures reais, testes, diagnóstico JSON e Markdown e aprendizados incrementais.

## Resultado e verificação

- 3.571 candidatos válidos e únicos; zero problemas de normalização, duplicidades ou lacunas. 53.565 valores principais.
- Todas as oito comparações da baseline coincidiram. Duas auditorias com instantes locais diferentes geraram o mesmo diagnóstico, e o JSON salvo coincidiu com a execução.
- 34 testes da suíte unittest passaram, incluindo nove desta etapa. Duas verificações legadas passaram por execução direta, não via pytest. Compilação e verificação de whitespace passaram.
- Os seis hashes brutos coincidiram com a SPEC-0001. Não houve modificação de dados, relatórios anteriores, dependências, pipeline legado ou módulos da Mega-Sena. Somente os aprendizados foram incrementados além dos novos arquivos desta etapa.
- Nenhum candidato foi persistido; apenas diagnóstico JSON/Markdown. Sem banco, interface ou coleta.

## Decisões de implementação

`app/ingestion/lotofacil.py` mantém o adaptador específico e `lotofacil_history.py` reaproveita a agregação já testada da SPEC-0005 com baseline própria e versão explícita. Não foi extraído um framework comum nem modificada a Mega-Sena. O parser local distingue dinheiro numérico de texto brasileiro e rejeita montantes não finitos. A leitura exige concurso, data, quinze bolas e cinco pares de ganhadores/rateios; montantes adicionais ausentes são desconhecidos. Collisão de nomes e largura incompatível são falhas estruturais explícitas.

Mapeamento: `Bola1..15` → `primary.main`; `Ganhadores/Rateio N acertos` → `hits_N`, N=11..15; `Acumulado 15 acertos` → `rollover_amount`; arrecadação → `sales_total`; estimativa → `next_estimated_jackpot`; acumulado da Independência → `special_draw_rollover`. Cidade/UF e observação ficam como texto de origem em metadados.

Evidências e ressalvas: [relatório](../data/lotofacil-normalizacao-historica.md) e [diagnóstico](../data/lotofacil-normalizacao-historica.json). Fixtures incluem concursos 1, 1786 e 3571. Regressões usam alterações controladas dessas amostras apenas em testes, não dados históricos fictícios.

## Próxima tarefa recomendada

SPEC-0007 — Normalizador e validação histórica da +Milionária, para exercitar seis números principais e o grupo separado de trevos, sem ampliar para banco ou coleta.
