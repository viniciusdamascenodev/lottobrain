# SPEC-0014 — Contrato de extração do EuroMillions

## Estado

Concluída em 2026-10-14.

## Objetivo e limites

Definir e testar a fronteira entre o JSON histórico do EuroMillions e o domínio com fixtures reais. Esta SPEC não certifica regras, IDs ou dinheiro e não audita integralmente as 1.906 linhas.

Sem rede, banco, pesquisa externa, coleta, interface ou alteração do raw.

## Critérios definidos antes da implementação

- Exigir raiz como lista e cada item como objeto com exatamente sete campos.
- Manter cinco números e duas estrelas em componentes independentes.
- Preservar `has_winner` como booleano, sem convertê-lo em contagem.
- Preservar `id` e `draw_id` em namespaces separados sem inventar concurso oficial.
- Usar data como identidade provisória e não interpretar meia-noite GMT como horário do sorteio.
- Ler decimais sem conversão binária adicional e não normalizar `prize` sem moeda/semântica.
- Distinguir zero, inválido e desconhecido.
- Rejeitar tipos, cardinalidades, limites, duplicidades, ordem e estrutura incompatíveis.
- Reconciliar fixtures do início, descontinuidade de ID e fim com o raw imutável.

## Entregas e decisões

- `app/ingestion/euro_millions.py`: leitor JSON, linha tipada e normalizador conservador.
- `tests/fixtures/euro_millions_rows.json`: três registros reais de controle.
- `tests/test_euro_millions_ingestion.py`: sete testes de semântica, estrutura e falhas.
- [Relatório do contrato](../data/euro-millions-contrato-extracao.md) e aprendizados L-055 a L-058.

O envelope 1–50/1–12 serve apenas para fixtures. `reported_prize` mantém texto de origem com status desconhecido; não recebe EUR por inferência. `id` e `draw_id` não são descartados, mas também não definem a identidade canônica.

## Evidências finais

- 1.906 objetos uniformes, de 2004-02-13 a 2025-12-26.
- Cinco números e duas estrelas em todas as linhas; zero duplicidades internas ou desordem.
- 1.906 datas, IDs e draw IDs únicos.
- 440 registros com `has_winner=true` e 1.466 falsos.
- Prêmio entre 0 e 250 milhões, nove zeros, moeda e semântica não declaradas.
- Descontinuidade de `id` preservada sem interpretação.
- Sete testes novos aprovados; hash do raw preservado.

## Próxima tarefa recomendada

**SPEC-0015 — Regras históricas, campos e fontes do EuroMillions.**

Justificativa: usar o envelope máximo 1–12 para estrelas antigas seria permissivo. É necessário pesquisar versões oficiais e esclarecer dinheiro/IDs antes de processar o histórico completo.
