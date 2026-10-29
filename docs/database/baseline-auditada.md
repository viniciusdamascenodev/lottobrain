# Baseline auditada e passagem entre fontes — SPEC-0030

## Responsabilidades e referências

A baseline é uma decisão imutável sobre uma cobertura, não o maior concurso visto, um arquivo anexado ou a aprovação permanente de uma fonte. O cenário implementado usa somente Mega-Sena: histórico XLSX 1–2954, fluxo JSON e sequência oficial numérica.

| Registro | Origem e responsabilidade |
|---|---|
| `ingestion_baseline` | source_id XLSX, artifact_id original, intervalo, manifesto de registros, auditoria e status loaded |
| `baseline_activation` | vínculo append-only entre baseline, run/receipt históricos, relatório/hash de cobertura, aprovação e checkpoint de destino |
| `sync_checkpoint` | source_id JSON, stream fixo mega_sena_forward, baseline histórica e cursor inicialmente 2954 |
| `sync_step` | observação JSON aceita do próximo concurso, token de lease e conclusão atômica com cursor |

Não há conversão do XLSX em captura JSON fictícia. A baseline histórica continua pertencendo à fonte XLSX, mesmo quando o checkpoint que a utiliza pertence à fonte JSON.

## Migration 0030_01

Migration nova, posterior a 0024_03. Nenhum arquivo de migration aplicado foi reescrito.

- `baseline_activation` possui FKs compostas para baseline/run/receipt e suas fontes/loteria, além de FK diferível para o contexto completo do checkpoint (id, baseline, fonte de destino, loteria e stream).
- O vínculo é inserido antes do checkpoint. Sua FK diferível só permite confirmar a transação quando o checkpoint correspondente existe; a guarda do checkpoint só admite passagem entre fontes quando o vínculo já está presente. O ciclo é deliberado e restrito à criação atômica desses dois registros.
- A FK antiga que exigia fonte idêntica entre baseline/checkpoint foi substituída por FKs explícitas de baseline/loteria e fonte/loteria, mais guarda de passagem entre fontes. Não houve remoção da verificação de fonte/loteria.
- Contexto de checkpoint continua imutável e regido por row_version, fencing e evidência contígua. As operações legadas de mesma fonte continuam possíveis; suas referências não se tornam loaded automaticamente.
- Unicidade de comando, baseline e checkpoint, e de destino/loteria no vínculo, impede duas ativações do mesmo destino. A aplicação também rejeita qualquer checkpoint anterior dessa fonte, mesmo com outro stream.
- Baseline e vínculo são append-only. Downgrade com ativação ou checkpoint entre fontes é recusado antes de remover qualquer evidência. Downgrade vazio restaura as FKs anteriores; upgrade sobre dados anteriores não os promove/modifica.

Não se promete provar hashes canônicos ou cobertura de 2.954 registros em um CHECK SQL. A aplicação reconstrói e confere esses hashes em snapshot; o banco protege referências, estados, tamanhos, intervalos, formato do relatório, ator e contexto de destino. `@>` com array vazio não prova que o array está vazio: os arrays de problemas são comparados explicitamente com `[]`.

## Conteúdo da aprovação

O vínculo registra `command_key/request_hash`, política versionada, hash do plano histórico, snapshot/fingerprint do catálogo JSON, relatório/hash da cobertura, referência explícita de aprovação, papel SQL executor e instante obtido do banco.

`ingestion_baseline.audit_reference` aponta para `urn:lottobrain:baseline-activation:UUID`; o vínculo resolve essa referência para evidências persistidas no mesmo banco. Não é URL de relatório externo que precise ser baixado para autorizar a criação.

O ator é `current_user`, conferido pela guarda SQL, não uma identidade humana enviada livremente pela aplicação. Isso serve à operação controlada e não implementa autenticação, autorização administrativa de usuários ou assinatura digital de auditoria.

## Privilégios

`scripts/database/roles.sql` continua sendo aplicado explicitamente pelo provisionador **após** as migrations. Nenhum login/segredo é criado pela aplicação.

| Papel | Permissões relevantes |
|---|---|
| lottobrain_ingest | permissões anteriores de captura/escrita/lease/step; sem INSERT de baseline, ativação ou checkpoint |
| lottobrain_audit | somente leitura |
| lottobrain_bootstrap | SELECT e INSERT de baseline, ativação e checkpoint; sem UPDATE de catálogo/baseline/ativação, DELETE, DDL ou publicação |

O bootstrap é uma fronteira de confiança de operação, não um verificador independente do código da aplicação: alguém autorizado a escrever SQL diretamente com esse papel pode criar referências. A operação suportada passa pelo caso de uso e sua auditoria integral. Não distribuir esse acesso ao coletor comum ou ao navegador.

## Limites

Sem nova arquitetura genérica de aprovação, extensão de hashing SQL, microsserviço ou mecanismo de autorização HTTP. A tabela/modelo atende ao consumidor concreto Mega-Sena; outras estratégias de cobertura e modalidades exigirão suas próprias políticas e provas. Baseline loaded não implica dado publicado, fonte permanentemente autorizada ou sincronização agendada.
