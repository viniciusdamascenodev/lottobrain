# SPEC-0024 — Primeiras migrations PostgreSQL e testes de integridade

## Estado e objetivo

Concluída em 21/10/2026 (America/Sao_Paulo). Critérios registrados antes da implementação.
Transformar o recorte de ingestão da SPEC-0023 em DDL versionado e verificável em PostgreSQL 17 isolado. Não acessar os serviços PostgreSQL 12/13 existentes na máquina.

## Recorte

- Catálogo: loteria, escopo, regra, série, componente, faixa e fonte.
- Evidência: execução, tentativa HTTP, artefato, captura, receita/tentativa de interpretação, observação e problema de validação.
- Concurso: identidade, referências externas, revisão selada, números, atributos, faixas e fatos monetários.
- Continuidade: baseline, checkpoint, lease e passos contíguos.
- Alembic, dependências separadas do legado, privilégios por papel e testes PostgreSQL reais.

Agendas/extensões, publicação/decisões/outbox, API, ORM/repositórios, importação e canonicalização relacional ficam fora. Não conectar o coletor ao banco. Não modificar históricos nem workspace de coleta. Não instalar serviço do Windows, alterar bancos existentes ou cadastrar usuários reais.

## Critérios de aceitação

1. Upgrade de banco vazio, segunda execução sem efeito e rollback somente de schema vazio, preservando evidência em banco preenchido.
2. Catálogo estrutural das seis loterias exercitado com definições reais existentes, sem seed automático de resultados.
3. DB-01, DB-03 (vínculo/unicidade), DB-06 a DB-16 e DB-35 comprovados no recorte físico.
4. DB-17/18, DB-24 a DB-27 e DB-31 apenas quanto às garantias SQL; não declarar pronto o comportamento de repositórios/HTTP/importação.
5. Commit rejeita revisão incompleta, regra incompatível, números inválidos, alteração tardia e cursor sem evidência contígua.
6. Nada de SQLite como substituto; testes não usam bancos existentes, registram versão real e falham quando a configuração de integração exigida estiver ausente.
7. Privilégios de ingestão sem superuser/DDL/publicação/exclusão de evidência. Segredos não entram no repositório.
8. Documentar cobertura, limites, comandos reproduzíveis, recuperação e única próxima tarefa.

## Verificação planejada

Testes unitários existentes, auditoria offline idêntica e hashes dos seis históricos antes/depois. Testes de integração em base descartável dedicada com dados reais das fixtures; entradas inválidas são mutações explícitas de teste, nunca dados operacionais. Canonicalização relacional/vetores das seis modalidades permanecem gate obrigatório antes da importação, não serão simulados com hashes inventados.

## Entregas e resultado

- `0024_01` catálogo; `0024_02` evidências/resultados/selo; `0024_03` continuidade/lease: 27 tabelas no schema `lb`, sem seed operacional.
- [Migrations e operação](../database/migrations-ingestao.md): ambiente, permissões, comandos, decisões físicas, recuperação e limites.
- [Verificação por DB-ID](../database/verificacao-spec-0024.md): 31 testes PostgreSQL 17.11 aprovados, mais 148 testes existentes; cenários parciais e futuros não foram marcados como concluídos.
- Teste das seis loterias e 20 versões existentes no mesmo modelo. Não há tabelas exclusivas da Mega-Sena.
- Upgrade, no-op e downgrade vazio comprovados; reversão preenchida recusada sem mudar dados/ledger. Papel ingestor não publica/edita catálogo/apaga evidência; auditoria é somente leitura.
- Auditoria SPEC-0022 reproduzida exatamente; seis hashes raw inalterados. Serviços PostgreSQL 12/13 e alterações preexistentes preservados.
- Aprendizados L-121…L-129 registrados para as próximas tarefas.

O banco foi exercitado **somente em clusters descartáveis**, desligados ao final. Não houve importação histórica, nova coleta de loteria, banco operacional nem conexão do coletor aos repositórios SQL. Binários/dependências foram obtidos no ambiente isolado para viabilizar os testes, sem alterar instalações existentes.

## Ajustes de escopo e pendências controladas

A implementação física selecionou o recorte T1–T3/checkpoint, sem antecipar agendas, extensões, auditoria administrativa, publicação ou outbox. O gate de publicação é um CHECK explícito enquanto T5 não existe. Baseline referenciada permanece diferente de carga materializada.

Vetores canônicos relacionais serão qualificados com o mapper, antes da carga; nesta etapa testes identificam explicitamente o hash semântico legado. Testes físicos não substituem os cenários de concorrência/retry/UoW nem comprovam integração de HTTP/storage. O [relatório](../database/verificacao-spec-0024.md) atribui todos os 37 DB-IDs sem apresentar cobertura parcial como conclusão do contrato inteiro.

## Próxima tarefa recomendada

**SPEC-0025 — Persistência transacional da Mega-Sena: repositórios e unidade de trabalho.**

Justificativa: conectar o primeiro fluxo ao schema já comprovado, com identidade/revisão/idempotência/lease, testes de duas conexões e falhas controladas, antes de mover históricos. Sem carga em massa ou publicação nesse incremento. Não executada nesta tarefa.
