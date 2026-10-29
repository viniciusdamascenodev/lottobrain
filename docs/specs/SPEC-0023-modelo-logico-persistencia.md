# SPEC-0023 — Modelo lógico e contrato de persistência PostgreSQL

## Estado

Concluída em 21/10/2026 (America/Sao_Paulo). Critérios registrados antes do detalhamento.

## Objetivo

Converter as invariantes do domínio e do fluxo auditado em modelo lógico relacional e contratos transacionais implementáveis. Preparar a implementação das migrações e adaptadores PostgreSQL.

## Escopo

- Identidade, chaves, relacionamentos, valores tipados e escopos financeiros.
- Separação entre bytes raw, captura, interpretação, revisão e publicação.
- Baseline, continuidade, revisão e checkpoint.
- Garantias de banco, validações de aplicação e auditorias periódicas.
- Concorrência, idempotência, limites de transação e recuperação.
- Contratos de repositórios/unidade de trabalho e mapeamento dos arquivos atuais.
- Cenários de aceitação para futuras migrações e testes de integração.

Não inclui instalar PostgreSQL, criar tabelas, migrations, ORM, adaptar o coletor, importar dados ou implementar autenticação e análises.

## Critérios de aceitação

1. As seis loterias cabem no mesmo modelo sem colunas específicas por modalidade.
2. Identidade sobrevive a correções de data e IDs privados continuam externos.
3. Raw compartilhado não apaga capturas, fontes ou instantes distintos.
4. Revisões são imutáveis, publicação é explícita e replay antigo não regride estado.
5. Regra, componentes e séries possuem vínculos coerentes por loteria e versão.
6. Faixas e dinheiro distinguem zero, desconhecido, escopo e forma de pagamento.
7. Checkpoint contíguo se apoia em processamento concluído e não no maior ID.
8. Concorrência e falhas possuem estratégias explícitas; rede não segura transação aberta.
9. Restrições estão atribuídas a mecanismos viáveis, sem CHECK que consulte outras tabelas.
10. Modelo lógico, contrato, matriz de validação, decisões e aprendizados estão documentados.

## Entregas

- [Modelo lógico](../database/modelo-logico.md): catálogo, evidência, identidade, conteúdo tipado, escopo financeiro e continuidade.
- [Contrato de persistência](../database/contrato-persistencia.md): transações T1–T6, concorrência, portas e importação.
- [Matriz de validação](../database/matriz-validacao-persistencia.md): 37 cenários atribuídos aos incrementos responsáveis.
- [ADR-0003](../architecture/decisions/ADR-0003-persistencia-revisionada.md): registro das decisões e alternativas.
- Referência cruzada no modelo canônico e aprendizados L-112 a L-120.

## Decisões que refinam o desenho anterior

1. `raw_artifact` representa bytes; `capture_receipt` representa observação. Deduplicar o primeiro não elimina o segundo.
2. `draw_id` é durável; data e regra ficam em `draw_revision`, com aliases para identidade externa/provisória.
3. Candidato, validação e publicação são estados distintos: conteúdo é selado e decisões são registradas separadamente.
4. Dinheiro exige escopo e forma de pagamento; suas ausências continuam tipadas.
5. Um passo contíguo, sua observação e o avanço do checkpoint confirmam juntos.
6. Mesma receita de interpretação é reutilizada, e tentativas repetidas continuam auditáveis.
7. Não aplicar UNIQUE global de hash por concurso, nem unicidade global de data.
8. O modelo não promete transação distribuída com a fonte ou object storage.

## Verificação realizada

- Revisão de correspondência com os contratos das seis loterias e as invariantes das SPECs 0020–0022.
- Restrições, tratamento de NULL, intervalos, locking, isolamento e numeric confrontados com documentação oficial PostgreSQL, citada nos documentos.
- Conferência das relações, dos responsáveis por cada garantia e dos links internos.
- Comparação da auditoria operacional antes/depois e dos hashes históricos.
- Alterações desta tarefa restritas à documentação. Não houve criação de banco, migration, mudança do domínio, importação ou nova coleta.

Não foram executados testes SQL ou de concorrência PostgreSQL: eles dependem da implementação futura. Os 37 cenários são critérios de aceitação, não resultados já aprovados em banco real.

## Limitações e pendências controladas

- DDL, ordem de migrations, instalação de `btree_gist`, versão exata do servidor e privilégios serão comprovados no ambiente da próxima tarefa.
- Vínculos compostos e constraint triggers exigem testes de integração; não estão protegendo o código atual por mera existência desta documentação.
- Canonicalização relacional precisa de versão e vetores antes da carga.
- Receitas de processamento legadas com versões desconhecidas permanecem identificadas como legadas.
- Preços/políticas comerciais, usuários, dados analíticos e modelos de previsão terão schemas em seus incrementos.

## Próxima tarefa recomendada

**SPEC-0024 — Primeiras migrations PostgreSQL e testes de integridade do recorte de ingestão.**

Justificativa: transformar este contrato em DDL verificável sobre banco vazio, com catálogo, evidências, revisões seladas e checkpoint, selecionando explicitamente os cenários da matriz cobertos. Repositórios, carga histórica e API seguem em incrementos posteriores.
