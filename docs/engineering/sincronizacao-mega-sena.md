# Operação da sincronização incremental Mega-Sena

A [auditoria da SPEC-0022](auditoria-recuperacao-mega-sena.md) confere a cadeia completa e as lacunas do intervalo. Usá-la antes de recuperar estado, restaurar backup ou diagnosticar divergência de cursor.

## Inicialização e execução

Executar na raiz do repositório:

```powershell
python -m app.interfaces.sync_mega_sena --bootstrap-history
```

A opção confere o SHA-256 do XLSX auditado pela SPEC-0005 e registra uma baseline até o concurso 2954. Não lê a planilha novamente, não presume que seus concursos já estejam no repositório incremental e não faz carga de banco. O hash liga o checkpoint ao exato arquivo auditado anteriormente.

Depois da primeira execução:

```powershell
python -m app.interfaces.sync_mega_sena
```

Repetir `--bootstrap-history` não reinicia o cursor: a baseline precisa ser igual à já registrada. Não existe opção de reset silencioso ou de escolher um número arbitrário para pular concursos.

## Limites configuráveis

| Parâmetro | Padrão | Limites |
|---|---:|---|
| `--max-requests` | 4 | 1–10 GETs por execução, incluindo descoberta |
| `--review-window` | 3 | 0–20 concursos incrementais anteriores ao lote |
| `--interval` | 2 | 2–30 segundos antes de cada consulta |
| `--workspace` | data/collections/mega_sena | mesmo workspace do coletor unitário |

O intervalo é uma política conservadora do projeto, não um limite publicado pela CAIXA. Inclui pausa antes da primeira requisição, espaçando também invocações consecutivas no mesmo workspace. A trava exclusiva é mantida durante o lote. Não usar múltiplos workspaces para contornar orçamento ou pausa.

Um orçamento de 1 permite descoberta e, se o próximo concurso for o descoberto, avanço sem outro GET. Com backlog e orçamento de pelo menos 3, uma consulta é reservada para revisão quando há cobertura incremental anterior. Com orçamento 2, o avanço tem prioridade; usar pelo menos 3 para revisar enquanto recupera lacunas.

## Significado do cursor

O cursor indica o último concurso contíguo processado com sucesso depois da baseline. Ele não representa o maior número já capturado, a última data publicada ou um concurso certificado para publicação.

Exemplo: a descoberta recebe o 3071, mas o cursor está em 2954. A descoberta é preservada como candidata antecipada. O fluxo precisa processar 2955, 2956 e assim por diante antes de avançar a continuidade até 3071. Quando finalmente atingir o concurso descoberto naquela execução, reutiliza o resultado já validado.

`remaining` é a distância entre último observado e cursor, mesmo quando algum concurso adiante já possui uma captura. Não é uma contagem de downloads necessários nem uma declaração de completude histórica.

## Persistência

O workspace da SPEC-0020 passa a conter:

```text
sync-state.json         baseline, cursor, próximo concurso de revisão e cooldown
sync-runs/<id>.json     resumo imutável de cada execução concluída
```

Checkpoints são substituídos atomicamente. Avanços maiores que um concurso ou regressões são rejeitados pelo adaptador. A revisão apontada pelo cursor é conferida quanto a identidade e hash ao carregar o estado. Essa verificação não substitui uma auditoria completa de todos os arquivos do intervalo.

## Sequência de uma execução

1. Carregar/validar checkpoint e baseline; aplicar cooldown persistido.
2. Consultar e processar o último resultado, contando um GET.
3. Se o último estiver atrás do cursor, interromper sem regressão.
4. Processar os concursos seguintes em ordem, até o orçamento reservado para avanço.
5. Salvar checkpoint depois de raw, normalização, reconciliação e outcome concluídos de cada concurso.
6. Revisar circularmente a janela recente anterior ao lote, usando o orçamento restante.
7. Gravar resumo com solicitações, resultados, cursor e pendências.

## Janela de revisão

A janela cobre somente concursos posteriores à baseline e já processados pelo fluxo incremental. Ela não compara novamente todos os 2.954 concursos do XLSX. Sua ordem é circular e seu próximo item fica persistido, permitindo distribuir revisões em lotes pequenos.

A janela se move quando o cursor avança; concursos que saem dela deixam de ser verificados automaticamente. Correções mais antigas exigem consulta explícita ou auditoria separada. A revisão preserva correções candidatas e nunca reduz o cursor.

## Parada e recuperação

| Stop reason | Conduta |
|---|---|
| `caught_up` | cursor atingiu o último observado; novas mudanças podem surgir depois |
| `budget_exhausted` | execução válida e limitada; continuar em outra invocação |
| `collection_stopped` | examinar operação que falhou; concurso não é pulado |
| `source_behind_cursor` | investigar resposta atrasada; cursor preservado |
| `cooldown` | nenhuma consulta; aguardar horário registrado |

HTTP 404, 429, 5xx, schema alterado e falha de transporte interrompem o lote. HTTP 429 registra cooldown de 15 minutos, que sobrevive a uma nova invocação. O coletor ainda não interpreta `Retry-After`; a pausa é política interna e não promessa do fornecedor. Não há repetição automática dentro do mesmo lote.

Falha durante revisão mantém o item pendente e os avanços anteriores. Falha ao substituir checkpoint mantém o JSON anterior: a próxima execução pode consultar novamente o concurso já salvo, reconhecendo-o como idêntico antes de avançar. O raw e a revisão são salvos antes do checkpoint; por isso, nunca se declara continuidade sem processamento concluído.

Crash pode deixar receipt sem resumo de lote ou trava residual. Seguir os procedimentos do [coletor unitário](coleta-mega-sena.md). Não editar manualmente o cursor para resolver uma falha. A retomada da sincronização pode fazer nova consulta ao item pendente; o replay offline de um receipt permanece disponível no coletor unitário e não altera sozinho o cursor de sincronização.

## Códigos de saída

- 0: lote concluído, orçamento esgotado ou cooldown respeitado; conferir `stop_reason` e `remaining`.
- 2: coleta interrompida ou fonte atrás do cursor.
- 1: inicialização ausente, baseline inválida, checkpoint corrompido ou falha de armazenamento.

## Validação real da SPEC-0021

Em 20/10/2026, horário de São Paulo (`2026-10-21T01:15:44.066192+00:00`):

- baseline auditada até 2954;
- orçamento de 2 GETs, ambos bem-sucedidos;
- descoberta: 3071, receipt `265fa95a1ff94110aefb4027736495a9`;
- avanço: 2955, receipt `80b893f334aa4a7f93992553e73b27f7`;
- raw 2955: `06529163206f05fcaecdc6dc589eee5026ab2183f4c072bd072d7079e43b0c6d`;
- cursor final 2955, pendência contígua de 116 identificadores até o último observado;
- parada por orçamento, sem varredura em massa.

Uma tentativa anterior sob bloqueio de rede encerrou na descoberta e preservou o cursor 2954. A execução seguinte retomou após liberar o acesso de rede necessário.

## Testes

```powershell
python -m unittest discover -s tests -p test_mega_sena_sync.py -v
```

Os testes não consultam a rede. As mutações da fixture real são exclusivamente cenários controlados dentro de workspaces temporários; não constituem novos resultados históricos.
