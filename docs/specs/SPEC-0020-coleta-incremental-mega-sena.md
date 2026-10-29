# SPEC-0020 — Primeiro fluxo incremental da Mega-Sena

## Estado

Concluída em 2026-10-20 (America/Sao_Paulo). Critérios definidos antes da construção.

## Objetivo e escopo

Qualificar por amostra limitada a resposta JSON pública da CAIXA e implementar uma execução manual, de um concurso por chamada, que preserve o raw, normalize, diagnostique e reconcilie revisões locais. A persistência fica atrás de uma porta substituível pelo futuro PostgreSQL.

Não inclui scheduler, download histórico em massa, publicação de concursos, migração física do repositório ou mudança dos arquivos históricos.

## Critérios de aceitação

- GET de último concurso ou número explícito, host e paths fixos, TLS verificado, redirects desabilitados, timeout e tamanho limitados.
- Resposta original preservada antes de qualquer tentativa de interpretação.
- Dinheiro decimal, identidade solicitada conferida, datas, dezenas, ordem de extração e três faixas validadas.
- JSON inválido, estrutura nova, números inválidos, valores negativos e respostas incompletas geram diagnóstico e não alteram revisões válidas.
- Nova coleta idêntica não duplica revisão; conteúdo diferente cria revisão candidata conservando a anterior.
- Hash semântico não depende de horário da captura ou flags de navegação da resposta.
- Adaptadores de rede e filesystem separados do caso de uso e do parser.
- CLI permite retomada pelo artefato salvo sem rede.
- Testes offline cobrem erros, idempotência, correções e preservação de evidência.
- Evidências, limites da qualificação e próxima tarefa documentados.

## Entregas

- `app/application/collect_mega_sena.py`: caso de uso, portas, hash semântico e coordenação da coleta/replay.
- `app/ingestion/mega_sena_api.py`: interpretação pura do JSON observado.
- `app/infrastructure/caixa_http.py`: GET restrito com timeout, TLS, limite e bloqueio de redirects.
- `app/infrastructure/local_collection.py`: raw por hash, receipts, diagnósticos e revisões locais com lock e gravação atômica.
- `app/interfaces/collect_mega_sena.py`: CLI manual para último concurso, concurso explícito e replay.
- `app/catalog.py`: fonte JSON oficial registrada como `contract_observed`.
- Fixture real formatada e testes em `tests/test_mega_sena_collection.py`.
- [Qualificação e contrato observado](../data/mega-sena-fonte-incremental.md).
- [Guia operacional](../engineering/coleta-mega-sena.md).
- Aprendizados L-091 a L-097.

## Verificação e resultados

- 15 testes novos offline: contrato, conciliação com histórico, idempotência, correção, replay, schema, datas, números, rateios, rede, limites, interrupção e lock.
- 22 testes existentes de domínio, catálogo e normalização Mega-Sena permanecem passando.
- Consulta real do concurso 2954: HTTP 200, 1.750 bytes, nenhuma falha de normalização, revisão candidata 1.
- SHA-256 observado e capturado pelo coletor: `78242eed3eb7d9384721f8739e6c10f5e344f3a747619f3e9006dd55108921a1`.
- Replay real sem rede: `unchanged`, revisão 1.
- Históricos originais permanecem com os seis hashes registrados na SPEC-0001.
- Nenhuma alteração nas dependências preexistentes ou na aplicação web.

## Decisões e limitações

1. Persistência local substituível permite validar o fluxo sem antecipar banco e infraestrutura.
2. Toda revisão é candidata. Publicação e aceitação de correções serão políticas explícitas futuras.
3. A API oficial não possui contrato público ou limites localizados nesta pesquisa; não foi promovida a fonte aprovada para automação recorrente.
4. Cada chamada consulta somente um concurso. Não há cursor, lote, scheduler ou recuperação automática dos 117 identificadores posteriores ao histórico local.
5. `tipoPublicacao=3` é o perfil observado nas duas amostras; outros códigos permanecem sem semântica certificada.
6. Campos de navegação e informações ainda sem contrato semântico permanecem no raw e não geram correção do conteúdo normalizado.
7. Correções anteriores à janela consultada só serão descobertas se o concurso for consultado novamente.
8. A gravação local é serial e atômica por arquivo, não uma transação distribuída. Há procedimentos de retomada por receipt.

## Próxima tarefa recomendada

**SPEC-0021 — Sincronização incremental limitada da Mega-Sena, com cursor, retomada e janela de revisão.**

Justificativa: o fluxo unitário está validado. O próximo incremento deve planejar e processar concursos intermediários com limite de requisições, checkpoint somente após sucesso e recuperação de falhas, aproveitando os mesmos adaptadores. A política de frequência deve continuar explícita e conservadora enquanto o contrato do fornecedor não estiver qualificado.
