# SPEC-0016 — Regras versionadas e histórico do EuroMillions

## Estado

Concluída em 2026-10-14.

## Objetivo e limites

Implementar as três matrizes pesquisadas na SPEC-0015, normalizar integralmente o JSON e produzir diagnóstico reproduzível. Sem rede, banco, coleta, interface ou alteração do raw.

## Critérios definidos antes da implementação

- Selecionar regra pela data, com limite próprio para estrelas.
- Não preencher dias sem sorteio entre versões.
- Preservar cinco números e duas estrelas como componentes independentes.
- Manter `id` e `draw_id` apenas como referências externas da fonte.
- Renomear `has_winner` semanticamente para ganhador da faixa 5+2.
- Normalizar somente valores positivos como prêmio individual 5+2 em EUR e manter jurisdição PT/ES.
- Tratar os nove zeros como desconhecidos, nunca como EUR 0.
- Detectar duplicidade e manter linhas problemáticas no diagnóstico.
- Conciliar 1.906 linhas, hash, período, versões e baseline da SPEC-0014.
- Salvar somente diagnóstico e cobrir todas as fronteiras com testes.

## Entregas e decisões

- `app/ingestion/euro_millions.py`: três regras, seleção temporal e semântica pesquisada dos campos.
- `app/ingestion/euro_millions_history.py`: baseline, auditoria e contagens específicas.
- `tests/test_euro_millions_history.py`: seis testes de fronteiras, lacunas, limites, dinheiro, duplicidade e reprodutibilidade.
- `tests/test_euro_millions_ingestion.py`: contrato atualizado para dinheiro e provenance da SPEC-0016.
- [Relatório](../data/euro-millions-normalizacao-historica.md), [diagnóstico JSON](../data/euro-millions-normalizacao-historica.json) e aprendizados L-063 a L-066.

## Verificação final

- 1.906 candidatos válidos e únicos; nenhum problema, duplicidade ou identidade ausente.
- Distribuição das regras: 378, 562 e 966.
- 440 sorteios com ganhador 5+2 e 1.466 sem ganhador dessa faixa.
- 1.897 prêmios individuais 5+2 conhecidos em EUR; nove zeros preservados como desconhecidos.
- 1.906 `draw_id` únicos; `source_id` preservado com 2.152 lacunas entre mínimo e máximo.
- Diagnóstico reproduzível com hash `2b1048a885a12d704be8b6768c1ff9ea4bc6fbe0762785508fe847c0e358358d`.
- Fonte preservada antes/depois; nenhuma escrita de candidato ou alteração do raw.

## Limitações

Validade significa consistência com as regras pesquisadas e o snapshot secundário, não certificação oficial linha a linha. A origem PT ou ES exata não existe no endpoint legado. Horário, local, jackpot anunciado, faixas completas, ganhadores por país, arrecadação e extensões nacionais permanecem ausentes.

## Próxima tarefa recomendada

**SPEC-0017 — Consolidar os seis históricos e definir o contrato do catálogo configurável de loterias.**

Justificativa: as seis loterias de base agora têm inventário e contrato, e todas possuem auditoria histórica ou diagnóstico equivalente. Antes de banco e cadastro administrativo, é preciso consolidar garantias, lacunas e definir o mínimo configurável para adicionar loterias sem codificar regras específicas na interface.
