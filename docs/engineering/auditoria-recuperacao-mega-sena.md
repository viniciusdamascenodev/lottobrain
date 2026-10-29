# Auditoria e recuperação da ingestão Mega-Sena

## Executar a auditoria

Na raiz do repositório:

```powershell
python -m app.interfaces.audit_mega_sena
```

O comando é offline, não cria lock, não consulta a CAIXA e não modifica o workspace. A saída JSON pode ser salva em um arquivo novo fora dele:

```powershell
python -m app.interfaces.audit_mega_sena --output docs/data/mega-sena-auditoria-nova.json
```

O comando rejeita arquivo de saída já existente e destino dentro do workspace. Para auditar um backup, usar `--workspace` com o diretório da cópia.

## O que é conferido

1. Hash do XLSX usado como baseline, confrontado com a referência auditada da SPEC-0005.
2. Nome, tamanho e SHA-256 de cada raw.
3. Identidade, timestamp com timezone, status HTTP, URL restrita e referência raw de cada receipt.
4. Outcomes, identidade canônica, referência à revisão e coerência com a validação atual.
5. Sequência, estado candidato, identidade e hash de todas as revisões.
6. Reprodução da revisão a partir de seu raw, usando o normalizador identificado no relatório.
7. Evidência de processamento e continuidade em todo o intervalo entre baseline e cursor.
8. Resumos de lote, quantidade de consultas, reutilização de descoberta, último observado e pendências.
9. Órfãos, arquivos temporários, links, entradas inesperadas e mudanças observadas durante a leitura.

O arquivo do cursor isolado não prova cobertura. Um raw de hash correto isolado também não prova que a interpretação esteja correta.

## Resultado

| Status | Significado | Saída do comando |
|---|---|---:|
| `healthy` | nenhuma inconsistência encontrada nas evidências examinadas | 0 |
| `attention` | avisos, como captura sem outcome ou raw órfão | 0 |
| `failed` | erro de integridade, continuidade ou snapshot instável | 2 |
| falha de I/O da execução | auditoria não concluída | 1 |

`healthy` não significa sincronização em dia, publicação aprovada ou certificação oficial de toda a história. Conferir sempre `coverage`, `issues` e `recovery_plan`.

## Coberturas diferentes

- `baseline_referenced_through`: referência ao XLSX auditado. O auditor confere seu hash, sem refazer a leitura/normalização da planilha.
- `materialized_candidate_contests`: arquivos de revisão encontrados, inclusive os problemáticos.
- `verified_candidate_contests`: concursos cujas revisões possuem cadeia consistente e reproduzível.
- `cursor_claimed`: continuidade declarada pelo checkpoint.
- `cursor_verified_through`: prefixo realmente sustentado por evidência depois da baseline.
- `ahead_candidates`: candidatos válidos adiante do cursor; não cobrem seus intermediários.
- `pending_identifiers_to_observed`: distância até o maior concurso nas capturas salvas.
- `unverified_after_cursor`: intervalos ainda sem candidato verificado; apresentados como faixas compactas.

O último observado é o das evidências locais. A auditoria não verifica o último concurso disponível na web.

## Reprodutibilidade e concorrência

O relatório não inclui relógio da auditoria, path absoluto, PID do auditor ou ordem de leitura do filesystem. Inclui manifesto de caminhos relativos, tamanhos e hashes de todos os arquivos, além da versão do normalizador.

O leitor captura o inventário duas vezes. Diferença de conteúdo, arquivos ou baseline invalida o diagnóstico. Um `.collection.lock` encontrado também gera erro. Para uma evidência operacional forte, interromper coletas ou auditar uma cópia estável; duas leituras não oferecem uma transação de filesystem nem detectam toda mudança transitória ocorrida e revertida entre elas.

Links simbólicos e junctions detectados não são seguidos. Cada arquivo tem limite de leitura de 8 MiB neste adaptador; raws ainda obedecem ao teto de 256 KiB do coletor. Excesso ou falha de leitura gera diagnóstico e impede certificação silenciosa.

## Recuperação manual

A auditoria somente recomenda ações. Não há opção `--repair`, alteração automática de cursor ou remoção automática de arquivos.

| Ação do relatório | Procedimento |
|---|---|
| `restore_baseline` | localizar o XLSX original no backup e conferir seu SHA-256 antes de qualquer substituição autorizada |
| `restore_workspace` | identificar o workspace correto ou restaurar cópia íntegra; não inicializar vazio para encobrir perda |
| `restore_artifact` | restaurar os bytes exatos do backup conferindo o hash esperado; conservar a evidência corrompida para investigação |
| `restore_receipt` | restaurar metadados originais; nunca inventar URL ou instante de captura para completar a cadeia |
| `restore_revision` | restaurar histórico de revisões do backup; se indisponível, reconstruir separadamente sob revisão humana |
| `replay_receipt` | examinar o raw e a versão do normalizador; usar replay unitário quando a cadeia de revisões estiver íntegra |
| `restore_contiguous_evidence` | investigar cada faixa dentro do cursor, recuperar evidências faltantes e auditar novamente antes de sincronizar |
| `inspect_checkpoint` | confrontar baseline, revisões e runs; não reduzir ou aumentar manualmente o número para esconder divergências |
| `reconcile_normalizer_version` | reproduzir com a versão registrada e avaliar mudança de interpretação; não reescrever revisão anterior |
| `inspect_orphan` | conservar raw e investigar interrupção; ausência de receipt não autoriza apagar nem fabricar proveniência |
| `inspect_interrupted_write` | preservar temporário e comparar com backups; não promovê-lo a arquivo definitivo por seu nome |
| `retry_stable_snapshot` | confirmar que não há escrita em andamento e repetir em cópia estável; lock residual exige verificar o processo proprietário |
| `inspect_quarantine` | verificar diagnóstico e conteúdo; qualificar fonte/parser antes de repetir coleta ou replay |
| `inspect_run` / `inspect_evidence` | confrontar documentos apontados; manter original e registrar decisão humana |
| `continue_bounded_sync` | após resolver erros, continuar o lote manual com o orçamento e os limites da SPEC-0021 |

Uma nova consulta à CAIXA pode produzir bytes diferentes. Ela cria nova evidência; não recupera magicamente o artefato original de um hash ausente. Da mesma forma, reprocessar em um workspace sem histórico de revisões pode criar uma nova revisão 1 e não reconstruir a ordem perdida. Nesses casos, preferir backup e reconstrução em cópia separada.

## Sequência de recuperação

1. Interromper escritas e preservar cópia do workspace e do diagnóstico.
2. Tratar integridade de raw e receipts antes das interpretações derivadas.
3. Restaurar/reconstruir revisões em cópia de trabalho, preservando originais.
4. Auditar a cópia novamente e conferir a continuidade inteira.
5. Registrar evidências e decisão humana antes de qualquer substituição operacional.
6. Retomar a sincronização limitada somente após resolver os erros.

Não foram executadas recuperações nesta SPEC; o workspace real não apresentou erro. Os testes simulam falhas em diretórios temporários.

## Testes

```powershell
python -m unittest discover -s tests -p test_mega_sena_audit.py -v
```

SHA-256 comprova consistência dos bytes e relações locais, não autenticidade criptográfica da publicação da CAIXA. Um agente capaz de reescrever todos os documentos e hashes pode fabricar uma cadeia coerente; proteção de storage, backups e controles de acesso continuam necessários.
