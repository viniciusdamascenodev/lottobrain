# Mega-Sena — qualificação inicial da fonte incremental

## Situação

**Autoridade:** oficial, domínio CAIXA. **Prontidão:** contrato observado, execução manual limitada. Automação recorrente ainda não qualificada. Pesquisa e implementação realizadas em 20/10/2026 no horário de São Paulo (capturas após 00h UTC de 21/10).

## Consultas efetuadas

| Recurso | Resultado observado | Uso |
|---|---|---|
| `/portaldeloterias/api/megasena` | HTTP 200, JSON, 1.747 bytes, concurso 3071 de 18/10/2026 | descobrir último resultado disponibilizado |
| `/portaldeloterias/api/megasena/2954` | HTTP 200, JSON, 1.750 bytes, concurso 2954 de 20/12/2025 | consultar identidade explícita e conciliar amostra |
| `/robots.txt` no servicebus2 | HTTP 404 | não oferece política de robots nesse recurso; não implica licença |

Foram feitas cinco requisições públicas bem-sucedidas ao servicebus2: a primeira consulta histórica, três consultas de qualificação e uma consulta pelo coletor pronto. Não houve varredura do histórico ou scraping em massa.

Fontes: [resposta mais recente](https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena), [concurso 2954](https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena/2954), [página oficial](https://loterias.caixa.gov.br/Paginas/mega-sena.aspx) e [comunicados oficiais](https://www.caixa.gov.br/loterias/comunicados-importantes/Paginas/default.aspx).

## Evidência reproduzível

| Amostra | SHA-256 dos bytes HTTP |
|---|---|
| Último resultado, 3071 | `7a4d0c4e3decee29a652b5d9a417c97b10c88daebd975b00db056ca0bec701e8` |
| Resultado 2954 | `78242eed3eb7d9384721f8739e6c10f5e344f3a747619f3e9006dd55108921a1` |

O coletor preservou o 2954 em `data/collections/mega_sena`, receipt `c6749b775d7144cd9c92f6251f37e131`, captura `2026-10-21T01:04:42.980735+00:00`. A pasta operacional é ignorada pelo Git. A fixture `tests/fixtures/mega_sena_api_2954.json` é uma representação formatada da mesma resposta real, com Unicode legível; seus bytes não são os bytes originais nem possuem o mesmo hash.

O teste concilia data, concurso, dezenas, quantidade de ganhadores e valores por ganhador contra a fixture existente do XLSX. Essa é uma verificação pontual, não certificação de todos os concursos.

## Contrato observado e mapeamento

| Campo da fonte | Destino | Decisão |
|---|---|---|
| `numero` | número oficial e chave canônica | inteiro positivo; conferir contra pedido explícito |
| `dataApuracao` | data civil | DD/MM/AAAA estrito, não posterior à captura |
| `tipoJogo` | validação | deve ser MEGA_SENA |
| `listaDezenas` | primary/main | seis inteiros únicos, ordenados, 1–60 |
| `dezenasSorteadasOrdemSorteio` | metadado `draw_order` | mesma combinação, preservada em ordem de extração |
| `listaRateioPremio` | sena, quina e quadra | três faixas, identidade e descrição conferidas |
| `valorArrecadado` | sales_total | decimal BRL |
| `valorAcumuladoProximoConcurso` | rollover_amount | decimal BRL |
| `valorEstimadoProximoConcurso` | next_estimated_jackpot | decimal BRL |
| `valorAcumuladoConcursoEspecial` | special_draw_rollover | decimal BRL |
| `valorAcumuladoConcurso_0_5` | ending_zero_five_rollover | decimal BRL |
| `localSorteio`, `nomeMunicipioUFSorteio` | metadados de local | não confundir local do sorteio com local do ganhador |
| `acumulado` | rollover booleano | independente do montante |
| `observacao` | metadado textual | preservado quando preenchido |
| demais campos | raw | ainda sem promoção semântica |

Valores monetários `null` permanecem desconhecidos; valores negativos, booleanos, não finitos ou com mais de duas casas são rejeitados. Um teto operacional de BRL 10¹⁸ protege a serialização de expoentes extremos; esse teto é defensivo e não é uma regra oficial da loteria. O rateio de cada faixa precisa estar disponível. O total de ganhadores deve ser inteiro não negativo. Zero é legítimo na amostra.

O código `tipoPublicacao=3` é aceito como perfil observado completo, sem afirmar que sua semântica esteja documentada. Outros códigos ou `premiacaoContingencia` preenchida exigem qualificação e ficam em quarentena.

## Descobertas que afetam a coleta

- O concurso histórico 2954 também retorna `ultimoConcurso=true`. Essa flag é excluída da identidade e do hash semântico.
- A data do próximo concurso pode refletir alteração posterior de agenda. Ela é preservada somente no raw e não transforma uma consulta histórica em novo concurso.
- Campos genéricos de outras modalidades, como `nomeTimeCoracaoMesSorte`, estão presentes e podem conter caracteres nulos. Não são dados da Mega-Sena.
- Cabeçalhos observados incluem cookie de borda e `Cache-Control: no-cache`. Cookies não são persistidos nem reutilizados; não há dependência de autenticação.
- Não foi observado ETag nesta amostra. O fluxo não presume suporte a 304 ou requisição condicional.
- Novos campos ou remoções no JSON geram quarentena para revisão consciente do contrato.

## Limites da qualificação

Não foram localizados contrato público de API, limites de frequência, SLA, política de versionamento ou licença específica de redistribuição nesses recursos. Ausência desses documentos não confirma autorização nem proibição; a fonte permanece `contract_observed`.

Ainda exigem qualificação: HTTP 404 para concurso inexistente, HTTP 429 real, publicação parcial durante sorteio, códigos de publicação, contingências, localidades de ganhadores, correções reais e disponibilização de números em horário de sorteio. Esses comportamentos possuem testes simulados quando aplicável; não são apresentados como observações do fornecedor.

## Cobertura

O histórico original continua terminando no concurso 2954. Na pesquisa, o último resultado era 3071; existem 117 identificadores posteriores a verificar. Esta tarefa não baixou esse intervalo e não afirma completude atualizada.

A CLI processa um concurso por chamada. Consultar apenas o último não recupera intermediários perdidos nem descobre correções antigas automaticamente. A próxima SPEC deverá definir cursor e lote limitado com retomada e janela de revisão.
