# Persistência comum das seis loterias

## Contrato implementado na etapa 6

A estrutura de concursos permanece única. A migração 0033_01 acrescenta conjuntos
privados aprovados, sem alterar as migrations anteriores nem o bloqueio de publicação
individual. O contrato histórico da SPEC-0026 e os normalizadores existentes continuam
sendo as autoridades de interpretação.

O caso de uso PersistQualifiedResult recebe um resultado normalizado com seus bytes,
hash, referência e localizador. Usa o armazenamento raw existente e uma transação SQL
para registrar captura legada, interpretação, revisão, observação, referências externas
e decisão de reconciliação. Não faz GET, não enumera concursos nem importa um histórico.

PreparedResult guarda o conteúdo e a evidência em bytes canônicos imutáveis.
O seletor de amostras interpreta uma cópia temporária dos bytes arquivados, evitando
associar o hash de um arquivo ao conteúdo de uma versão modificada durante a leitura.
O limite offline é 8 MiB, explícito; o limite HTTP anterior de 256 KiB foi preservado.

## Perfis e catálogo

| Loteria | Componentes e identidade | Particularidades preservadas |
|---|---|---|
| Mega-Sena | seis principais; concurso oficial | três faixas, BRL, ponte histórica/JSON existente |
| Lotofácil | quinze principais; concurso oficial | cinco faixas, BRL, concursos distintos na mesma data |
| +Milionária | seis principais e dois trevos; concurso oficial | dez faixas, indicador booleano de acumulação, BRL |
| Powerball | principais e Powerball; data provisória | sete matrizes, Power Play como atributo, USD |
| Mega Millions | principais e Mega Ball; data provisória | sete matrizes, Megaplier histórico e ausência posterior, USD |
| EuroMillions | principais e estrelas; data provisória | três matrizes, IDs externos, booleano de ganhador, contexto financeiro da fonte, EUR |

Datas dos históricos internacionais são identidades provisórias limitadas ao contrato,
não números oficiais inventados. IDs e referências do fornecedor são preservados à parte.
Valores ausentes, zero, escopo financeiro e multiplicadores não são intercambiáveis.

bootstrap_catalog prepara as seis loterias e suas 20 regras a partir do catálogo Python.
É um comando operacional, sem dependência de helpers de testes: adiciona ausentes,
reutiliza correspondências exatas e interrompe diante de divergência. Não faz upsert
destrutivo nem ativa novas loterias arbitrárias.

As fontes atuais qualificadas na etapa 2 são registradas com chaves adicionais.
Os endpoints e snapshots históricos permanecem intactos, inclusive o contrato legado
servicebus2. As chaves atuais servicebus3, OPEN-NY e SELAE não recebem capacidade de
aquisição por estarem cadastradas: coletores e perfis recentes pertencem à etapa de
atualização. Um perfil não implementado é recusado.

## Transação e reconciliação

- Mesma chave e mesmo pedido devolvem o resultado registrado; reutilização conflitante falha.
- Comando novo com conteúdo igual registra nova observação/captura, conservando a revisão.
- Divergência fica em quarentena por padrão, sem substituir o candidato anterior.
- Correção explícita do mesmo contrato cria nova revisão candidata; não aprova um dataset.
- Entre contratos Mega-Sena, a ponte existente conserva enriquecimento e recusa perda/conflito.
- Locks transacionais da identidade e da revisão serializam gravações concorrentes.
- Falha anterior ao commit desfaz toda a gravação SQL. Um objeto por conteúdo que ficou
  sem referência não é evidência de commit e não autoriza avançar cursor.

A reutilização do escritor de componentes, finanças, leitor de conteúdo, ledger,
armazenamento e unidade de trabalho evita criar um modelo SQL para cada loteria.

## Conjuntos aprovados

A política imutável delimita loteria, perfis, versões de regras e o hash do catálogo
e da semântica dos perfis autorizados. Mudança desse contrato exige nova política explícita.
A aprovação seleciona revisões
seladas com observação aceita, processamento concluído e fonte permitida. Nenhum conjunto
pode conter dois resultados do mesmo concurso ou misturar loterias.

As relações novas são dataset_policy, approved_dataset, dataset_member, dataset_decision
e active_dataset. A auditoria guarda o ator informado e a identidade real da conexão SQL.
O ator de CLI é uma identificação administrativa declarada; não implementa autenticação
de usuário do produto.

O manifesto dataset_members_v1 tem versão persistida no conjunto e é SHA-256 de UTF-8:

    slug LF
    policy_hash LF
    catalog_fingerprint LF
    draw_uuid|revision_uuid|observation_uuid|YYYY-MM-DD|content_hash LF
    ... uma linha por membro em ordem ordinal

A aplicação calcula o manifesto e o PostgreSQL o reconstrói no commit. Membros,
quantidade, fronteiras, hashes, loteria, fonte, revisão, observação e decisão são conferidos.
Conjuntos aprovados e suas decisões são imutáveis, inclusive contra inserções tardias.
Pedidos distintos para o mesmo manifesto e política reutilizam o conjunto aprovado,
registrando uma decisão de reutilização sem duplicar membros ou fabricar nova aprovação.

A aprovação não ativa o conjunto. A ativação exige versão esperada e decisão auditada:
zero representa ausência de ponteiro; cada troca incrementa a versão. Concorrência ou
rollback conserva o conjunto anterior. Uma decisão repetida conserva seu recibo original.

A leitura resolve o conjunto ativo uma vez e devolve seu UUID. As páginas seguintes
devem informar esse UUID, conservando os mesmos membros mesmo após nova ativação.
Datasets anteriores continuam consultáveis por versão aprovada. A versão individual
published_revision_id permanece vazia; o fluxo privado não remove a constraint existente.

## Permissões

| Papel de grupo | Responsabilidade |
|---|---|
| lottobrain_catalog_admin | bootstrap/administração do catálogo; consulta de metadados de revisões para os guards |
| lottobrain_ingest | captura, interpretação e candidatos; sem aprovação de conjuntos |
| lottobrain_dataset_approver | política, aprovação, ativação e respectivas decisões; sem alteração de resultados selados |
| lottobrain_reader | somente catálogo necessário e views de resultados de conjuntos aprovados |

Os grupos são NOLOGIN e não têm privilégios administrativos. O provisionador associa
logins separados a cada grupo. O leitor não pode acessar raw, receipts, candidatos ou
as tabelas internas de membros. As views usam security_barrier e contexto por dataset.
Esquemas continuam privados; nenhum endpoint HTTP foi aberto.

## Limites da entrega

Não há carga integral, agendamento, atualização das fontes, telas, identidade de usuários
ou modelos analíticos nesta etapa. A quarentena preserva a divergência; reconciliação
automática e a apresentação de qualidade/atualidade continuam nos fluxos futuros.
O armazenamento raw comprovado neste recorte é o adaptador local dedicado; não há prova
de integração de objetos com Supabase Storage por apenas configurar o banco.

O teste em PostgreSQL descartável comprova o código e as regras. A instalação em
Supabase exige projeto, conectividade, versão 17.x, migrations, permissões e execução
controlada comprovadas separadamente. Estado e evidências: [etapa 6](../engineering/etapa-6-persistencia.md).
