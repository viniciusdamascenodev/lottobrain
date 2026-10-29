# Aprovação da baseline e início seguro — SPEC-0030

## Fluxo implementado

`ActivateMegaSenaBaseline` recebe um `BaselineRequest` imutável: chave de comando, chave da importação histórica, hash esperado do plano e referência explícita de aprovação. Fonte, loteria, intervalo, stream e cursor não são parâmetros livres.

1. Ler o manifesto e a localização do raw persistidos na importação, sem usar uma cópia editável de relatório da documentação.
2. Ler/verificar bytes e reconstruir o plano fora da transação SQL; conferir o hash esperado antes de qualquer INSERT.
3. Abrir snapshot REPEATABLE READ, serializar a chave e procurar a aprovação anterior. Pedido incompatível na mesma chave é conflito; pedido idêntico retorna a decisão original, sem reaprovação ou reset de cursor/tempos.
4. Para uma aprovação nova, qualificar o catálogo JSON atual e serializar o destino. Recusar checkpoint anterior, inclusive de outro stream. Não usar `max(concurso)` ou um candidato adiantado como fronteira.
5. Reauditar o conteúdo relacional/evidência dos 2.954 registros no mesmo snapshot. Exigir estado completed **e** qualified=true. Fonte histórica posteriormente bloqueada não apaga sua evidência; destino JSON precisa estar qualificado agora.
6. Inserir baseline loaded nova, vínculo/auditoria e checkpoint JSON na mesma transação. Qualquer falha reverte os três. Não atualizar uma baseline referenced nem manter registro parcial como se a aprovação tivesse terminado.
7. Retornar identidades e fronteira de criação. Não obter lease, executar HTTP, criar sync_step, agendar job ou publicar dados como efeito colateral.

## Estados e replay

O retorno `initial_cursor=2954/next_contest=2955` descreve a criação, não é uma leitura do cursor atual. Quando o checkpoint já avançou, repetir a aprovação retorna essa mesma decisão e não o faz regredir.

Replay não renova autorização: pode recuperar a decisão passada mesmo que o catálogo JSON tenha sido bloqueado depois. As novas coletas e a aquisição de lease pelo fluxo suportado devem qualificar o catálogo atual. Recuperar o registro de uma aprovação não autoriza usar uma lease antiga para ignorar bloqueios.

Concorrência usa locks de comando/destino e unicidade. `INSERT ... ON CONFLICT DO NOTHING` no vínculo permite que um snapshot obsoleto gere conflito de serialização; a unidade de trabalho reaplica apenas transações abortadas conhecidas, com limite de três tentativas. Não repetir automaticamente um commit de resultado ambíguo: o operador/chamador repete a mesma chave e recupera a decisão já confirmada.

Storage e SQL não formam uma transação distribuída. Bytes são conferidos antes de abrir a transação; não se impede uma remoção externa posterior. Reauditoria/replay detectam evidência ausente/corrompida; retenção e backup do storage precisam de operação própria antes de produção.

## Verificação

Os testes da nova funcionalidade usam cluster descartável e papéis separados. O cenário completo importa o XLSX aprovado, mantém uma baseline referenced anterior, registra candidato real 3071 e inicializa exclusivamente em 2954. Interrompe cada INSERT, recusa qualidade/estado inválidos, disputa a mesma intenção entre dois chamadores e simula perda de resposta depois do COMMIT.

A passagem ao concurso 2955 usa os bytes JSON reais já arquivados localmente (SHA `06529163206f05fcaecdc6dc589eee5026ab2183f4c072bd072d7079e43b0c6d`). O candidato 3071 também usa arquivo local (`7a4d0c4e3decee29a652b5d9a417c97b10c88daebd975b00db056ca0bec701e8`). O transporte é dublê de teste: não há GET novo nem alegação de nova captura original.

Esses dois arquivos foram copiados byte a byte para `tests/fixtures/mega_sena_api_2955.json` e `mega_sena_api_3071.json`, com os mesmos hashes. Os testes não dependem do diretório de coleta ignorado pelo Git e continuam reproduzíveis em checkout novo. Não se editou o raw ou o arquivo legado para montar as fixtures.

Falha depois do step reverte revisão/observação/step/cursor juntos, conservando o receipt. A repetição legítima avança 2954→2955, e replay da aprovação não reseta checkpoint. Todas as mutações de bloqueio, estado inválido, alias e perda de resposta são testes identificados, não resultados operacionais fictícios.

## Reprodução e dependências

### Verificação final — 25/10/2026

**334 testes distintos aprovados**: 235 comuns (202,79 s) e 99 no runner completo (2.080,574 s: 91 PostgreSQL reais + oito dublês de infraestrutura/estado). Outros seis casos foram reexecutados com as constraints finais, incluindo a aprovação sobre carga integral, e passaram em 1.110,716 s; são repetição de casos já incluídos nos 99.

Resultado SQL: uma baseline loaded histórica, uma referência anterior preservada como referenced, um vínculo, um checkpoint JSON e um step para 2955. O candidato 3071 ficou separado do cursor. A auditoria da aprovação verificou 2.954/2.954, sem problemas; seu hash foi `6406a246210b3b55116dfcb30a343359969eac59f9d978bef21708304dd0efa9`. [Relatório novo com contexto/identidades](../data/mega-sena-baseline-spec-0030.json).

Log completo `.local-postgres/spec0030-integracao-20261025.log`, cluster `883b1ebac360425cb013c13d3e26a462`. Log focal final `.local-postgres/spec0030-ativacao-final-20261025.log`, cluster `7cc4e8e0f83d4ce0a75fbe7a1e1190f0`. Ambos terminaram com saída 0, shutdown confirmado e postmaster.pid ausente. O primeiro runner começou antes do último reforço de FKs/ator/arrays, razão da reexecução integral da nova funcionalidade no segundo cluster. Os demais casos da regressão criam seus próprios bancos no head final.

O smoke preliminar passou quatro casos; um quinto foi acrescentado e passou nas duas execuções maiores. A primeira tentativa do smoke esperava RaiseException para o trigger imutável, que corretamente emitiu CheckViolation; corrigiu-se a expectativa do teste, não a proteção. Todos os clusters preliminares também foram desligados. Logs de tentativas preservados, sem contá-las como aprovação adicional.

Os 70 arquivos protegidos continuaram idênticos: seis raws, 30 documentos de dados anteriores, nove fontes de migrations anteriores, nove fixtures anteriores e 16 arquivos da coleta local. Auditoria anterior: healthy, reproduzida exatamente. Serviços PostgreSQL 12/13 existentes não foram usados nem interrompidos. Não houve nova dependência, atualização de dataset até hoje ou ativação operacional.

Sem novas dependências. A suíte pura usa requirements-test; testes/infraestrutura de banco também exigem requirements-database e binários PostgreSQL 17 qualificados. Instalar dependências/provisionar papéis é decisão explícita de ambiente, não efeito do import de um módulo.

```powershell
.venv\Scripts\python -m pytest tests/test_baseline_activation.py -q
.venv\Scripts\python scripts/database/run_integration.py --pg-bin .local-postgres\17.11-3\pgsql\bin --test-pattern test_baseline_activation_smoke.py
.venv\Scripts\python scripts/database/run_integration.py --pg-bin .local-postgres\17.11-3\pgsql\bin --test-pattern test_baseline_activation*.py
.venv\Scripts\python scripts/database/run_integration.py --pg-bin .local-postgres\17.11-3\pgsql\bin
.venv\Scripts\python -m pytest tests --ignore=tests/database -q
```

`--test-pattern` é somente filtro de diagnóstico do runner; sucesso de um filtro não equivale à regressão completa. O runner preserva log/dados locais ignorados e encerra o cluster; não usar bancos ou serviços instalados como alvo.

Não há CLI operacional de ativação ou worker automático nesta SPEC. O caso de uso está disponível para a composição explícita com UoW/storage, e a prova é executada pelos testes. Essa separação evita transformar um teste de inicialização em ativação de um ambiente real sem catálogo, credenciais e aprovação próprios.

## Limites e única próxima tarefa recomendada

**SPEC-0031 — Orquestração PostgreSQL da sincronização limitada Mega-Sena.** Reutilizar a baseline/checkpoint aprovados para descoberta, avanço contíguo e revisão limitada, com orçamento de requisições, espaçamento, cooldown e recuperação por comando. A orquestração em arquivos existente não deve ser apontada para SQL por adaptação implícita. Não incluir agendamento, ativação operacional, publicação ou novas modalidades nessa recomendação. Não executada nesta etapa.
