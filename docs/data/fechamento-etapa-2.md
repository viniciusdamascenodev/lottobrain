# Etapa 2 — Conhecer e qualificar os dados

## Resultado em 27/10/2026

**Concluída a descoberta e qualificação documental das seis loterias.** Foram esclarecidas as pendências de calendário, disponibilidade/semântica de campos, continuidade recente e condições publicadas das fontes. O resultado inclui fontes tecnicamente legíveis com restrições de uso e integração. Não significa que todas estejam liberadas para redistribuição ou habilitadas para operação automática.

O fechamento responde ao pedido de concluir a etapa 2. Não cria uma nova SPEC nem substitui o inventário. Reutiliza os [15.471 históricos qualificados](qualificacao-importacao-historica.md), as 20 matrizes numéricas, os 45 vetores existentes e a [verificação amostral anterior](verificacao-fontes-atuais-2026-10-27.md). Aqueles documentos e suas evidências permanecem como fotografias das respectivas execuções.

O [manifesto desta conclusão](fechamento-etapa-2.json) contém os novos receipts, hashes, cobertura e restrições. As [12 amostras preservadas](fechamento-etapa-2-2026-10-27/amostras/) somam 806.058 bytes. Foram 31 consultas diretas adicionais, limitadas a 4 MiB por resposta, sem retries automáticos, paginação ou varredura de concursos. Pesquisa web e consultas diretas são evidências diferentes, sem atribuir um status HTTP direto a resultados de busca.

## Critérios de conclusão

| Critério da descoberta | Resultado e evidência |
|---|---|
| Conhecer os seis históricos e problemas de qualidade | Inventário/normalização/qualificação existentes reaproveitados, sem repetir a auditoria original |
| Identificar fontes atuais e formatos | JSON/XLSX CAIXA, CSV Texas, ZIP/CSV FDJ; host atual CAIXA descoberto pela configuração oficial |
| Distinguir campos existentes, derivados e ausentes | Matriz de campos abaixo, incluindo escopo financeiro e ausência condicional |
| Verificar período recente e meios de recuperação | 756 registros posteriores às fronteiras dos arquivos originais, com verificação de continuidade nos snapshots |
| Esclarecer calendários excepcionais | Mega Semana, eleições e remanejamentos de junho documentados por fontes oficiais |
| Qualificar regras e diferenças entre jogos | Matrizes existentes preservadas; evidência primária adicional para PB inicial/MM 1999; calendário e rateio separados da matriz |
| Investigar uso, disponibilidade e limitações | Políticas localizadas, restrições explícitas e ausência de SLA identificada; nenhuma licença presumida |
| Definir tratamento de divergências/ausências | Decisões abaixo e condições verificáveis de integração nas SPECs 0033/0034 |
| Preservar dados/código e registrar aprendizados | Hashes e testes no manifesto; nenhum coletor, banco, migration ou agendador alterado |

Uma qualificação pode concluir que determinado uso ainda depende de autorização ou que um transporte falhou. Esses são resultados da investigação, não certificados de prontidão operacional. **A aprovação irrestrita das fontes não foi obtida.** Não é possível conceder autorização em nome dos operadores ou deduzir um SLA de uma resposta 200.

## Continuidade recente comprovada

| Loteria | Fronteira do arquivo original | Fronteira da fonte inspecionada | Registros posteriores disponíveis | Verificação |
|---|---|---|---:|---|
| Mega-Sena | 2954, 20/12/2025 | 3075, 26/10/2026 | 121 | XLSX com 3.075 concursos, IDs 1–3075 sem buracos/duplicação; combinação/data final iguais ao JSON |
| Lotofácil | 3571, 24/12/2025 | 3814, 26/10/2026 | 243 | XLSX com 3.814 concursos, IDs consecutivos; dois concursos distintos na mesma data, explicados abaixo |
| +Milionária | 314, 24/12/2025 | 401, 24/10/2026 | 87 | XLSX com 401 concursos, IDs consecutivos; combinação, trevos e data final iguais ao JSON |
| Powerball | 24/12/2025 | 26/10/2026 | 131 | CSV já preservado; conjunto de datas recentes igual às segundas/quartas/sábados do intervalo |
| Mega Millions | 23/12/2025 | 23/10/2026 | 87 | CSV já preservado; conjunto de datas recentes igual às terças/sextas do intervalo |
| EuroMillions | 26/12/2025 | 27/10/2026 | 87 | Nova captura da partição FDJ; conjunto de datas recentes igual às terças/sextas do intervalo |

Na janela recente declarada não foram encontrados IDs brasileiros faltantes, datas americanas/europeias esperadas ausentes, duplicação da identidade escolhida ou combinações principais/especiais fora da cardinalidade e dos limites vigentes. A duplicação de **data** da Lotofácil não é duplicação de identidade.

Essa prova mede continuidade e estrutura dos arquivos oferecidos, não certificação individual independente de cada resultado nem auditoria financeira integral. Não revalida contra fonte primária cada linha anterior a dezembro/2025. Os arquivos Texas contêm 2.017/2.389 registros totais desde a participação estadual e o ZIP FDJ 703 registros da partição desde 2020; não substituem os históricos locais anteriores a essas fronteiras.

Os XLSX foram capturados às 18h55 e o ZIP FDJ às 18h57, America/Sao_Paulo. Os CSVs Texas são os bytes já obtidos às 12h35–12h38. A FDJ passou de 23/10 na fotografia anterior para 27/10 nesta captura. O conjunto 21–30–32–42–48, estrelas 3–6, concorda com o [operador irlandês](https://www.lottery.ie/results/euromillions/history). Não tratar a fotografia anterior como permanentemente atual, nem a diferença entre horários de nossas consultas como latência de publicação.

**Nenhum desses 756 registros foi importado por esta tarefa.** Eles são posteriores aos arquivos originais, não necessariamente ausentes de todo armazenamento local: há candidatos Mega-Sena isolados no workspace antigo. O cursor 2955 não foi avançado.

## Fonte brasileira vigente e mudança de estrutura

A página oficial [Mega-Sena](https://loterias.caixa.gov.br/Paginas/Mega-Sena.aspx) referencia o script de download. Ele usa a base configurada em [params.txt](https://loterias.caixa.gov.br/Style%20Library/json/params.txt), que aponta para **`https://servicebus3.caixa.gov.br/portaldeloterias`**. A cadeia publicada está preservada nas amostras, sem executar scripts externos.

As três rotas antigas `servicebus2/.../api/resultados/download?...` responderam 404. As equivalentes no host configurado `servicebus3` retornaram XLSX 200 para `Mega-Sena`, `Lotofácil` e `+Milionária` — esta última com `+` codificado `%2B`. Portanto, não concluir que a CAIXA deixou de oferecer histórico porque uma base legada falhou.

Os JSONs atuais nesse host retornaram 34 campos comuns, contra 33 do perfil anterior; +Milionária tem também `trevosSorteados`. O campo adicional é `tituloConcursoEspecial`, nulo nas três respostas. Todos os campos anteriormente amostrados dos mesmos últimos concursos permaneceram iguais. Mesmo assim, o normalizador Mega-Sena existente produz **`is_valid=false`, `source.schema_changed`**: candidato diagnóstico não equivale a resultado aprovado. Essa proteção foi comprovada, não removida.

O pedido exploratório de concurso zero respondeu **HTTP 500**, com erro interno de origem 404 encapsulado. Não converter todo 500 em “concurso inexistente”, não apresentar stack trace ao usuário e não afirmar que a rota publica um contrato simples de 404. Publicação parcial, contingência e rate limiting reais não foram observados; devem resultar em estado não qualificado/retomável conforme o caso, sem fabricação de números, limites do fornecedor ou faixas.

Os três XLSX continuam declarando dimensão apenas da primeira linha (`A1:T1`, `A1:AG1`, `A1:AI1`). Foi necessário ignorar esse metadado na leitura. Os leitores históricos existentes já fazem isso; não houve nova correção de parser.

## Calendários e identidade

| Caso | Conclusão para o contrato | Fonte |
|---|---|---|
| Calendário brasileiro regular | Mega: ter./qui. 21h, dom. 11h; Loto: seg.–sex. 21h, dom. 11h; +Mili: qua. 21h, dom. 11h; `America/Sao_Paulo` | [Regras CAIXA](https://loterias.caixa.gov.br/Paginas/regras-sorteios.aspx) |
| Mega Semana 26–30/10/2026 | Concursos 3075–3079, segunda a sexta às 21h; explica 3075 em segunda. Não altera a matriz 6/60 | [Comunicado CAIXA Notícias](https://caixanoticias.caixa.gov.br/Paginas/Not%C3%ADcias/2026/09-SETEMBRO/Mega-Sena-tera-cinco-sorteios-na-ultima-semana-de-outubro.aspx) |
| Eleições de outubro | Programação prevista para domingo 25/10 antecipada para sábado 24/10 às 21h; explica +Milionária 401 | [CAIXA Notícias, segundo turno](https://caixanoticias.caixa.gov.br/Paginas/Not%C3%ADcias/2026/10-OUTUBRO/CAIXA-loterias-antecipa-sorteios-no-segundo-turno-das-eleicoes-2026.aspx) |
| Lotofácil 3715/3716 | XLSX e os dois JSONs oficiais indicam 20/06/2026, combinações diferentes. Preservar os dois números oficiais. A CAIXA anunciou remanejamento dos sorteios nos dias de jogos do Brasil em junho | [Comunicado de junho](https://caixanoticias.caixa.gov.br/Paginas/Not%C3%ADcias/2026/06-JUNHO/CAIXA-ajusta-horario-dos-sorteios-das-loterias-nos-dias-de-Jogo-do-Brasil-na-Copa-do-Mundo.aspx) e amostras 3715/3716 |
| Powerball | Seg./qua./sáb., 22h59 ET; `America/New_York`; Double Play ocorre depois, como outra série | [Powerball](https://www.powerball.com/) e [Double Play](https://www.powerball.com/double-play) |
| Mega Millions | Ter./sex., 23h ET; `America/New_York`; números e ganhadores podem ser publicados em momentos distintos | [FAQ oficial](https://www.megamillions.com/faqs) |
| EuroMillions | Ter./sex.; horário anunciado francês aproximadamente 21h05, `Europe/Paris`; data civil comum não é timestamp UTC do sorteio | [Dossiê e fontes oficiais já pesquisados](dossie-oficial-loterias.md) |

O horário efetivo dos concursos 3715/3716 não é fornecido pelos JSONs; não foi deduzido da ordem dos IDs. A justificativa geral oficial do remanejamento é suficiente para não classificar a mesma data como corrupção ou fundir os resultados. A tabela do comunicado é imagem; horários exatos por concurso não são certificados nesta tarefa.

Decisão: calendário é previsão versionada, com exceção por data/concurso, e não identidade ou critério rígido de validade. Respeitar data oficial, anúncio excepcional e `dataProximoConcurso` contextualizada; sinalizar conflito em vez de deslocar resultado automaticamente. Fuso IANA deve ser usado para converter janelas e horário de verão; não congelar ET/França como deslocamento UTC constante. Data local e instante de coleta são fatos diferentes.

## Regras: o que a pesquisa adicional consolidou

- As **20 matrizes numéricas** existentes continuam sendo o ponto de partida. Não foram reescritas no catálogo.
- A matriz inicial Powerball 5/45 + 1/45 ganhou suporte primário no [boletim da Iowa Lottery de 2004, página 1](https://publications.iowa.gov/1378/1/LA041904.pdf). Ele descreve o lançamento em 1992; a fronteira final continua sustentada pelas evidências já registradas, sem promover toda cronologia a uma prova primária única.
- A versão Mega Millions 5/50 + 1/36, desde o sorteio de 15/01/1999, ganhou suporte no [comunicado da Michigan Lottery](https://milotteryconnect.com/1999/01/12/michigan-lottery-big-game-players-can-now-cash-in-instantly/amp/). O texto tem dateline 1998 discrepante da URL, mas explicita o sorteio de 1999 e a nova matriz; conservar essa ressalva de proveniência.
- A CAIXA anunciou novo **rateio ordinário a partir de 3073, 22/10/2026**: 40/10/10% para sena/quina/quadra, 25% para reserva final 0/5 e 15% para especial. As duas reservas não são novas faixas de acertos. A combinação permanece 6/60. Fonte: [comunicados oficiais](https://www.caixa.gov.br/loterias/comunicados-importantes/Paginas/default.aspx), conteúdo recuperado por pesquisa; a consulta direta retornou redirecionamento para a própria URL.

Calendários, preços e políticas financeiras precisam de vigências próprias. O dossiê de 20/10 não deve ser aplicado como rateio vigente após 3073. Não recalcular pagamentos históricos com porcentagens atuais; conservar os valores publicados e a regra aplicável à data/concurso. Os códigos `indicadorConcursoEspecial` e `tipoPublicacao` não recebem nova semântica oficial por inferência do nome.

## Campos disponíveis e dados adicionais

Legenda: **A** = observado na fonte/amostra; **D** = derivável com contexto explícito; **C** = precisa de coleta/enriquecimento em fonte identificada; **N** = não oferecido no contrato escolhido; não significa inexistente no mundo. Uma disponibilidade A não implica carga SQL ou autorização de redistribuição.

| Informação | Mega-Sena | Lotofácil | +Milionária | Powerball | Mega Millions | EuroMillions |
|---|---|---|---|---|---|---|
| Identificador oficial | A: `numero` | A: `numero` | A: `numero` | N; D: chave contextual por data | N; D: chave contextual por data | A: referência anual FDJ; D: chave contextual por data |
| Data civil | A | A | A | A | A | A |
| Hora efetiva do sorteio | N no JSON; calendário previsto separado | N no JSON; idem | N no JSON; idem | N no CSV; calendário previsto separado | N no CSV; idem | N no CSV; calendário previsto separado |
| Números principais | A: 6/60 | A: 15/25 | A: 6/50 | A: 5/69 atuais | A: 5/70 atuais | A: 5/50 |
| Números especiais | Não aplicável | Não aplicável | A: 2/6 trevos | A: PB 1/26 atual | A: MB 1/24 atual | A: 2/12 estrelas atuais |
| Regra vigente | D: catálogo + vigências documentadas | D: idem | D: idem | D: matriz pela data | D: matriz pela data | D: matriz pela data |
| Prêmio principal | A: prêmio por ganhador da faixa 1; não equivale à estimativa | A: idem | A: idem | A no legado; C: jackpot/annuity e cash na página central | A no legado; C: jackpot na tabela Texas/central | A: rateio por faixa FDJ; C: jackpot anunciado contextualizado |
| Faixas de premiação | A: 3 | A: 5 | A: 10 | C: página central, base e Power Play separados | C: detalhe Texas é estadual; central para agregado | A: 13 categorias comuns + extensões separadas |
| Ganhadores | A por faixa | A por faixa | A por faixa | C: página central | C: Texas por estado; central para agregado | A: França/Europa separados |
| Arrecadação | A: `valorArrecadado` | A: idem | A: idem | N no CSV; C: relatórios de vendas, sem qualificação de total nacional | N no CSV; C: idem | N no contrato recente; fonte consolidada pan-europeia não localizada nesta pesquisa |
| Moeda | A/contexto oficial BRL | A/contexto BRL | A/contexto BRL | D/contexto oficial USD | D/contexto oficial USD | D/contexto FDJ EUR; operador UK pode publicar GBP |
| Local do sorteio | A: local + município/UF | A: idem | A: idem | C: metadado atual Tallahassee | C: metadado atual Atlanta | N por sorteio no CSV; não inventar local histórico |
| Próximo prêmio estimado | A: campo específico | A: campo específico | A: campo específico | C: próximo desenho na página central | C: página de jogo/estimativa | C: página do operador; separar do rateio do sorteio anterior |
| Multiplicadores/extensões | Não aplicável | Não aplicável | Trevos são componentes, não multiplicadores | A: Power Play quando aplicável; C: Double Play separado | A: Megaplier histórico; atual atribuído ao bilhete, não ao sorteio | A: My Million/Etoile+ franceses; demais países exigem contrato próprio |

Há meios identificados de obter os campos essenciais e vários complementos. Arrecadação pan-europeia consolidada e horário efetivo de todos os sorteios históricos não têm uma fonte técnica qualificada nesta pesquisa. Isso fica explicitamente **indisponível no contrato**, sem estimativa fictícia. Se uma futura análise depender desses fatos, ela fica indisponível até qualificação específica; a investigação atual não afirma que toda informação desejável é publicamente coletável.

Detalhes que governam o enriquecimento:

- **BR:** rateio é prêmio por aposta ganhadora, distinto de fundo acumulado, RGP, arrecadação e estimativa futura. Valor zero com zero ganhadores pode ser válido. Cidade de ganhadores não é local do sorteio. Não derivar jackpot anunciado multiplicando rateio por ganhadores quando não houve vencedor.
- **Powerball:** [resultado de 26/10](https://www.powerball.com/draw-result?date=2026-10-26&gc=powerball) oferece jackpot anunciado, cash value e ganhadores/faixas. A página é legível pela ferramenta web; o transporte Python falhou sem HTTP. [Double Play](https://www.powerball.com/draw-result?date=2026-10-26&gc=pb-double-play) também é legível por esse meio, com 5–11–14–24–59 + PB 8, e precisa de transporte de produção qualificado. Não acrescentá-lo ao resultado principal.
- **Mega Millions:** [detalhe Texas de 23/10](https://www.texaslottery.com/export/sites/lottery/Games/Mega_Millions/Winning_Numbers/details.html_1158400901.html) declara **Texas Winners Only** e separa ganhadores por fator do bilhete. O texto `2X, 3X, 4X, 5X or 10X` não é um fator sorteado. Os [relatórios PB](https://www.texaslottery.com/export/sites/lottery/Games/Powerball/draw_sales.html) e [MM](https://www.texaslottery.com/export/sites/lottery/Games/Mega_Millions/draw_sales.html) identificam possíveis fontes de vendas e avisam que os dados financeiros não são auditados. Os PDFs não foram baixados/analisados: não se certifica total nacional a partir da página de índice.
- **EuroMillions:** o ZIP FDJ separa França/Europa, rateios, My Million e Etoile+. A [Irlanda](https://www.lottery.ie/results/euromillions/history) separa ganhadores totais e irlandeses, EuroMillions Plus e rifa local. A combinação comum conferiu, mas jackpot anunciado e valores financeiros dos operadores não foram promovidos a uma medida única reconciliada. O `prize` legado PT/ES permanece com a semântica e nove ausências já diagnosticadas, sem substituição automática por coluna francesa.

Cada medida financeira futura precisa de data/concurso, fonte, moeda, território, categoria, forma anunciada/paga/estimada e estado de ausência. A nova arquitetura de cadastro deve suportar perfis distintos, componentes, séries vinculadas, símbolos/códigos nacionais, fontes alternativas, calendários excepcionais e mudanças independentes de regras; não precisa gerar um coletor a partir de uma URL qualquer.

## Uso das fontes, transporte e publicação

| Fonte | Resultado da investigação | Consequência verificável |
|---|---|---|
| CAIXA | [Termos publicados](https://www.caixa.gov.br/termos-de-uso/Paginas/default.aspx) protegem conteúdo; não foi identificada licença específica da API, cota de requisições ou SLA | `contract_observed`; permissão aplicável ao armazenamento/exibição/automação deve ser esclarecida antes de ativação recorrente. API alcançável não é autorização irrestrita |
| Texas Lottery | [Aviso de copyright](https://www.texaslottery.com/export/sites/lottery/Misc/copyright.html) exige autorização prévia para uso/reprodução dos elementos protegidos; [linking statement](https://www.texaslottery.com/export/sites/lottery/Misc/linking_statement.html) permite links sob condições | Não apresentar o CSV como feed livremente licenciado. Disponibilidade técnica demonstrada; liberação de uso no produto não obtida |
| Powerball/MUSL | [Termos](https://www.powerball.com/terms-conditions) restringem reutilização de material protegido e não garantem atualização/completude; API MUSL exige chave e termos próprios | Não substituir CSV por scraping central sem qualificação do transporte e uso. Nenhuma chave foi solicitada/contratada |
| FDJ | [Regulamentos e aviso legal](https://www.fdj.fr/informations/reglements) reservam direitos de conteúdo/base e pedem autorização escrita para elementos protegidos | ZIP 200 demonstra formato/cobertura, não liberação para redistribuição. Não contornar 403; a página de regras respondeu 200 em consulta separada |
| Irish National Lottery | [Termos, parte I](https://www.lottery.ie/legal/terms-and-conditions) limitam uso pessoal e reutilização/integração sem permissão | Fonte de corroboração observada; não é fallback de redistribuição automaticamente aprovado |
| NY Open Data | [Catálogo oficial](https://data.ny.gov/Government-Finance/Lottery-Powerball-Winning-Numbers-Beginning-2010/d6yy-54nr) e [catálogo federal Mega Millions](https://catalog.data.gov/dataset/lottery-mega-millions-winning-numbers-beginning-2002) identificam alternativa pública | Quatro sondagens pequenas de metadados/amostras falharam no cliente Python sem HTTP. Alternativa identificada, não tecnicamente qualificada nem escolhida só pelo nome “open data” |

O registro descreve o que os fornecedores publicam; não resolve por conta própria a aplicação jurídica dessas cláusulas a fatos numéricos. **Acesso privado com usuários aprovados não constitui, por si só, permissão de reutilização.** Não foram enviados contatos ou pedidos em nome do usuário. Uma autorização externa não pode ser fabricada por documentação interna.

Para números e ganhadores, a [FAQ Mega Millions](https://www.megamillions.com/faqs) informa momentos de publicação distintos. Nenhum feed selecionado teve SLA contratual identificado. A decisão operacional é observar disponibilidade, manter revisão posterior de financeiros e medir atraso quando houver execução real, sem prometer atualização instantânea ou números de rate limit inexistentes. O agendador gratuito também terá sua própria limitação, tratada no plano de infraestrutura.

## Handoff para implementação, sem repetir descoberta

| Restrição/ação restante | Onde executar | Evidência para liberar |
|---|---|---|
| Perfil JSON atual com `tituloConcursoEspecial` | SPEC-0033 | Alteração deliberada do contrato, testes com bytes atuais/antigos e tratamento de valor não nulo; não apenas ignorar qualquer campo novo |
| Condição de uso das fontes escolhidas | SPEC-0033/0034, antes de ativar coleta/exibição abrangidas | Permissão aplicável confirmada ou alternativa com termos e transporte qualificados; bloqueio da fonte fica visível enquanto não resolvido |
| Perfis específicos Loto/+Mili/Texas/FDJ e Double Play | SPEC-0034 | Mapeamento, identidade, transporte e prova operacional; a inspeção não implementa adaptadores |
| Carga da defasagem e aprovação por lote | SPEC-0034 | Reconciliar as fronteiras aqui listadas com o estado real, sem sobrescrever raws e sem deduplicar Lotofácil por data |
| Agenda, exceções e enriquecimento posterior | SPEC-0034 | Rodada real, retomada, atraso visível e revisita após publicação de ganhadores; converter fusos com vigência |
| Rateio/medidas financeiras e análises | SPEC-0034/0035 | Vigência 3073 e escopos preservados; análises dependentes de fatos indisponíveis permanecem desabilitadas |

Essas atividades integram as entregas funcionais já planejadas. Não há nova etapa de inventário ou pesquisa genérica em aberto para os resultados principais. Persistência atualizada, automação e liberação de uso continuam requisitos reais de operação, sem serem declarados concluídos pelo fechamento documental.

## Validação e preservação

Os testes offline específicos exercitam hashes, continuidade dos seis snapshots, combinações recentes, dois concursos na mesma data e recusa do perfil JSON não qualificado. Comando:

```powershell
.venv\Scripts\python -m pytest tests/test_current_source_samples.py tests/test_stage2_source_qualification.py -q
```

**43 testes passaram em 5,38 segundos**, incluindo a aceitação dos 451 registros brasileiros recentes pelos normalizadores XLSX existentes. A recusa do JSON atual por mudança de estrutura é resultado esperado do teste, não falha omitida. Entre 288 arquivos preexistentes registrados, 282 ficaram idênticos por SHA-256 e seis documentos de planejamento/aprendizados receberam somente o encaminhamento desta conclusão. Os seis arquivos brutos originais e todos os relatórios anteriores permanecem intactos.

Resultado e comparação de arquivos estão no manifesto. Não foi necessário repetir suítes SQL, carga histórica ou testes de interface: não há alteração de produção. Fixtures, migrations, código, baseline e cursor foram preservados. Os scripts descartáveis ficam ignorados em `.local-postgres/stage2-close/`; as provas necessárias aos testes ficam nas amostras versionáveis.

**Próxima tarefa única: SPEC-0033 — Primeiro fluxo online Mega-Sena**, reutilizando este diagnóstico e respeitando os bloqueios de uso e compatibilidade. Ela não foi iniciada nesta tarefa.
