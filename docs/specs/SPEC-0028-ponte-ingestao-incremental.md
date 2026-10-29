# SPEC-0028 — Ponte XLSX/JSON no fluxo incremental Mega-Sena

## Estado

Concluída em 21/10/2026 (America/Sao_Paulo). Critérios/política registrados antes da implementação.

## Objetivo e limites

Permitir que ProcessMegaSena/CollectMegaSenaPostgres interpretem JSON sobre head histórico qualificado, conservando revisões, evidência, replay e continuidade atômica. Sem carga integral, banco operacional, rede de loterias, publicação, nova modalidade, agendamento ou interface. Não alterar raw, relatórios/vetores anteriores, contratos canônicos ou migrations aplicadas.

## Política incremental v1

- JSON v1→JSON v1 mantém correções do fluxo existente, inclusive A→B→A; capturas distintas podem apoiar o mesmo conteúdo e conservam evidência própria.
- Histórico v1→JSON v1 usa a projeção/ponte conservadora já qualificada: compartilhado igual e entrada estritamente mais completa permite nova revisão JSON; divergência/remoção mista gera quarentena. Não sobrescrever revisão histórica.
- Não associar observação JSON a revisão histórica usando hash falso. Apoio parcial que não possa respeitar a versão de saída do processador é recusado em quarentena; atuais JSONs qualificados acrescentam extração/fundo 0/5 e seguem o caminho de enriquecimento.
- Versão desconhecida/catálogo incompatível falha fechado. Não generalizar confiança entre todas as fontes ou transformar divergência entre fontes em correção automática.
- Versionar código/política de processamento sem mudar canonicalização/hashes. Comando legado exatamente compatível retorna resultado original; receipt já interpretado no contrato legado não é reinterpretado/regressado silenciosamente com outra chave.

## Critérios de aceitação

1. JSON incremental enriquece head histórico em SQL real, com roundtrip/hash dos dois contratos e head/publicação corretos; fonte/identidade/catálogo conferidos.
2. Quarentena entre contratos preserva entrada/evidência/diagnóstico, não muda head e não cria passo/avanço; registro de quarentena confirma mesmo quando havia intenção de avanço.
3. JSON→JSON mantém correções serializadas A→B→A, deduplicação, replay antigo e evidência por captura sem modificar filhos selados.
4. Código/política novos e fingerprints explícitos; replay de comando/receipt legado concluído mantém observação, head e finished_at originais. Chave com outro receipt/intenção/catálogo continua conflito.
5. Ordem de locks comando→checkpoint→receita→draw preservada no fluxo incremental. Concorrência com piloto histórica e duas interpretações reais deve convergir sem órfãos/perda de enriquecimento; não duplicar a ponte por cópia.
6. Comprovar revisão/observação/passo/cursor na mesma transação e rollback em falha/lease expirada/perdida; replay com nova lease/intenção pode concluir depois. Cooldown 429 independente e nenhuma repetição HTTP automática.
7. Diagnóstico/evidência por observação versionados e limitados; arquivo/receipt continuam autoridade da entrada. Nenhuma alteração destrutiva de hashes ou triggers.
8. Regressão comum/PostgreSQL completa, incluindo cenários anteriores de piloto e ingestão; atualizar o teste do gate antigo para a integração agora autorizada. Dados brutos, relatórios e auditorias anteriores intactos.
9. Documentar operação/limites, aprendizados e uma única próxima tarefa; não executar a carga histórica completa como efeito colateral.

## Estratégia

Política incremental pura na aplicação; reconciliação SQL existente recebe decisão/evidência explícitas. Reutilizar leitura/escrita relacional, unidade de trabalho, disputa de alias, armazenamento e ponte de projeção. Testes só em cluster descartável sob ingestor restrito, com fixtures reais e mutações negativas declaradas.

## Entregas e comprovação

- Política incremental pura, código `spec-0028-v1` e política `mega-sena-incremental-bridge-v1`; ProcessMegaSena/CollectMegaSenaPostgres usam a ponte sem mudar o contrato JSON v1 ou seus hashes.
- Head histórico relido/verificado sob lock; enriquecimento gera revisão JSON, compartilhado divergente confirma quarentena. Nenhum merge genérico, recanonicalização destrutiva ou suporte com hash falsificado.
- Evidência/diagnóstico versionados por observação, com hash próprio e limite de 32 KiB; textos novos de captura não alteram filhos selados.
- Compatibilidade estrita com fingerprints/receitas anteriores concluídas; replay mantém revisão/head/finished_at. Outro pedido com a mesma chave continua conflito.
- Correções histórico→JSON→A→B→A, replay antigo, sete pontos de rollback, token obsoleto/perda de lease, concorrência piloto/incremental e serialização observada em duas conexões comprovados. Quarentena não chama sync.advance; uma captura válida posterior pode concluir o avanço.
- **282 testes aprovados**: 194 comuns (277,91 s; três novos) e 88 no runner isolado (441,380 s; 83 PostgreSQL reais + cinco UoW simulados; 12 SQL novos). Os 27 cenários anteriores de ingestão e os 13 do piloto permanecem, atualizando o teste 13 do gate antigo para provar a integração autorizada.
- Hashes dos **31 arquivos protegidos** inalterados: raw, relatórios JSON anteriores e workspace de coleta. Auditoria Mega-Sena anterior reproduzida exatamente/healthy; vetores e relatório da SPEC-0026 preservados pela suíte comum.
- Compileall, links locais e whitespace verificados; aviso CRLF de requirements.txt é preexistente, arquivo não editado. Nenhuma nova dependência, migration, tabela, baseline carregada, publicação ou coleta de rede.
- Cluster final `.local-postgres/runs/cb1387998f2f4f81bcbeb89206a950f6`, desligamento confirmado no server.log e postmaster.pid ausente; serviços PostgreSQL 12/13 existentes preservados.
- [Operação, política e provas](../engineering/ponte-ingestao-incremental.md); aprendizados L-151…L-156, README e roadmap atualizados.

## Limites e decisões conservadoras

O caminho JSON→JSON mantém correções da fonte qualificada; isso não declara confiança universal em qualquer fonte do mesmo formato. Divergência entre contratos não se resolve automaticamente. Apoio parcial sem saída compatível vai para quarentena; versões desconhecidas e evidência acima do limite falham fechado, com receipt preservado.

O teste de upgrade simula fingerprints/metadados antigos com fixture e SQL reais, não executa binário anterior nem downgrade. Falhas físicas de rede/disco, carga completa, outras modalidades, promoção de baseline e produção não foram exercitadas. O importador piloto mantém sua seleção limitada; o novo fluxo não o transforma em batch integral.

## Única próxima tarefa recomendada

**SPEC-0029 — Importação histórica completa e auditada da Mega-Sena em ambiente controlado.**

Justificativa: com a interoperabilidade comprovada, implementar/provar carga retomável dos 2.954 registros qualificados, reconciliando cobertura por concurso e sobreposição JSON. Não inferir completude de contagem de revisões nem promover baseline sem evidência/fluxo próprio. Não executada nesta SPEC.
