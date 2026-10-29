# Operação manual da coleta Mega-Sena

Para sincronizar uma sequência de concursos com checkpoint e orçamento, usar o [guia da SPEC-0021](sincronizacao-mega-sena.md). Este comando continua disponível para coleta individual e replay.

## Execução

Na raiz do repositório, Python 3.12, sem dependência adicional para este fluxo:

```powershell
python -m app.interfaces.collect_mega_sena --contest 2954
```

Para consultar o último resultado publicado, omitir `--contest`. Cada execução faz um único GET, sem repetição automática e sem consultas paralelas. O endpoint é fixo; a CLI não aceita URL externa.

## Workspace

Por padrão, os arquivos ficam em `data/collections/mega_sena/`:

```text
artifacts/<sha256>.json           bytes originais da resposta limitada
receipts/<receipt_id>.json        metadados da captura
outcomes/<receipt_id>-<id>.json   resultado de cada processamento
revisions/<concurso>.json         revisões candidatas, preservando anteriores
.collection.lock                 trava exclusiva durante a execução
```

O local pode ser selecionado com `--workspace`. Não usar a pasta histórica `data/raw`. O workspace é um adaptador local de desenvolvimento, com execução serial; a migração para PostgreSQL e object storage usará as portas definidas na aplicação.

Os artefatos não são sobrescritos pelo programa. O arquivo de histórico de revisões é substituído atomicamente após preservar todas as revisões anteriores. Isso não equivale a proteção WORM no sistema operacional ou transação distribuída. Backup e recuperação produtivos serão definidos na fase de infraestrutura.

## Resultados

| Outcome | Significado |
|---|---|
| `new` | primeiro candidato observado desse concurso neste workspace |
| `unchanged` | conteúdo normalizado igual à última revisão |
| `correction_candidate` | nova revisão candidata com diferença; anterior preservada |
| `replayed` | captura antiga já processada, sem rollback de revisão posterior |
| `quarantined` | resposta arquivada, mas não elegível para reconciliação |
| `failed` | falha de transporte ou armazenamento; não há conclusão de coleta |

`new` não significa descoberta absoluta: significa novo no repositório local de revisões. A integração com a carga histórica será feita explicitamente em tarefa de sincronização.

Saída é JSON em stdout. Código de saída: 0 para processamento válido, 2 para quarentena e 1 para falha. Nada é publicado na interface existente.

## Retomada sem rede

```powershell
python -m app.interfaces.collect_mega_sena --replay c6749b775d7144cd9c92f6251f37e131
```

Usar o receipt retornado pela execução no mesmo workspace. O replay confere tamanho e hash dos bytes salvos e reutiliza o instante original de captura.

Se houver interrupção após salvar o raw, o receipt permite retomar quando tiver sido gravado. Raw sem receipt é um órfão recuperável por inspeção, não um concurso importado. Interrupção entre reconciliação e outcome é recuperada por replay idempotente. Falha de rede antes de receber um corpo não produz artefato; é retornada como falha em stdout.

Uma trava deixada por encerramento forçado precisa ser examinada pelo operador: confirmar que o PID registrado não está executando esta coleta antes de remover o arquivo de trava exato. O programa não remove travas por idade, evitando concorrência acidental.

## Segurança e limites

- HTTPS com verificação de certificado.
- Host/path fixos e redirects desabilitados.
- Timeout de socket de 15 segundos, tamanho máximo de 256 KiB e conferência de Content-Length quando presente.
- Não persiste cookies, tokens ou headers completos.
- HTTP não 200 é arquivado em quarentena; 429 não é repetido automaticamente.
- JSON inválido, mudança de schema, identidade divergente e dados incompletos ficam fora do histórico candidato válido.
- Lock obrigatório para escrita no adaptador local.

## Verificação

```powershell
python -m unittest discover -s tests -p test_mega_sena_collection.py -v
```

O teste usa fixture oficial formatada e mutações controladas para cenários de erro. Testes não acessam a rede. O hash do raw e o hash semântico cumprem funções distintas: o primeiro audita os bytes; o segundo identifica diferenças do conteúdo promovido ao domínio.
