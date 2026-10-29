# SPEC-0025 — Persistência transacional da Mega-Sena

## Estado

Concluída em 21/10/2026 (America/Sao_Paulo). Critérios registrados antes da implementação.

## Objetivo e recorte

Implementar portas/casos de uso e adaptadores PostgreSQL sobre o schema da SPEC-0024, para uma captura Mega-Sena atravessar T1–T3 com evidência, identidade, revisões, idempotência e avanço opcional atômico. O fluxo em arquivos permanece intacto; SQL é opt-in e exige catálogo/baseline previamente qualificados. Não importar históricos, provisionar banco operacional, consultar loterias na rede, agendar, publicar, criar API/UI/autenticação ou novos coletores.

## Critérios de aceitação

1. Unidade de trabalho libera a conexão em sucesso, falha do corpo, commit e rollback; repositórios não fazem commit nem I/O externo.
2. T1 confirma antes do GET; PUT e parsing ficam fora de transação SQL; T2 preserva resposta HTTP inclusive erro e distingue falha sem corpo.
3. Receitas e comandos possuem identidade/fingerprint: repetir a mesma chave não duplica efeitos; chave com outro pedido é conflito explícito.
4. Receipts distintos podem produzir observações distintas e uma só revisão; mesma receita antiga é replay e não regride head.
5. Corridas de identidade/conteúdo usam duas conexões independentes, com coordenação por eventos/locks, não sleeps para presumir ordem. Não deixar draw órfão ao perder UNIQUE.
6. Correções têm números serializados; A→B→A mantém três revisões; publicação permanece bloqueada.
7. Revisão/observação/passo/cursor confirmam juntos. Cursor usa CAS/lease/token vigentes; candidato adiante não permite salto; perda de lease conserva captura, sem avanço.
8. 429 persiste cooldown de 15 minutos em transação própria; não repetir HTTP automaticamente. Retry limitado é somente da transação SQL com evidência já arquivada.
9. Mapper relacional Mega-Sena possui versão, vetor real/hash fixado, roundtrip e ordinais de extração explícitos. Não renomear hashes legados nem declarar prontos vetores das demais modalidades.
10. Testar sob login ingestor não proprietário/superuser, manter 31 testes SQL e suíte existente, auditoria e hashes raw anteriores.
11. Documentar comandos, recuperação, limites, cobertura DB-ID, aprendizados e única próxima tarefa.

## Decisões de execução

- Nenhuma migration 0024 aplicada será reescrita; necessidade de DDL adicional deve ganhar nova revisão.
- Identidades novas disputam UNIQUE dentro de savepoint: perdedor desfaz seu agregado e recarrega vencedor sob lock.
- Locks: comando → checkpoint (se houver) → receita → draw → filhos. Nenhum caminho de draw tenta obter checkpoint depois.
- Comando de aquisição interrompido sem receipt não repete GET silenciosamente: devolve estado em andamento/ambíguo e exige nova intenção explícita.
- Estado local de coleta não será migrado automaticamente. Baseline/catálogo SQL são pré-requisitos, não criados pelo coletor.

## Verificação planejada

Fixtures reais disponíveis, mutações negativas identificadas como teste; PostgreSQL 17.11 descartável e sem rede de loterias. Injetar falhas antes/depois dos pontos de confirmação, testar retomada com a mesma chave e executar duas conexões coordenadas. Relatórios anteriores e dados brutos devem permanecer byte a byte iguais.

## Entregas e comprovação

- Portas/DTOs e casos de uso sem driver em `app/application`; adaptadores separados por responsabilidade em `app/infrastructure/postgres`, com unidade de trabalho e storage local por hash.
- Fluxo SQL manual opt-in e replay por receipt, com configuração explícita; coletores em arquivos preservados.
- Reconciliação com savepoint/UNIQUE, head lido sob lock, conteúdo selado, sem publicação automática, A→B→A e replay antigo rastreáveis.
- Avanço opcional de checkpoint na mesma transação de observação/revisão; CAS, lease e fencing inclusive no commit.
- Fingerprints de comando/receita, retorno idempotente após commit ambíguo, retry limitado só de SQL abortado e cooldown independente.
- Vetor relacional JSON Mega-Sena 2954 e leitura de verificação com hash reproduzível; legados não renomeados.
- **220 testes aprovados**: 157 na suíte comum; 58 PostgreSQL reais (31 anteriores + 27 casos de uso); cinco de ciclo de vida de UoW com conexão simulada.
- Auditoria anterior reproduzida exatamente e seis hashes raw inalterados; nenhum GET de loteria, importação ou banco operacional criado. Serviços PostgreSQL existentes intocados; cluster descartável desligado.
- Nenhuma migration ou dependência nova necessária. Executor de testes recebeu ajuste de recursos/prazo de shutdown, mantendo fsync habilitado.

Operação/recuperação: [persistência Mega-Sena](../engineering/persistencia-mega-sena.md). Evidências, limites e matriz DB-ID: [verificação SPEC-0025](../database/verificacao-spec-0025.md). Aprendizados L-130…L-138 registrados.

## Limites controlados

Casos de concorrência usam duas conexões reais e coordenação por estado; transporte/429/404/correções e perdas de resposta são simulações de teste declaradas, sem inventar dados históricos operacionais. Falha de disco/rede física e ambiente de produção não foram exercitados.

Aquisição sem receipt confirmado não é repetida silenciosamente: pode haver GET/PUT ambíguo/órfão e exige investigação/nova intenção explícita. Não existe ainda reparador de storage SQL, importador, provisionamento de catálogo/baseline operacional ou scheduler/batch SQL. CLI não oferece avanço; a porta da aplicação é exercitada nos testes e exige checkpoint aprovado.

O esquema permanece compartilhado pelas seis loterias, mas o mapper/processador entregue é do JSON Mega-Sena. XLSX Mega-Sena, demais modalidades, fontes adicionais, T4/T5, audit_event/outbox, API e frontend mantêm seus gates; não foram certificados por analogia.

## Próxima tarefa recomendada

**SPEC-0026 — Qualificação da importação histórica: mapeamentos e vetores das seis loterias.**

Justificativa: antes de carregar os históricos, provar a representação fiel de cada fonte/regra, incluindo identidade, estados de ausência, valores financeiros, séries e símbolos. Entregar vetores/hashes e plano de importação auditada, sem carga em massa nesse incremento. Não executada nesta tarefa.
