# SPEC-0010 — Regras versionadas e histórico da Powerball

## Estado

Concluída em 2026-10-14.

## Objetivo e limites

Implementar as sete matrizes pesquisadas na SPEC-0009, normalizar integralmente o snapshot HTML e produzir diagnóstico reproduzível. Sem rede, banco, coleta, interface, alteração do raw ou integração com a API MUSL.

## Critérios definidos antes da implementação

- Selecionar regra exclusivamente pela data e não validar resultados antigos com limites atuais.
- Representar sete matrizes sem preencher os dias sem sorteio entre versões.
- Separar Power Play em `not_applicable`, `fixed_prize_no_multiplier` e `observed`.
- Exigir multiplicador somente nas vigências em que ele é sorteado.
- Exigir Double Play desde 2021-08-23 e rejeitá-lo antes do lançamento.
- Manter cinco números principais e uma Powerball por série, com limites da época.
- Detectar duplicidades e preservar a identidade provisória por data sem inventar número oficial.
- Conciliar 3.742 linhas, período, hash, contagens por regra e três formatos da SPEC-0008.
- Salvar somente diagnóstico, manter relógio fora do hash e cobrir fronteiras/mutações em testes.

## Entregas e decisões

- `app/ingestion/powerball.py`: sete regras validadas, seleção por data e estados históricos de Power Play/Double Play.
- `app/ingestion/powerball_history.py`: auditoria local, baseline, contagens por regra e componentes especiais.
- `tests/test_powerball_history.py`: sete testes para fronteiras, lacunas, limites históricos, recursos opcionais, duplicidade e reprodutibilidade.
- [Relatório](../data/powerball-normalizacao-historica.md), [diagnóstico JSON](../data/powerball-normalizacao-historica.json) e aprendizados L-040 a L-043.

Os identificadores de versão usam `snake_case` exigido pelo domínio. Double Play permanece uma série opcional na definição da matriz 2015 porque sua vigência é independente; o normalizador aplica a obrigatoriedade temporal explicitamente. Power Play permanece atributo da série principal e seu estado semântico é preservado em metadados.

## Verificação final

- 3.742 candidatos válidos e únicos, nenhum problema, duplicidade ou identidade ausente.
- Sete distribuições: 578, 514, 302, 350, 316, 388 e 1.294 linhas.
- 2.606 multiplicadores observados, 210 ausências por prêmio fixo e 926 períodos não aplicáveis.
- 680 Double Plays desde a data oficial de lançamento.
- 3.742 jackpots anunciados parseáveis, sem promovê-los a prêmio pago.
- Diagnóstico reproduzível com hash `41afe9224564a803fdd624c07fb65eed4514528f7b8a2ba0701982960520fd83`.
- Fonte com o mesmo SHA-256 antes/depois; nenhuma escrita de candidato ou alteração do raw.

## Limitações conscientes

A consistência é contra o snapshot secundário e as versões pesquisadas, não certificação linha a linha pela Powerball. Primeira matriz ainda tem confiança média. Identificador oficial, faixas, ganhadores, cash value, horário e local não estão disponíveis. Conjuntos históricos de multiplicadores e regras financeiras não foram implementados.

## Próxima tarefa recomendada

**SPEC-0011 — Contrato de extração e normalização da Mega Millions.**

Justificativa: a Powerball já tem uma vertical completa e reproduzível. A próxima redução de risco é entender as formas reais do segundo HTML norte-americano com poucas fixtures, mantendo pesquisa de regras e auditoria integral em tarefas posteriores.
