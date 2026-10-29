# Ponte histórica no fluxo incremental — SPEC-0028

## Resultado e escopo

ProcessMegaSena/CollectMegaSenaPostgres agora aceitam JSON qualificado sobre head histórico Mega-Sena, por política explícita. O histórico permanece selado em seu contrato/hash; o JSON compatível e mais completo cria uma nova revisão no contrato JSON v1. Divergências entre contratos são preservadas em quarentena, sem mover head ou cursor.

Foram exercitadas somente fixtures existentes em PostgreSQL descartável. Nenhuma requisição a loterias, carga integral, banco operacional, promoção de baseline, publicação ou nova modalidade foi realizada. O piloto continua limitado às linhas 1/2/2954; integrá-lo ao fluxo não remove esse limite do importador.

## Política e fronteiras

Política pura: `app/application/mega_sena_incremental.py`, código `spec-0028-v1`, política `mega-sena-incremental-bridge-v1`. Reutiliza a projeção/comparação da ponte da SPEC-0027, sem copiar seu algoritmo de merge — nenhum merge genérico existe.

| Head | Entrada JSON qualificada | Resultado |
|---|---|---|
| ausente | contrato JSON v1 | new, revisão JSON v1 |
| JSON v1 | conteúdo igual | unchanged, nova observação/evidência sem revisão |
| JSON v1 | conteúdo diferente | correction_candidate; revisões A→B→A preservadas |
| histórico v1 | compartilhado igual e fatos estritamente adicionais | enrichment / correction_candidate, nova revisão JSON v1 |
| histórico v1 | fato compartilhado diferente, perda mista ou apoio parcial sem versão de saída compatível | quarentena, sem revisão nova/head/cursor |
| versão desconhecida | qualquer entrada | canonicalization_conflict; rollback T3, receipt preservado |

Correção de JSON→JSON continua permitida no caminho de fonte JSON CAIXA já qualificado. Isso não autoriza tratar uma divergência entre fontes/contratos como correção automática. Fonte, tipo, catálogo/fingerprint e número oficial continuam conferidos pelos mesmos normalizadores/adaptadores.

Apoio parcial sobre outra versão não usa um hash inventado para satisfazer o trigger. Nesta integração, a receita de saída é JSON v1; se não há enriquecimento comprovado, não se associa observação JSON a revisão histórica. Os JSONs atuais qualificados acrescentam extração/fundo final 0/5; o caso de igualdade de projeções é um limite negativo testado, não um resultado fabricado do importador.

## O que muda e o que permanece

- `persist_mega_sena.py`: fingerprint novo com compatibilidade estrita conhecida, evidência por observação e avanço apenas para observação aceita com revisão.
- `processing.py`: receita nova e recuperação de receitas/comandos legados concluídos, sem reinterpretar receipt antigo silenciosamente.
- `draws.py`: head lido/verificado sob lock; decisão pura; roundtrip SQL de revisão nova; diagnóstico/evidência por observação e quarentena entre contratos.
- Porta de reconciliação recebe evidência explicitamente. O piloto conserva sua política própria e recebe apenas ajuste de assinatura; seu teste do gate anterior passa a provar a integração agora autorizada.

Continuam intactos: normalizadores, canonicalização `lottobrain.mega_sena.result.v1`/`lottobrain.historical.result.v1`, vetor/hash JSON `62755ae7c8057839aa4fcb97c2840afbc6e0a296844f7b02fb6d66f81bbe6477`, storage/raw/receipts, migrations/head `0024_03`, gate de publicação e fluxo legado em arquivos. Nenhuma nova dependência ou tabela foi necessária.

## Compatibilidade de comandos e receitas

Mudar comportamento de processamento exige mudar código/política da receita, não o hash canônico dos números/prêmios. Porém, incrementar essas versões sem compatibilidade faria um comando já confirmado virar conflito ou um receipt antigo gerar interpretação tardia/regressão de head.

A aplicação calcula dois fingerprints conhecidos para o mesmo pedido: atual e anterior da SPEC-0025. Receipt, normalizador, catálogo, contexto de avanço e lease/token continuam incluídos. Apenas se o hash armazenado corresponder exatamente a um deles o comando retorna seu resultado original. A lista de compatibilidade é interna, derivada dos mesmos parâmetros; não é opção de cliente nem bypass geral de idempotência.

Com outra chave, um receipt com receita anterior **concluída**, no mesmo normalizador/canonicalização/catálogo e com observação, recupera essa interpretação. Recebe tentativa de replay, sem reescrever finished_at, revisão ou head. Não se cria receita nova para apresentar o raw antigo como captura posterior. Receipt ainda não interpretado, inclusive quando o gate histórico anterior fez rollback, segue a política nova.

Pedido com outro receipt/intenção/catálogo continua idempotency_conflict. Não há reinterpretação forçada/automática de receipts antigos nesta SPEC; se uma política futura precisar dela, exige intenção e auditoria próprias, não reaproveitar replay como correção.

## Evidência por observação

Payload `mega-sena-incremental-observation-v1`, limitado a **32 KiB de JSON canônico**, contém política, decisão, contrato/hash de entrada, evidência/hash, versão/hash/número da revisão anterior e comparação. Referências do receipt/processing_run conservam raw, captura e versões para reconstrução.

Dois raws com o mesmo resultado mas textos decimais distintos podem gerar uma revisão e duas evidências diferentes. Não atualizar monetary_fact/source_text selado para guardar a segunda captura. Hash de evidência, hash raw e hash de conteúdo têm finalidades diferentes.

Payload acima do limite gera observation_evidence_too_large e rollback T3; bytes/receipt já confirmados permanecem. O erro não é um resultado aceito e não autoriza nova aquisição ou truncamento silencioso. Esse caso exige revisão do limite/entrada, mantendo o raw original. O teto de artefato de 256 KiB continua separado do limite do diagnóstico.

## Continuidade e locks

O fluxo incremental conserva ordem comando → checkpoint (quando solicitado) → receita → draw. A busca de receita legada e a nova receita são obtidas antes do draw. A reconciliação relê/verifica a revisão depois de obter o lock, nunca decide sobre um head anterior ao lock.

Uma observação aceita confirma revisão/filhos/observação/tentativa/passo/cursor juntos. CAS e fencing continuam conferidos no início, UPDATE e commit. Validade da lease não é inferida do tempo da captura nem do sucesso da normalização. Uma falha de T3 ou lease perdida reverte enriquecimento e avanço, conservando captura e revisão histórica anterior.

**Quarentena confirma sem passo.** Antes da integração, candidatos válidos para o normalizador sempre chegavam a uma revisão aceita no reconciliador; a ponte introduziu rejeição semântica posterior. O caso de uso agora verifica revision_id antes de chamar sync.advance. Sem isso, o trigger do passo rejeitaria a quarentena e apagaria seu diagnóstico no rollback.

Replay com a mesma intenção/chave confirmada retorna o resultado anterior sem aplicar novamente cursor. Uma nova lease/intenção pode recuperar a mesma interpretação/receipt para um avanço ainda não realizado, respeitando identidade/fonte e CAS. Cooldown 429 continua em transação independente; 404, transporte e retries SQL não foram convertidos em recaptura automática.

O piloto continua com receita própria, código/política separados e sem checkpoint. A corrida piloto versus incremental, incluindo intenção de avanço, foi testada com duas conexões/claims de identidade. Duas capturas JSON também foram observadas serializando no draw por pg_blocking_pids, não por atraso presumido.

## Provas executáveis

`tests/database/test_incremental_bridge.py`:

| Caso | Prova |
|---|---|
| 01 | histórico→JSON e avanço atômico, dois roundtrips e hashes originais, sem publicação/baseline promovida |
| 02 | conflito confirma quarentena sem step/cursor; outra captura válida depois avança |
| 03 | histórico→A→B→A, replay antigo e apoio XLSX tardio sem regressão |
| 04 | sete pontos de falha T3 revertem enriquecimento/passo/cursor juntos |
| 05–06 | lease perdida no commit e token obsoleto recusam enriquecimento; intenção legítima retoma |
| 07 | duas capturas JSON, lock real observado, uma revisão de enriquecimento e outra observação de apoio |
| 08 | piloto e incremental disputam identidade, com avanço JSON, sem órfão/perda de enriquecimento |
| 09 | fingerprints/receitas legadas simulados com fixture e SQL reais; replay preserva head/tempo; outro pedido conflita |
| 10 | textos financeiros diferentes ficam em evidência separada, sem alterar filhos selados |
| 11–12 | versão desconhecida e evidência grande falham fechado com captura preservada |

O caso 09 simula os metadados/fingerprints anteriores; **não executa binário antigo nem faz downgrade de migrations**. Correções, conflitos, corrupção e leases expiradas nos testes são mutações negativas declaradas, não novos resultados históricos verdadeiros. Erros de COMMIT perdido/429 continuam cobertos pela regressão existente com injeções identificadas, não falha física de infraestrutura.

Testes puros em `tests/test_mega_sena_incremental.py` fixam decisões de política e recusa de versões/apoio parcial. Os testes anteriores de coleta, piloto, integridade, isolamento e UoW permanecem obrigatórios.

## Operação e reprodução

Verificação final em 21/10/2026: **282 testes aprovados** — 194 comuns (277,91 s, três novos) e 88 isolados (441,380 s, 12 SQL novos; 83 PostgreSQL reais + cinco UoW simulados). Log: `.local-postgres/runs/cb1387998f2f4f81bcbeb89206a950f6/server.log`, com desligamento confirmado e postmaster.pid ausente. Serviços PostgreSQL 12/13 existentes preservados; 31 arquivos protegidos mantiveram os hashes, e auditoria Mega-Sena anterior foi reproduzida exatamente/healthy.

```powershell
.venv\Scripts\python -m pytest tests/test_mega_sena_incremental.py -q
.venv\Scripts\python scripts/database/run_integration.py --pg-bin .local-postgres\17.11-3\pgsql\bin
.venv\Scripts\python -m pytest tests --ignore=tests/database -q
```

São comandos distintos: a exclusão de database no pytest não executa a integração. O runner verifica cluster dedicado em `.local-postgres/runs/UUID`, usa ingestor restrito e desliga o PostgreSQL ao terminar. Serviços/bancos existentes não são usados como ambiente de teste.

A CLI SQL opt-in existente usa agora a política nova; suas exigências de DSN/storage/catálogo permanecem. Não há nova CLI de batch nem ativação operacional nesta entrega. Antes de qualquer uso real, revisar configuração, catálogo, proveniência, cobertura e recuperação. [Fluxo/captura e recuperação](persistencia-mega-sena.md) e [piloto/manifesto](piloto-importacao-mega-sena.md) continuam referências complementares.

## Única próxima tarefa recomendada

**SPEC-0029 — Importação histórica completa e auditada da Mega-Sena em ambiente controlado.**

Justificativa: a interoperabilidade comprovada permite especificar/implementar carga retomável dos 2.954 registros qualificados, com manifesto, cobertura reconciliada e sobreposição JSON, sem confundir quantidade de revisões com completude ou promover baseline por inferência. A carga integral não foi executada nesta SPEC; produção e demais modalidades continuam gates posteriores.
