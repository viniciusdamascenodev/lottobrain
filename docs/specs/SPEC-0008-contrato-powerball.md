# SPEC-0008 — Contrato de extração e normalização da Powerball

## Estado

Concluída em 2026-09-16.

## Objetivo

Definir e testar a fronteira entre o HTML histórico e o domínio com amostras reais dos três formatos observados. Esta SPEC não certifica regras históricas nem aprova ainda a normalização integral das 3.742 linhas.

## Critérios definidos antes da implementação

- Ler o HTML com biblioteca padrão, sem navegador, rede ou alteração da fonte.
- Exigir estrutura semântica: data/link, primeiro `ul` como sorteio principal, classes `bonus` e `multiplier`, e `ul.extradraw` como Double Play.
- Separar cinco bolas principais, Powerball, Power Play e Double Play. Nunca inferir significado apenas pela contagem total de `li`.
- Usar fixtures reais para: resultado simples; resultado com Power Play; resultado com Power Play e Double Play.
- Preservar URL e data visível, detectar divergência entre elas e usar data como identidade provisória por ausência de número oficial.
- Converter jackpot Million/Billion em Decimal USD com texto original, sem confundir valor anunciado com prêmio pago.
- Rejeitar elementos desconhecidos, multiplicador inválido, Double Play incompleto, datas e valores monetários inválidos com diagnósticos estruturados.
- Manter Double Play como série adicional opcional e Power Play como atributo da série principal.
- Documentar a distribuição dos três formatos, limites observados, pendências externas e proteção necessária antes da auditoria completa.
- Confirmar que nenhum raw, pipeline ou relatório anterior foi alterado e executar a suíte completa.

## Limites conscientes

O contrato usa um envelope observado (main 1–69, Powerball 1–45) apenas nas fixtures. Ele não substitui versões oficiais de regras. Fonte secundária USA Mega, sem número de concurso, ganhadores, faixas, arrecadação ou local. Sem banco, coleta, interface ou download.

## Entregas e decisões

- `app/ingestion/powerball.py`: leitor HTML baseado em estrutura, linha bruta tipada, normalizador de fixtures e regra provisória explicitamente não certificada.
- `tests/fixtures/powerball_rows.json`: três linhas reais reconciliadas com o raw — 2025-12-24, 2021-08-21 e 1992-04-22.
- `tests/test_powerball_ingestion.py`: nove testes de contrato, estrutura e falhas.
- [Relatório do contrato](../data/powerball-contrato-extracao.md) e aprendizados L-032 a L-035.

O leitor usa somente `html.parser` da biblioteca padrão. A classificação depende de blocos/classes e falha explicitamente diante de item ou bloco de resultado desconhecido. Jackpot é `advertised_jackpot`, não prêmio pago. A data fornece chave provisória e `drawing_path` permanece referência externa; nenhum número oficial foi inventado.

Não foi criado diagnóstico JSON histórico: isso implicaria normalizar todas as linhas sob um envelope que esta SPEC declara não oficial. A ausência é deliberada e mantém o critério de pesquisa antes da auditoria integral.

## Evidências finais

- 3.742 linhas extraídas: 1.136 simples, 1.926 com Power Play e 680 com Power Play + Double Play. Zero classes desconhecidas no snapshot; 3.742 caminhos de sorteio distintos.
- As três fixtures normalizam com bolas, Powerball, atributo e série adicional separados. Mutações cobrem datas divergentes, escala monetária, multiplicador, números, ordem, duplicidade e Double Play incompleto.
- 53 testes unittest passaram, incluindo nove novos; duas verificações legadas passaram por execução direta, não via pytest. Compilação e verificação de whitespace passaram.
- Os seis hashes brutos coincidiram com a SPEC-0001. Nenhum raw, dependência, pipeline, relatório anterior ou normalizador existente foi modificado; aprendizados foram apenas incrementados.
- Sem rede, navegador, banco, persistência, coleta ou interface.

## Próxima tarefa recomendada

SPEC-0009 — Pesquisa e especificação das versões históricas oficiais da Powerball e da fonte preferencial, antes da auditoria integral.
