# SPEC-0029 — Importação histórica completa Mega-Sena

## Estado

Concluída em 25/10/2026 (America/Sao_Paulo), incluindo as correções da revisão. Critérios registrados antes da implementação; importação comprovada exclusivamente em PostgreSQL descartável e controlado, sem banco operacional.

## Objetivo e limites

Importar os 2.954 registros do XLSX já qualificado e comprovar retomada, cobertura por concurso e convivência com JSON 2954. Sem banco operacional, nova coleta, publicação, agendamento, outras loterias ou promoção de baseline. Raw, relatórios/vetores anteriores, contratos canônicos e migrations aplicadas devem permanecer intactos.

## Critérios de aceitação

1. Plano completo limitado ao raw SHA aprovado, 2.954 linhas/concursos 1–2954, período 11/03/1996–20/12/2025 e normalizador existente; não ampliar silenciosamente o piloto de três linhas.
2. Manifesto compacto/versionado fixa input, código/política, intervalo e hash dos registros/evidências. Preparar/reconstruir fora de SQL e evitar custo quadrático de reserializar o plano para cada linha.
3. Raw integral arquivado; registro legado idempotente e honesto quanto ao horário original desconhecido. Ledger por localizador e transação por registro; seleção/intenção incompatível com a mesma chave continua conflito.
4. Interromper a carga real, auditar cobertura parcial como incompleta e retomar somente pendências a partir de manifesto/bytes persistidos, sem depender do arquivo original/objetos anteriores. Replay completo não duplica observações/revisões nem regride head/tempos.
5. Auditoria SQL em snapshot consistente reconstrói hashes relacionais e verifica identidade, normalização/valores, evidência, observação, comando/receita, estados e selagem; reportar ausentes, inesperados, duplicados, quarentenas e inconsistências. Contagem de revisões não é prova de cobertura.
6. Preservar JSON 2954 pré-existente como revisão apoiada; conferir input histórico e revisão apoiada em seus próprios contratos. Histórico completo permanece atualizável pelo fluxo incremental qualificado.
7. completed exige cobertura auditada total; falha/quarentena não promove sucesso. Auditoria é somente leitura e não altera relatório anterior. Não criar sync_step/checkpoint/baseline/publicação como efeito colateral.
8. Reutilizar ponte, unidade de trabalho, storage e SQL de escrita/registro; extrair abstrações somente com consumidores concretos. Limitar I/O por blocos e usar leitura relacional em lote para auditoria, sem COPY destrutivo ou constraints desabilitadas.
9. Provar carga integral em PostgreSQL descartável sob ingestor restrito, regressão comum/SQL, hashes protegidos, auditorias anteriores e desligamento do cluster. Evidência de execução nova deve ser identificada, sem dados fictícios operacionais.
10. Documentar operação/limites, cobertura real, aprendizados e uma única próxima tarefa, sem executá-la.

## Decisões de verificação

Um cenário SQL integral combina sobreposição JSON, interrupção, auditoria parcial, restauração, auditoria completa e replay. Casos menores/negativos e regressões anteriores permanecem separados. O relatório final não usará UUIDs/relógios como hash de cobertura; referências locais da execução documentam o ambiente descartável. Baseline continua gate próprio, mesmo com carga auditada completa.

## Fechamento após revisão — 25/10/2026

Antes de encerrar, corrigir e comprovar dois pontos identificados na revisão:

- Estado terminal persistido não será reescrito nem substituído apenas no retorno. A qualificação do snapshot atual é independente do estado de encerramento do run; nova auditoria pode reprovar uma execução encerrada sem reescrever sua história/finished_at.
- Leitura da evidência histórica usa manifesto/fingerprint registrados no receipt, validando o vínculo com o request do run. Não depende da aprovação/configuração atual da fonte. Novas escritas e retomadas continuam exigindo catálogo atual qualificado e intenção compatível; auditar não equivale a autorizar importação.

Adicionar regressões negativas do avaliador de cobertura e testes SQL para evolução/bloqueio do catálogo e estados terminais. Só marcar concluída após nova execução integral, regressão comum/SQL, conferência dos arquivos protegidos e encerramento confirmado do cluster descartável. A execução anterior sem resultado final recuperável não é evidência de aprovação.

## Resultado e critérios atendidos

- **1–2 — Plano e universo:** 2.954 registros, concursos 1–2954, 11/03/1996–20/12/2025, raw aprovado de 221.261 bytes. Manifesto compacto/cacheado e restauração conferidos; o piloto segue limitado a três linhas.
- **3–4 — Evidência e retomada:** arquivo integral arquivado com proveniência legada explícita; interrupção após 100 commits, auditoria com 2.854 ausentes, nova instância reconstruída de bytes/manifesto persistidos, retomada integral e replay sem duplicação/alteração de finished_at. Reutilização incompatível de chave recusada.
- **5–7 — Cobertura e convivência:** 2.954/2.954 verificados; zero ausentes, inesperados, duplicados, quarentenas ou inconsistências. 2.953 novas revisões históricas e um apoio ao JSON 2954 já existente. Correção JSON posterior preserva a evidência histórica. Nenhuma baseline, checkpoint, sync_step ou publicação criada no cenário de carga. Auditoria permanece válida após evolução/bloqueio do catálogo, enquanto retomadas incompatíveis são recusadas. Estado terminal devolvido corresponde ao persistido.
- **8–9 — Implementação e regressão:** ponte/UoW/storage/escrita compartilhados; verificação por blocos e reconstrução em seis consultas de conteúdo. **312 testes distintos aprovados:** 219 comuns, 90 no runner isolado (85 PostgreSQL reais + cinco dublês UoW) e três dublês de estado terminal executados separadamente. Os 69 arquivos protegidos permaneceram idênticos; auditoria local anterior reproduzida exatamente/healthy. Clusters desta retomada desligados, com postmaster.pid ausente e serviços PostgreSQL 12/13 existentes preservados.
- **10 — Documentação:** operação, limites, relatório novo, roadmap e aprendizados L-157–L-161 atualizados. A próxima tarefa é apenas recomendada.

O relatório positivo de cobertura foi idêntico em dois clusters independentes. A primeira suíte desta retomada terminou com erro no próprio teste de alteração de configuração (fetchall após UPDATE sem RETURNING); foi corrigido no teste e toda a integração foi repetida, **90/90, saída 0**. Essa tentativa com erro não foi contada como aprovação. Os três testes de estado foram separados da suíte comum para manter opcionais as dependências SQL e passaram em execução própria; próximas execuções do runner também os descobrem.

## Evidências e limites finais

- [Relatório novo de execução e cobertura](../data/mega-sena-cobertura-spec-0029.json), derivado do SQL, sem sobrescrever relatórios anteriores.
- [Operação, reprodução e limites](../engineering/importacao-completa-mega-sena.md).
- Log aprovado: `.local-postgres/spec0029-fechamento-20261025-reexecucao.log`; cluster `.local-postgres/runs/3fa44c4a11f4482dbae1d617e2fd0fe1`, PostgreSQL 17.11, desligamento confirmado no server.log.
- Hash do manifesto de registros esperado/observado: `9c963b7f327ea52482a83d86433ad2e48c990838be1f1ebee6ffa1e175c298e5`.

Não houve nova coleta, atualização até a data atual, carga operacional, importação completa de outras modalidades, migration/dependência nova, alteração de raw/contratos/vetores anteriores ou ativação de sincronização/publicação. Dados físicos e logs de teste ficam locais/ignorados, sem servidor descartável ativo. As mudanças preexistentes no repositório foram preservadas.

## Única próxima tarefa recomendada

**SPEC-0030 — Registro de baseline auditada e inicialização segura da sincronização Mega-Sena.** Converter cobertura comprovada em autorização explícita de continuidade entre fontes histórica/JSON, exigindo encerramento completed e auditoria atual qualificada, sem alterar baseline já referenciada. Não executada nesta etapa.
