# ADR-0003 — Persistência revisionada com evidência e checkpoint transacional

## Estado

Definida em 21/10/2026 pela SPEC-0023; implementação pendente.

Atualização de estado em 27/10: catálogo/ingestão/revisões/continuidade e baseline Mega-Sena foram parcialmente implementados e exercitados nas SPECs 0024–0032 em bancos descartáveis. A indicação de pendência acima descreve o instante original, não o estado de todo o núcleo atual. Publicação individual/outbox permanece futura; a primeira consulta usa conjuntos aprovados conforme a [ADR-0004](ADR-0004-produto-privado-seis-loterias.md), sem remover o gate existente.

## Contexto

As SPECs 0020–0022 demonstraram coleta, revisões locais, continuidade e auditoria. O workspace contém capturas do 2954, 2955 e 3071, mas só sustenta cursor contíguo em 2955. Existem múltiplos outcomes para a mesma captura e uma tentativa de rede sem corpo.

Uma tabela única de resultados ou um checkpoint solto não preservaria essas diferenças. Os históricos também apresentam duas matrizes numéricas, séries vinculadas, ausência condicional, prêmios de naturezas diferentes e IDs privados.

## Decisão

1. Separar raw_artifact, capture_receipt e processamento: deduplicar bytes sem apagar observações.
2. Manter draw_id opaco, aliases qualificados e data/regra em revisão.
3. Selar conteúdo e filhos de cada revisão antes do commit; eventos de decisão e publicação são separados.
4. Persistir resultados tipados, escopo financeiro e estados explícitos de ausência.
5. Concluir observação, revisão, sync_step e avanço contíguo na mesma unidade transacional.
6. Conservar aquisição externa e object storage fora de transação longa, com auditoria para órfãos.
7. Usar constraints relacionais e poucos triggers específicos para integridade de commit.
8. Preservar a distinção entre baseline referenciada, carga materializada e dados publicados.

## Consequências

- A migração exige mudar a unidade de trabalho da aplicação; apenas substituir um arquivo por INSERT não basta.
- Um replay pode ser registrado sem duplicar o concurso ou retroceder a revisão atual.
- Conteúdo divergente fica como candidato até decisão explícita.
- Datas corrigidas e mudanças de matriz não exigem trocar identidade interna.
- O banco protege vínculos e transições; o auditor continua conferindo bytes, hashes, reprodução e cobertura.
- O schema inicial contém somente relações do fluxo em implementação, com expansão posterior por módulo.

## Alternativas consideradas

| Alternativa | Motivo para não adotar |
|---|---|
| Uma tabela com coluna por bola e prêmio | não representa as seis modalidades, suas versões ou evidências |
| JSONB como única persistência | deixa vínculos, escopos e invariantes sem proteção relacional |
| UNIQUE de hash por concurso | elimina a ocorrência legítima A → B → A e confunde conteúdo com observação |
| Data como PK | dificulta correções e modalidades com mais de um resultado no mesmo dia |
| Atualizar resultado publicado no lugar | perde auditoria e contamina avaliações temporais |
| Transação envolvendo GET e PUT externos | não oferece atomicidade real e segura recursos SQL durante rede |
| Event sourcing completo | acrescenta reconstrução generalizada sem requisito atual; eventos são restritos às decisões e auditoria |

## Critério de revisão

Reavaliar fragmentação, índices, particionamento e projeções após medir consultas e carga real. Alterar a receita de canonicalização ou identidade exige versão, vetores e plano de migração; não apenas mudança de coluna.

Detalhes: [modelo lógico](../../database/modelo-logico.md), [contrato](../../database/contrato-persistencia.md) e [matriz de validação](../../database/matriz-validacao-persistencia.md).
