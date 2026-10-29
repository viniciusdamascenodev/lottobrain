# SPEC-0021 — Sincronização incremental limitada da Mega-Sena

## Estado

Concluída em 20/10/2026 (America/Sao_Paulo). Critérios registrados antes da construção.

## Objetivo

Planejar e executar um lote manual de consultas, mantendo cursor contíguo, retomada após falha e janela de revisão. Reutilizar coleta, normalização, raw e revisões da SPEC-0020.

## Critérios de aceitação

- Inicialização explícita pelo histórico auditado, conferindo hash antes de ancorar o cursor em 2954.
- Descoberta do último resultado incluída no orçamento; no máximo dez GETs por execução e quatro por padrão.
- Cursor só avança por concurso contíguo validado e com processamento concluído.
- Resposta descoberta antecipadamente não pula lacunas; pode ser reutilizada ao atingir seu número.
- Interrupção, 404, 429, transporte ou quarentena interrompem o lote sem pular o concurso pendente.
- Checkpoint atômico depois de cada avanço; replay/retomada idempotente após falha de gravação.
- Revisão circular de janela recente, sem regredir cursor e sem gerar revisões duplicadas.
- Intervalo mínimo entre consultas e cooldown persistido após 429.
- Reuso do lock existente, resumo de execução e testes offline com cenários de recuperação.
- Não criar scheduler, banco, publicação automática ou atualização em massa do histórico.

## Entregas

- `app/application/sync_mega_sena.py`: política de lote, cursor, revisão circular e pausa após 429, com relógio e espera injetáveis.
- `app/infrastructure/local_collection.py`: checkpoint atômico, validação do cursor e resumos de execução, sob o lock existente.
- `app/infrastructure/mega_sena_baseline.py`: âncora conferida pelo hash da baseline auditada.
- `app/interfaces/sync_mega_sena.py`: execução manual limitada e parâmetros validados.
- `app/application/collect_mega_sena.py`: retorno explícito do número normalizado para a coordenação do lote.
- `tests/test_mega_sena_sync.py`: 17 testes offline de continuidade, revisão, limites e falhas.
- [Guia de operação e recuperação](../engineering/sincronizacao-mega-sena.md).
- Aprendizados L-098 a L-104 em [learnings.md](../engineering/learnings.md).

## Verificação

- 17 testes novos e 37 testes existentes relacionados passaram: 54 no total selecionado.
- Testes demonstram: descoberta não pula lacunas; 404 interrompe; 429 persiste pausa; falha de checkpoint retoma sem duplicar; revisão circular detecta correções e preserva continuidade.
- Validação real limitada a dois GETs: último observado 3071, concurso 2955 válido, cursor avançou de 2954 para 2955.
- Concurso descoberto antecipadamente fica candidato e não aumenta a cobertura contígua.
- Os seis arquivos históricos permanecem com os hashes originais.
- Dependências preexistentes, pipeline legado e interface web foram preservados.

## Limitações explícitas

- A baseline é uma referência ao XLSX auditado, não sua importação no repositório incremental.
- Estado e revisões ficam em arquivos locais de desenvolvimento; cada arquivo tem atomicidade própria.
- A janela de revisão é recente e incremental; não certifica correções de todo o histórico.
- Não há scheduler ou repetição automática; a fonte continua com contrato observado, sem aprovação operacional recorrente.
- Cooldown usa política interna fixa de 15 minutos; `Retry-After` ainda não é interpretado.
- A verificação do checkpoint cobre sua revisão de fronteira; a auditoria completa de cobertura ainda será implementada.

## Próxima tarefa recomendada

**SPEC-0022 — Auditoria de cobertura e recuperação da ingestão Mega-Sena.**

Justificativa: antes da persistência definitiva, é preciso confrontar baseline, cursor, revisões, receipts, hashes e diagnósticos de todo o intervalo; identificar lacunas, artefatos órfãos e capturas antecipadas sem confundir existência de arquivo com concurso publicado. O resultado será um diagnóstico reproduzível e um procedimento seguro de recuperação.
