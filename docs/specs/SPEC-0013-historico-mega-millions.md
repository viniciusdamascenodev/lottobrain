# SPEC-0013 — Regras versionadas e histórico da Mega Millions

## Estado

Concluída em 2026-10-14.

## Objetivo e limites

Implementar as sete matrizes pesquisadas na SPEC-0012, normalizar integralmente o HTML e produzir diagnóstico reproduzível. Sem rede, banco, coleta, interface ou alteração do raw.

## Critérios definidos antes da implementação

- Selecionar regra pela data, com limites próprios para números e Mega Ball.
- Não preencher dias sem sorteio entre versões.
- Distinguir `not_applicable`, `drawn_optional_megaplier` e `ticket_assigned_multiplier`.
- Exigir Megaplier somente de 2003-12-05 a 2025-04-04.
- Não fabricar fator do sorteio após a mudança de 2025.
- Preservar cinco números, Mega Ball, jackpot, fonte e identidade provisória por data.
- Detectar duplicidade e manter todas as linhas problemáticas no diagnóstico.
- Conciliar 2.984 linhas, hash, período, versões e formas da SPEC-0011.
- Salvar somente diagnóstico e cobrir todas as fronteiras com testes.

## Entregas e decisões

- `app/ingestion/mega_millions.py`: sete regras, seleção temporal e política de multiplicadores.
- `app/ingestion/mega_millions_history.py`: baseline, auditoria e contagens específicas.
- `tests/test_mega_millions_history.py`: seis testes de fronteiras, lacunas, limites, multiplicadores e reprodutibilidade.
- [Relatório](../data/mega-millions-normalizacao-historica.md), [diagnóstico JSON](../data/mega-millions-normalizacao-historica.json) e aprendizados L-051 a L-054.

A ausência pós-2025 é semântica e não `missing`: o fator passou a pertencer à aposta. O candidato registra apenas o estado da regra. A primeira fronteira foi corrigida para incluir 1999-01-12 na matriz original após confronto com o snapshot.

## Verificação final

- 2.984 candidatos válidos e únicos; nenhum problema, duplicidade ou identidade ausente.
- Distribuição das sete regras: 172, 348, 324, 869, 420, 776 e 75.
- Estados: 682 não aplicáveis, 2.227 Megapliers sorteados e 75 multiplicadores atribuídos por aposta.
- 2.984 jackpots anunciados parseáveis.
- Diagnóstico reproduzível com hash `8a22355224a6e54461cbfa267735c57ea3a5dabab7b24fb3cda6e32e8817644c`.
- Fonte preservada antes/depois; nenhuma escrita de candidato ou alteração do raw.

## Limitações

Validade significa consistência com regras pesquisadas e snapshot secundário, não certificação oficial linha a linha. A matriz 1999 continua com confiança média. Identificador oficial, faixas, ganhadores, cash value, horário e local não existem no arquivo. Regras financeiras e diferenças por jurisdição permanecem fora do escopo.

## Próxima tarefa recomendada

**SPEC-0014 — Contrato de extração e normalização do EuroMillions.**

Justificativa: cinco loterias já possuem ao menos contrato, e quatro brasileiras/norte-americanas têm auditoria integral. A próxima redução de risco é compreender o JSON europeu e seus componentes especiais antes de pesquisar regras históricas e auditar a sexta loteria.
