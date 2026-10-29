# Verificação técnica das fontes atuais das seis loterias

## Resultado e limite de encerramento

Verificação em 27/10/2026, com consultas diretas registradas entre 12h35 e 12h38, America/Sao_Paulo. Há transporte público estruturado e amostras interpretáveis do **resultado principal das seis loterias**, com sobreposição conferida contra os vetores históricos já qualificados. A etapa 2 pode ser encerrada nesse escopo básico da primeira versão, com as condições operacionais abaixo explícitas.

Isso não aprova automaticamente agendamento, licença de uso irrestrita, estabilidade/SLA, completude financeira ou todas as extensões nacionais/vinculadas. A cobertura integral recente não foi importada nem certificada. As pendências identificadas têm escopo/ação definidos e não serão ocultadas como fonte plenamente operacional.

Foram 18 intenções de consulta HTTP direta: 15 respostas 200, uma resposta 302 e duas falhas de transporte sem status HTTP. A pesquisa de páginas pelo navegador é contabilizada separadamente. Não houve retry automático, varredura de concursos ou scraping paginado. Foram obtidos dois CSVs e um ZIP publicados, pequenos e limitados, além das amostras JSON/HTML. Os nove arquivos de evidência versionados somam **312.412 bytes**.

As **62 verificações exploratórias passaram**, assim como **20 testes offline** reproduzíveis. O normalizador Mega-Sena existente aceitou bytes novos e de sobreposição sem mudança. Os seis históricos, relatórios anteriores, fixtures e migrations foram preservados. Nenhum coletor definitivo, cadastro de fonte, banco ou agendamento foi implementado/ativado nesta tarefa.

## Fontes e fronteiras observadas

As fronteiras são fotografias da fonte no instante da consulta, não uma afirmação permanente de último resultado. Ainda não havia resultado do sorteio europeu de 27/10 na amostra obtida ao meio-dia em São Paulo.

| Loteria | Fonte escolhida para o contrato técnico básico | Último resultado observado | Novos registros/posições oferecidos após o histórico local |
|---|---|---|---:|
| Mega-Sena | [JSON público CAIXA](https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena) | 3075, 26/10/2026 | 121 posições oficiais após 2954 |
| Lotofácil | [JSON público CAIXA](https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil) | 3814, 26/10/2026 | 243 posições após 3571 |
| +Milionária | [JSON público CAIXA](https://servicebus2.caixa.gov.br/portaldeloterias/api/maismilionaria) | 401, 24/10/2026 | 87 posições após 314 |
| Powerball | [CSV Texas Lottery](https://www.texaslottery.com/export/sites/lottery/Games/Powerball/Winning_Numbers/powerball.csv) | 26/10/2026 | 131 linhas recentes após 24/12/2025 |
| Mega Millions | [CSV Texas Lottery](https://www.texaslottery.com/export/sites/lottery/Games/Mega_Millions/Winning_Numbers/megamillions.csv) | 23/10/2026 | 87 linhas recentes após 23/12/2025 |
| EuroMillions | [ZIP da partição recente FDJ](https://www.sto.api.fdj.fr/anonymous/service-draw-info/v3/documentations/1a2b3c4d-9876-4562-b3fc-2c963f66afe6), ligado pelo [histórico oficial](https://www.fdj.fr/jeux-de-tirage/euromillions-my-million/historique) | 23/10/2026 | 86 linhas recentes após 26/12/2025 |

As diferenças numéricas brasileiras são posições a reconciliar, não concursos já importados nem prova individual de cada resposta. Mega-Sena já tem 2955 e candidato isolado 3071 no workspace antigo; após o cursor 2955 há 120 posições até 3075, sem avanço do cursor nesta tarefa. Nas fontes sem número oficial qualificado, a data permanece identidade provisória contextualizada pela loteria; não criar números de concurso artificiais.

## Contratos brasileiros observados

As três rotas responderam sem chave/cookie de aplicação, em JSON com identidade oficial, data civil DD/MM/AAAA, tipo de jogo, números e premiação. Consultas explícitas dos últimos números retornaram o mesmo payload da descoberta. Foram consultados também 2954/3571/314, já presentes nas fixtures: números/data e todos os ganhadores/valores das faixas conferiram com os vetores qualificados.

- **Mega-Sena:** seis dezenas distintas 1–60, três faixas e perfil `tipoPublicacao=3`; mesmo conjunto de campos esperado pelo parser existente. A resposta de 2954 manteve o hash já arquivado. Próximo concurso e flag `ultimoConcurso` não substituem identidade/cobertura.
- **Lotofácil:** quinze dezenas 1–25, cinco faixas de 15 a 11 acertos, perfil e campos comuns observados. O contrato JSON é fonte nova para o código: não há parser de produção Lotofácil JSON implementado nesta tarefa.
- **+Milionária:** seis dezenas 1–50, dois trevos 1–6 e dez faixas. Tem `trevosSorteados` adicional; números dos trevos chegam como textos de um dígito. A ordem observada tem **oito posições**, seis dezenas seguidas de dois trevos, e a ordem final pode diferir da lista de trevos. Não passar essa lista pelo parser de seis dezenas da Mega-Sena. As faixas superiores de 0/1 trevo continuam agregadas.

Valores financeiros foram lidos com Decimal; zero de rateio com zero ganhadores não é ausência genérica. Localidades dos ganhadores e local do sorteio são campos diferentes. Foram conferidos os perfis completos amostrados; contingência, novos campos, mudança de descrição/faixa ou perfil de publicação ainda exigem diagnóstico e qualificação.

## Contratos americanos observados

Os [downloads Powerball](https://www.texaslottery.com/export/sites/lottery/Games/Powerball/Winning_Numbers/download.html) e [Mega Millions](https://www.texaslottery.com/export/sites/lottery/Games/Mega_Millions/Winning_Numbers/download.html) indicam CSV sem cabeçalho. Nas amostras, as colunas são jogo, mês, dia, ano, cinco números, bola especial e posição do multiplicador. Os cinco números não estão sempre ordenados: ordenar para comparação sem atribuir automaticamente ordem oficial de extração.

**Powerball:** arquivo desde 03/02/2010; resultado recente 18–26–49–50–54 + PB 1, Power Play 3. Conferiu com a [página central](https://www.powerball.com/) pelo navegador. Datas de fronteira 2012-01-14/18 e 2014-01-18/22 confirmaram a mudança de multiplicador. Embora a descrição do layout omita o multiplicador no período fixo, o CSV observado mantém 11 posições e a última vazia. Não classificar isso como linha inválida por cardinalidade.

**Mega Millions:** arquivo desde 05/12/2003; resultado recente 3–7–46–49–51 + MB 5, conferido com a [tabela HTML do mesmo operador](https://www.texaslottery.com/export/sites/lottery/Games/Mega_Millions/Winning_Numbers/index.html). Não é confirmação por operador independente. Nas linhas de 08/04/2025 em diante, inclusive a última, há 11 posições com multiplicador vazio: o recurso passou a ser do bilhete, não um número sorteado ausente. Não fabricar um multiplicador a partir das opções 2x–10x.

O CSV de cada jogo cobre a atualização recente, mas não substitui o histórico anterior à entrada do Texas. Não fornece jackpot, arrecadação ou faixas nacionais. Esses valores permanecem desconhecidos neste perfil. A comparação com o último registro antigo de cada loteria conferiu números principais e bola especial. Double Play não está no CSV Powerball; foi observado separadamente pelo navegador em 26/10, mas o transporte direto Python das páginas centrais falhou sem status HTTP. Não assumir falha da fonte, nem qualificar a coleta automatizada desse sorteio vinculado a partir dessa prova.

## Contrato EuroMillions observado

O ZIP recente contém apenas `euromillions_202002.csv`, com 273.909 bytes descompactados. A amostra rejeita decodificação UTF-8 estrita e é compatível com CP1252/Latin-1; o teste usa CP1252. Delimitador `;`, 75 campos nomeados e coluna final vazia. O cabeçalho inclui acento em `numéro_de_tirage_dans_le_cycle`; preservar nomes/evidência antes de normalizar.

Foram conferidos os três sorteios recentes e a sobreposição de 26/12/2025. Em 23/10/2026: 24–33–35–44–47 e estrelas 7–11, iguais à [página FDJ do resultado](https://www.fdj.fr/jeux-de-tirage/euromillions-my-million/resultats/vendredi-23-octobre-2026). A ordenação da partição é decrescente e as colunas numéricas nem sempre estão crescentes. `annee_numero_de_tirage=26085` é referência da fonte, não nova sequência oficial global nem chave equivalente ao ID da API comunitária.

O CSV separa ganhadores na França e na Europa, valores por faixa, Etoile+ e My Million. Não somar escopos ou misturar extensões ao resultado comum. O rateio de primeira faixa é zero na amostra sem ganhador, enquanto a página informa jackpot anunciado de EUR 71 milhões: são medidas distintas. O antigo `prize` da API comunitária não deve ser reconciliado por equivalência ingênua com qualquer coluna FDJ. O caminho da partição deve ser descoberto pela página oficial, não por presumir que o UUID do download será permanente.

## Pendências delimitadas para a operação

| Pendência | Efeito e próxima ação |
|---|---|
| Exceções de calendário CAIXA | Página genérica indica dias que não explicam a Mega-Sena de segunda 26/10 e +Milionária de sábado 24/10. O PDF mensal de outubro respondeu 302 para a própria URL; não foi contornado. Preservar datas oficiais da resposta e qualificar exceções/janela de reconciliação antes de confiar só no calendário fixo. |
| Transporte Double Play | Página central foi corroborada pelo navegador; cliente Python não recebeu HTTP nas duas tentativas. Qualificar fonte alcançável ou apresentar ausência explícita da série vinculada. Isso bloqueia sua automação completa, não o resultado principal do CSV. |
| Financeiros e extensões adicionais | Perfil US não contém dados financeiros; FDJ tem escopos nacionais separados. Habilitar somente análises sustentadas por cada perfil; qualificação complementar quando necessária. |
| Adaptação de código | Reutilizar o parser Mega-Sena comprovado; implementar perfis JSON Lotofácil/+Milionária, CSV Texas e ZIP/CSV FDJ nas entregas funcionais. Scripts desta inspeção são temporários e não viram coletores definitivos. |
| Política de uso e estabilidade | HTTP 200/export público não implica licença irrestrita, SLA ou consultas ilimitadas. A prova usa orçamentos pequenos; manter qualificação da política do fornecedor para ativação recorrente. Não foi contratada/consultada API MUSL com chave. |

Essas condições não são rejeições de dados inventadas para a amostra: são limites da conclusão técnica. O encerramento é da descoberta e dos contratos básicos do resultado principal; o aceite operacional das SPECs 0033/0034 permanece pendente.

## Evidência e reprodução

- [Manifesto e resultado das verificações](verificacao-fontes-atuais-2026-10-27.json): receipts sanitizados, hashes, campos, amostras selecionadas, fronteiras e 62 verificações.
- [Amostras com bytes preservados](fontes-atuais-2026-10-27/amostras/): seis JSONs, dois CSVs e um ZIP, sem sobrescrever os raws originais.
- `tests/test_current_source_samples.py`: 20 testes offline de hash, parser existente, perfis novos, sobreposição e fronteiras de formato. Nenhum teste consulta a rede ou atualiza a data da amostra para simular atualidade.

```powershell
.venv\Scripts\python -m pytest tests/test_current_source_samples.py -q
```

O inspector e a análise exploratória permanecem ignorados em `.local-postgres/source-check-20261027/`. As amostras necessárias aos testes estão versionáveis. Não foi repetida a auditoria integral dos históricos nem a suíte SQL de escrita, pois código de produção, migrations e dados históricos não mudaram.

Próximo objetivo: **SPEC-0033 — Primeiro fluxo online Mega-Sena**, aproveitando esta verificação da atividade inicial. Carga recente e perfis adicionais ficam na SPEC-0034; não reiniciar inventário ou contratar fontes pagas para substituir uma prova técnica que agora existe.
