# SPEC-0011 — Contrato de extração da Mega Millions

## Estado

Concluída em 2026-10-14.

## Objetivo e limites

Definir e testar a fronteira entre o HTML histórico da Mega Millions e o domínio com fixtures reais. Esta SPEC não certifica regras históricas nem normaliza integralmente as 2.984 linhas.

Sem banco, rede, pesquisa externa, coleta, interface ou alteração do raw. O envelope numérico é explicitamente provisório.

## Critérios definidos antes da implementação

- Ler com biblioteca padrão e sem navegador.
- Exigir data/link, primeiro bloco de resultados, cinco números, `bonus`, Megaplier opcional e jackpot.
- Manter Mega Ball como componente e Megaplier como atributo.
- Rejeitar classes e blocos desconhecidos, números/multiplicadores/datas/dinheiro inválidos e divergência de datas.
- Preservar URL, data visível, texto monetário, Decimal e USD contextual.
- Usar fixtures do início, última ocorrência observada de multiplicador e formato de 2025 sem multiplicador.
- Conferir contagem, formas, unicidade de URLs, limites observados e hash sem converter o snapshot inteiro em histórico aprovado.
- Registrar pendências e recomendar somente a pesquisa necessária antes da auditoria.

## Entregas e decisões

- `app/ingestion/mega_millions.py`: leitor específico, linha tipada e normalizador conservador de fixtures.
- `tests/fixtures/mega_millions_rows.json`: três linhas reais — 1996-09-06, 2025-04-04 e 2025-12-23.
- `tests/test_mega_millions_ingestion.py`: sete testes de semântica, falhas, estrutura e reconciliação com o raw.
- [Relatório do contrato](../data/mega-millions-contrato-extracao.md) e aprendizados L-044 a L-046.

O adaptador da Powerball não foi generalizado: apesar da aparência semelhante, Mega Ball, Megaplier, caminhos, limites e evolução histórica pertencem a outro contrato. A estrutura desconhecida falha de forma fechada. Jackpot continua sendo valor anunciado.

## Evidências finais

- 2.984 linhas e identidades por data distintas, de 1996-09-06 a 2025-12-23.
- 757 formas sem multiplicador e 2.227 com Megaplier; nenhuma classe/bloco desconhecido no snapshot.
- Limites observados 1–75 para principais e 1–52 para Mega Ball.
- Megaplier observado entre 2003-12-05 e 2025-04-04; ausência posterior preservada sem interpretação não pesquisada.
- 2.984 jackpots parseáveis: 2.972 Million e 12 Billion.
- Fixtures normalizam com grupos separados e mutações inválidas geram diagnósticos estruturados.
- Hash do raw preservado; nenhum candidato histórico ou dado bruto foi escrito.

## Próxima tarefa recomendada

**SPEC-0012 — Regras históricas e fontes da Mega Millions.**

Justificativa: o envelope 1–75/1–52 não pode auditar corretamente todas as épocas. É necessário pesquisar matrizes oficiais, mudança de nome, Megaplier e novo desenho de abril de 2025, além de decidir a fonte preferencial, antes de processar o histórico completo.
