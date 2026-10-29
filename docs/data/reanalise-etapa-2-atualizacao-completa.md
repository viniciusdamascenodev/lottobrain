# Reanálise da etapa 2 e proposta de atualização completa

## Conclusão da revisão — 27/10/2026

**A troca dos três links de download brasileiros está correta. A atualização completa do produto ainda não foi implementada.** O fechamento anterior da etapa 2 representa descoberta/qualificação documental, não dados operacionais atuais nem garantia de transporte permanente. Esta revisão acrescenta alternativas oficiais comprovadas, limitações por campo e uma proposta executável, sem repetir o inventário ou mudar coletores.

Foram preservadas [nove novas amostras](reanalise-etapa-2-2026-10-27/amostras/), 134.754 bytes, e [manifesto com consultas/resultados](reanalise-etapa-2-atualizacao-completa.json). Houve 23 consultas diretas limitadas, incluindo cabeçalhos, amostras, metadados, dois pequenos intervalos recentes e duas exportações de 14 dias. Não houve varredura integral, carga SQL, alteração de raw original, cadastro de fonte operacional ou agendamento.

## Revisão dos links e do código existente

- Configuração legada e catálogo Python apontam os três XLSX para `servicebus3`; o qualificador PostgreSQL da fonte XLSX Mega-Sena usa o mesmo endereço. A query de +Milionária contém `%2B`, que decodifica como `+`, preservando o nome da modalidade.
- A consulta individual Mega-Sena continua em `servicebus2/.../api/megasena`. Essa rota tem outra função. Não trocá-la cegamente pelo host atual sem qualificar `tituloConcursoEspecial`, já diagnosticado no JSON novo.
- As três consultas **HEAD e GET retornaram 403** entre 19h19 e 19h20 de São Paulo, com página `Azion - Default error page / Forbidden`. Na captura anterior, os mesmos downloads GET retornaram XLSX válidos. Não se identificou a causa exata: não atribuir automaticamente a rate limit, mudança de URL, indisponibilidade geral ou falha do usuário. Não houve tentativa de contornar o bloqueio.
- Não é seguro executar o download legado como atualização definitiva: ele grava diretamente no mesmo arquivo com `wb`, usa `requests.get` sem timeout e não possui a aprovação/reconciliação do fluxo novo. A correção da URL não corrige esses comportamentos preexistentes.
- Alterar o catálogo em código não atualiza linhas de uma base PostgreSQL já criada. A próxima integração precisa conferir o catálogo persistido e preservar snapshots/fingerprints antigos, sem reescrever evidência de uma captura anterior.

Referências de código: `app/core/config.py`, `app/catalog.py`, `app/infrastructure/postgres/catalog.py`, `app/infrastructure/caixa_http.py` e `app/core/downloader.py`. Não houve nova mudança de produção nesta revisão. Os 50 testes existentes do recorte catálogo/fontes passaram em 4,85 segundos; eles não são apresentados como prova de HTTP 200 atual.

## Fontes recomendadas por finalidade

| Loteria | Para recuperar/atualizar o resultado principal | Para completar campos adicionais | Prova e limite |
|---|---|---|---|
| Mega-Sena | XLSX oficial atual para recuperação; JSON por concurso para incremental | JSON: faixas, ganhadores, arrecadação, reservas, local, estimativa | Links corretos; novo bloqueio 403 precisa de tratamento operacional. O JSON atual exige qualificação de estrutura |
| Lotofácil | XLSX oficial; perfil JSON próprio | Faixas/ganhadores, arrecadação, local e próxima estimativa | Snapshot anterior mostrou cobertura até 3814; manter concursos 3715/3716 separados apesar da mesma data |
| +Milionária | XLSX oficial; perfil JSON próprio com trevos | Faixas, RGP, ganhadores, arrecadação, local e estimativa | Snapshot anterior até 401; ordem tem seis dezenas e dois trevos, sem reutilizar parser Mega-Sena cegamente |
| Powerball | [NY Open Data](https://data.ny.gov/Government-Finance/Lottery-Powerball-Winning-Numbers-Beginning-2010/d6yy-54nr), com [CSV Texas](https://www.texaslottery.com/export/sites/lottery/Games/Powerball/Winning_Numbers/download.html) para comparação/fallback qualificado | [Colorado](https://www.coloradolottery.com/en/player-tools/winning-history/?game=powerball&timeframe=14): jackpot, cash value, faixas estaduais e Double Play | NY forneceu 131 principais recentes iguais ao Texas; Double Play tem somente 63 preenchidos nessa janela, não 131 |
| Mega Millions | [NY Open Data](https://data.ny.gov/d/5xaw-6ayf), com [CSV Texas](https://www.texaslottery.com/export/sites/lottery/Games/Mega_Millions/Winning_Numbers/download.html) para comparação/fallback qualificado | [Colorado](https://www.coloradolottery.com/en/player-tools/winning-history/?game=megamillions&timeframe=14) e páginas oficiais de detalhes, com escopo explícito | 87 principais NY iguais ao Texas; o multiplicador atual é do bilhete, não um campo obrigatório do sorteio |
| EuroMillions | [FDJ: seis partições oficiais desde 2004](https://www.fdj.fr/jeux-de-tirage/euromillions-my-million/historique) | [Win2day/Áustria](https://www.win2day.at/lotterie/euromillionen/euromillionen-statistik-zahlen-ergebnisse-download): arquivos anuais de números e quotas; Bélgica como candidata adicional | 86 sorteios austríacos de 2026 iguais à FDJ; financeiros têm semântica própria, sem merge automático entre países |

Os históricos locais antigos continuam úteis. NY começa em 03/02/2010 no Powerball e 17/05/2002 no Mega Millions, conforme os metadados consultados. O Texas começa em 2010/2003. Portanto, nenhum desses arquivos substitui sozinho o histórico americano desde 1992/1996. Preservar o trecho legado anterior e registrar sua autoridade secundária até reconciliação específica.

## Novas provas técnicas

### Nova York: alternativa estruturada alcançável

As rotas públicas `https://data.ny.gov/resource/d6yy-54nr.json` e `https://data.ny.gov/resource/5xaw-6ayf.json` responderam 200, sem token, pelo cliente nativo do Windows com verificação TLS. O cliente Python apresentou `SSLCertVerificationError`, código 20. Isso prova uma diferença entre clientes/cadeias de confiança neste ambiente; não prova que o serviço esteja fora do ar. Não foi desativada a verificação de certificados nem instalado pacote.

Metadados identificam a New York State Gaming Commission como responsável. A data tem tipo `calendar_date`; o texto `T00:00:00.000` não é horário real do sorteio. A licença específica não veio preenchida nos campos `licenseId/license`; acesso público sem chave não foi tratado como autorização irrestrita.

Foram consultados os intervalos posteriores às fronteiras locais, com ordenação por data, limites explícitos e no máximo 200 linhas por pedido:

| Série | Janela consultada | Linhas/datas únicas | Comparação com Texas |
|---|---|---:|---|
| Powerball principal + Power Play | 27/12/2025–26/10/2026 | 131/131 | Zero divergências de números principais, Powerball e fator |
| Mega Millions principal | 26/12/2025–23/10/2026 | 87/87 | Zero divergências de números principais e Mega Ball |
| Double Play no mesmo retorno Powerball | Mesma janela Powerball | 63 com formato válido; 68 ausentes | A coluna começa preenchida em 03/06/2026 nesta amostra. Não inferir que o jogo começou nessa data |

As contagens agregadas retornadas pelo servidor também foram preservadas. A API distingue os seis números Powerball principais e os seis Double Play em campos diferentes. No Mega Millions atual, o campo de multiplicador pode não vir; não inserir zero ou um fator inventado.

**Recomendação:** qualificar o cliente Python no ambiente de implantação com cadeia de certificados correta, sem `verify=False`. Windows 200 não certifica o futuro executor Linux. Usar filtro temporal e revisita de resultados recentes, com cursor por fonte e conteúdo idempotente. Correções não devem depender apenas de buscar datas posteriores ao último registro.

### Colorado: enriquecimento real, mas limitado por território e período

Os botões oficiais exportaram XLSX reais de 14 dias: seis sorteios Powerball em 61 colunas e quatro Mega Millions em 88 colunas. Os arquivos incluem combinações, jackpot, cash value e campos de ganhadores/premiação do Colorado; Powerball acrescenta Double Play. A URL pública é construída pelo botão com `xlsx=1` e instante de consulta. A página também oferece intervalo `sincestart`, mas a exportação integral, cobertura histórica e alterações de layout não foram testadas.

Ganhadores `CO` são estaduais, não totais nacionais. O jackpot Powerball de 26/10 veio como USD 687 milhões, enquanto uma observação anterior da página central registrou USD 691 milhões. Os valores foram capturados em contextos/instantes diferentes e não foram reconciliados. Conservar as observações, em vez de eleger silenciosamente um valor como pagamento definitivo. Números concordantes não certificam a equivalência de financeiros.

Para completar os 68 Double Play ausentes em NY, o próximo coletor deve provar a cobertura correspondente no Colorado ou noutra fonte oficial antes de chamar a série de completa. A amostra de 14 dias comprova o formato e o resultado recente, não resolve essa lacuna inteira.

### EuroMillions: recuperação oficial e complemento austríaco

A página FDJ fornece seis links de partições, descobertos novamente e registrados no manifesto. As coberturas anunciadas abrangem fevereiro/2004–maio/2011, maio/2011–fevereiro/2014, fevereiro/2014–setembro/2016, setembro/2016–fevereiro/2019, março/2019–fevereiro/2020 e fevereiro/2020–atual. Na implementação, conferir fronteiras/datas efetivas e mudanças de cabeçalho de cada arquivo; nomes de períodos sobrepostos não provam duplicação ou continuidade. Não fixar o UUID da partição como contrato eterno.

O CSV anual [austríaco de 2026](https://statics.win2day.at/media/NN_W2D_STAT_EUML_2026.csv) respondeu 200. Contém 86 sorteios, 02/01–27/10/2026, todos iguais à FDJ em data, cinco números e duas estrelas. São 1.118 linhas de faixas, 13 por sorteio, mais cabeçalho; não 1.118 concursos. A data/números aparecem na primeira linha do bloco. Encoding testado CP1252, incompatível com UTF-8 estrito, sem afirmar exclusividade desse encoding.

As colunas distinguem ganhadores Europa/Áustria e quota. `JP` é marcador de jackpot, não contagem numérica. Em 27/10 a quota de uma faixa contém instrução textual de transferência para outro rank. Esses casos não são dinheiro zero ou falha genérica de parsing. Não habilitar análises de retorno financeiro antes de qualificar essa semântica.

A [Loterie Nationale belga](https://www.loterie-nationale.be/nos-jeux/euromillions/resultats-tirage/statistiques) anuncia CSVs anuais de resultados e financeiros desde o início. A consulta Python da página respondeu 405; o CSV não foi obtido. É uma pista para investigação dirigida, não fonte já qualificada nem prova de arrecadação pan-europeia.

## O que “atualizar por completo” deve significar no produto

1. **Resultados principais completos até a fronteira observada:** seis séries com datas/IDs sem lacunas inexplicadas, números especiais corretos e regras históricas. É a primeira meta de dados, com prova por conjunto.
2. **Séries vinculadas completas no período declarado:** Power Play/Megaplier conforme vigência; Double Play com cobertura própria. Ausência do campo numa fonte não prova ausência do sorteio.
3. **Complementos financeiros com cobertura explícita:** identificar faixas, ganhadores, reservas, jackpot anunciado, cash/annuity, moeda e território. Não confundir completude de números com completude financeira.
4. **Atualização recorrente comprovada:** coleta real, validação, reconciliação, aprovação, retomada e atraso visível. O instante da última tentativa não substitui o último dado confirmado.

Não há evidência suficiente para prometer uma fonte única gratuita com **todo campo histórico de todas as jurisdições**, arrecadação nacional americana e total pan-europeu por sorteio. Horários efetivos históricos e certos campos financeiros continuam indisponíveis/pendentes de contrato. A interface deve mostrar essa cobertura, sem inventar valores nem impedir análises numéricas que já tenham dados suficientes.

## Sugestão de próximo trabalho

**Antecipar o bloco de recuperação e reconciliação de dados já previsto nas SPECs 0033/0034**, como uma entrega funcional única com as seis loterias, antes do painel analítico. É uma recomendação desta revisão, não reordenação executada ou nova SPEC.

Critérios concretos para esse bloco:

- Guardar capturas novas separadas dos originais, com hash, origem, período, contrato e instante. A tabela de disponibilidade anterior vira entrada, sem novo inventário.
- Resolver o transporte CAIXA e qualificar o JSON atual. Importar históricos antigos já aprovados e completar somente a diferença, confrontando sobreposições.
- Qualificar NY no executor real; compor o resultado principal e fazer reconciliação com Texas. Tratar as 68 ausências Double Play como trabalho identificável, com fonte complementar e conferência de intervalo.
- Usar a partição recente FDJ para a defasagem e preparar reconciliação posterior dos seis arquivos oficiais para elevar a proveniência do legado EuroMillions. Qualificar Áustria/Colorado por medida e período, sem trocar automaticamente pagamentos entre países.
- Gravar/auditar/aprovar os conjuntos no armazenamento persistente, com contagens, fronteiras, lacunas e ausência de campos visíveis. Atualizar o catálogo SQL deliberadamente e preservar os manifestos antigos.
- Comprovar atualização idempotente e ao menos uma execução real por fonte antes de habilitar o agendamento. Confirmar condições aplicáveis de uso; gratuidade/acesso sem chave não substituem essa verificação. A API MUSL é alternativa estruturada com cadastro de chave, sem gratuidade ou liberação presumidas; nenhum pedido foi enviado.

O primeiro fluxo online da SPEC-0033 e a atualização das seis modalidades da SPEC-0034 continuam planejados. Esta revisão não implementa banco, novos adaptadores ou agendamento. O ganho é substituir dúvidas genéricas por fontes e casos de teste concretos, mantendo SDD e Compounding Engineering sem criar outra sequência de microtarefas.

## Evidências e preservação

O manifesto registra receipts, representação salva, hashes e comparações. Os JSONs obtidos via PowerShell foram salvos a partir do conteúdo de resposta reencodado em UTF-8; seus hashes certificam esses arquivos, sem alegar equivalência ao fluxo de bytes comprimidos da rede. XLSX/CSV preservam os bytes das respostas correspondentes.

Os testes novos verificam os perfis amostrados e comparações offline: **15 passaram em 1,18 segundo**. Os 50 testes existentes foram executados antes dessa adição, totalizando 65 testes distintos aprovados, sem repetir carga SQL/auditoria integral dos históricos. Dos 303 arquivos preexistentes registrados, 300 ficaram idênticos por hash e três documentos receberam referências/aprendizados desta revisão. Código de produção, migrations, arquivos brutos e relatórios anteriores ficaram preservados. Resultados e conferência constam do manifesto.
