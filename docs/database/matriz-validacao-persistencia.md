# Matriz de validação do contrato de persistência

## Uso

São critérios de aceitação para implementar [modelo lógico](modelo-logico.md) e [contrato transacional](contrato-persistencia.md). Esta matriz não é uma suíte SQL executada: a SPEC-0023 é documental. Cada item deverá ganhar teste real de integração no incremento que implementar a respectiva garantia.

Execução posterior: [SPEC-0024 — resultados e pendências por DB-ID](verificacao-spec-0024.md). Somente os cenários ali atribuídos ao recorte físico foram exercitados; este contrato não passa a estar integralmente aprovado.

Evolução seguinte: [SPEC-0025 — repositórios, concorrência e falhas](verificacao-spec-0025.md). Essa cobertura acrescenta o fluxo JSON Mega-Sena, sem substituir os gates de importação/publicação das demais modalidades.

Não usar SQLite como prova de EXCLUDE, tipos temporais, locking ou constraints PostgreSQL. Verificações de concorrência precisam de duas conexões independentes e sincronização controlada; não depender de sleeps para obter a ordem esperada.

## Cenários obrigatórios

| ID | Cenário | Resultado esperado | Incremento responsável |
|---|---|---|---|
| DB-01 | Repetir slug ou alias da mesma loteria | rejeição por UNIQUE; não confundir com alias igual de outra loteria | migrations catálogo/identidade |
| DB-02 | Mesmo número oficial em fontes diferentes | mesmo draw_id, capturas e observações distintas | repositórios |
| DB-03 | Mesmo ID privado em dois provedores | referências independentes pelo source_id | migrations/repositórios |
| DB-04 | Dois concursos futuros no mesmo dia | sem colisão global de data; identidade qualificada por número/slot | identidade |
| DB-05 | Corrigir data de um concurso conhecido | mesmo draw_id; nova revisão e alias auditado quando necessário | reconciliação |
| DB-06 | Duas regras validadas sobrepostas | rejeitar; aceitar intervalos adjacentes e lacunas históricas legítimas | migrations catálogo |
| DB-07 | Fechar uma regra antes aberta excluindo revisão já referenciada | rejeitar a alteração; exigir decisão explícita de correção | migrations catálogo |
| DB-08 | Série/componente/faixa de outra regra ou loteria | rejeição por vínculo composto | migrations resultados |
| DB-09 | Cardinalidade incorreta, bola fora do limite ou repetida onde proibida | domínio rejeita antes da escrita; proteção de commit também falha em escrita direta | domínio + triggers |
| DB-10 | Regra sem principal ou com duas principais | ativação/commit rejeitados | migrations catálogo |
| DB-11 | Commit de revisão em building ou sem observação concluída | rejeitar; não persistir revisão parcial | migrations resultados |
| DB-12 | Adicionar bola/pagamento ou editar valor após selo | rejeitar inclusive INSERT de filho; permitir nova observação de suporte | imutabilidade |
| DB-13 | Conhecido zero versus desconhecido | zero com moeda é preservado; desconhecido não vira zero | migrations finanças |
| DB-14 | Dinheiro com NaN, infinito, envelope excedido ou escala inválida | rejeitar sem arredondamento silencioso | migrations finanças |
| DB-15 | Mesmo prêmio em escopos ou formas cash/annuity diferentes | fatos separados; não comparar/somar automaticamente | migrations finanças |
| DB-16 | Repetir medida com tier/currency nulos | rejeitar duplicata conforme regra explícita de NULL | migrations finanças |
| DB-17 | Raw idêntico capturado duas vezes | um blob/metadata de conteúdo, dois receipts | captura/storage |
| DB-18 | Timeout sem corpo e HTTP 404 com corpo | primeiro sem artefato; segundo com receipt e quarentena | captura |
| DB-19 | Repetir mesmo command_key após timeout de commit | retornar o efeito já confirmado, sem duplicar | repositórios/UoW |
| DB-20 | Reprocessar receipt/receita antiga depois de uma correção | reutilizar observação antiga, registrar tentativa e não regredir ponteiros | repositórios |
| DB-21 | Capturas distintas com A → B → A | três ocorrências ordenadas quando forem mudanças legítimas, sem UNIQUE global de hash | reconciliação |
| DB-22 | Dois escritores concorrentes da mesma identidade/conteúdo | um draw e uma revisão nova; rollback do candidato órfão; ambas observações preservadas | concorrência |
| DB-23 | Dois conteúdos concorrentes para o mesmo draw | números de revisão únicos e ordenados, nenhuma publicação implícita | concorrência |
| DB-24 | Commit interrompido antes/depois de revision/observation/step/checkpoint | tudo confirma junto em T3 ou nada; retry idempotente | UoW/falhas |
| DB-25 | Candidato adiante do cursor | persiste, mas não permite pular o próximo sequence_no | checkpoint |
| DB-26 | Worker com lease/token vencido tenta avançar | lease_lost; captura preservada e cursor intacto | checkpoint/concorrência |
| DB-27 | 429 seguido de falha na reconciliação | cooldown continua persistido na transação própria | checkpoint/falhas |
| DB-28 | Publicar revisão de outro draw ou candidata inválida | rejeitar, sem atualizar ponteiro ou emitir evento | publicação |
| DB-29 | Publicar correção válida | ponteiro, decisão, auditoria e outbox confirmam juntos; anterior preservada | publicação |
| DB-30 | Entregar outbox duas vezes | um efeito lógico no consumidor pela event_key | eventos |
| DB-31 | Baseline referenciada sem carga | cursor pode ancorar pela evidência aprovada; consultas históricas não fingem materialização | importação |
| DB-32 | Importar workspace atual | baseline 2954, cursor 2955, candidatos 2954/2955/3071, nenhuma publicação implícita | importação |
| DB-33 | Mudança de canonicalização | preservar hash/versionamento legado; novos vetores reproduzíveis | canonicalização/importação |
| DB-34 | Importar linha duplicada/sem identidade de XLSX | preservar posição e diagnóstico, sem deduplicação silenciosa | importação |
| DB-35 | Apagar raw/receipt/revisão ainda referenciado | rejeitar operação comum; restaurar via procedimento autorizado | retenção/segurança |
| DB-36 | Backtest consulta correção publicada depois do corte | excluir correção futura e usar revisões/decisões disponíveis naquele instante | plataforma analítica |
| DB-37 | Mesmo command_key com conteúdo/parâmetros diferentes | rejeitar com idempotency_conflict, sem reaproveitar resultado de outro pedido | repositórios/UoW |

## Recorte da primeira migration

Deverá criar entidades e garantias necessárias a um único concurso Mega-Sena atravessar T1–T3, incluindo referências de catálogo, selo de revisão, finanças, evidência e checkpoint. Relações futuras só entram se tiverem consumidor no recorte.

As decisões de publicação/outbox permanecem obrigatórias para T5, mas seu incremento pode suceder o da ingestão. Nenhuma API pública será conectada a candidatos antes desse gate.

A SPEC-0024 deve listar quais DB-IDs serão comprovados por SQL/migrations e quais dependem do próximo adaptador. Não declarar toda a matriz concluída apenas porque as tabelas foram criadas.

## Vetores de canonicalização

Antes da carga, produzir vetores a partir de dados reais já disponíveis para:

- Mega-Sena: JSON e XLSX do 2954, distinguindo fatos comuns de metadados exclusivos;
- Lotofácil: cinco faixas e valores fixos históricos presentes;
- +Milionária: clovers, faixas 0/1 agregadas e flag de acumulação;
- Powerball: fronteiras de matriz, Power Play e Double Play;
- Mega Millions: transição 2025, com ausência válida de fator único;
- EuroMillions: estrelas históricas, `has_jackpot_winner`, contexto PT/ES e nove zeros desconhecidos.

Cada vetor especifica representação, tipos, ordem de arrays, escala decimal, estados de ausência e hash esperado. Campos não disponíveis permanecem desconhecidos; não preencher vetores com dados inventados para facilitar o teste.

## Critério de saída antes de importar

- migrations aplicáveis a banco vazio e reaplicação controlada;
- instância PostgreSQL de versão fixada nos testes;
- constraints e transações do recorte comprovadas;
- auditoria SPEC-0022 íntegra e manifesto preservado;
- vetores canônicos aprovados pelo próprio contrato de dados;
- plano de rollback que preserve evidência;
- usuários/permissões de serviço sem acesso de superuser;
- toda pendência da matriz atribuída ao incremento correspondente.
