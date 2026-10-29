# Aprendizados de engenharia

## Propósito

Registrar descobertas reutilizáveis para que cada etapa torne as seguintes mais seguras e rápidas. Novos aprendizados devem indicar evidência, impacto e ação futura.

## SPEC-0001 — Inventário dos dados

### L-001 — Não existe um formato universal de sorteio

**Evidência:** os arquivos contêm sorteios com 15 números, 6 números, 5 números mais uma bola e 5 números mais duas estrelas, além de trevos.

**Impacto:** modelos fixos como `n1` a `n6` perdem semântica e descartam dados.

**Ação futura:** a SPEC-0002 deve separar números principais de grupos especiais nomeados e permitir cardinalidade configurável.

### L-002 — Regras precisam ser versionadas no tempo

**Evidência:** séries históricas de Powerball e Mega Millions possuem valores acima dos limites atuais aparentes, sem outros sinais de corrupção.

**Impacto:** validar todo o histórico com a regra atual gera falsos positivos e pode destruir dados válidos.

**Ação futura:** associar cada concurso à versão de regra válida na sua data e testar transições de regra.

### L-003 — Arquivo bruto deve ser imutável e rastreável

**Evidência:** os dados atuais não carregam, junto ao arquivo, URL efetiva, instante da coleta, resposta HTTP ou versão do coletor.

**Impacto:** fica difícil provar origem, comparar versões ou reproduzir um processamento.

**Ação futura:** toda ingestão deverá registrar hash, fonte, horário, versão do adaptador e resultado da coleta antes da normalização.

### L-004 — Ausência pode ser condicional, não defeito

**Evidência:** `Cidade / UF` tende a estar vazia quando não há ganhador principal nas planilhas brasileiras.

**Impacto:** métricas simples de completude podem classificar corretamente um campo não aplicável como erro.

**Ação futura:** regras de qualidade devem distinguir `ausente`, `não aplicável`, `desconhecido` e `zero`.

### L-005 — Zero não equivale a dado ausente

**Evidência:** contagens de ganhadores e alguns prêmios possuem zero legítimo.

**Impacto:** filtros baseados em valor verdadeiro/falso podem apagar informação válida.

**Ação futura:** parsers e validadores devem tratar `0`, `null` e texto vazio separadamente; adicionar testes de regressão.

### L-006 — HTML de apresentação não é contrato de dados

**Evidência:** as linhas americanas misturam bolas principais, multiplicador e Double Play em quantidades variáveis.

**Impacto:** selecionar todos os elementos `<li>` como se fossem uma única lista de números produz concursos incorretos.

**Ação futura:** criar fixtures por período e testes de contrato antes de implementar o adaptador; pesquisar fonte oficial estruturada.

### L-007 — Campos financeiros exigem unidade e semântica

**Evidência:** existem valores como texto em BRL, jackpots em `Million`/`Billion` e números sem moeda no JSON.

**Impacto:** converter apenas o valor numérico permite misturar moedas ou prêmio pago com estimativa.

**Ação futura:** todo valor deve guardar montante decimal, moeda, tipo e referência do concurso.

### L-008 — Identificador da fonte não deve virar chave canônica sem contrato

**Evidência:** os `id` do EuroMillions têm grandes saltos e `draw_id` não possui semântica documentada; os HTMLs americanos não trazem ID explícito.

**Impacto:** uma chave mal escolhida pode causar colisões, falsos concursos ausentes ou duplicação.

**Ação futura:** definir identidade canônica na SPEC-0002 e preservar identificadores externos como referências de origem.

### L-009 — Qualidade precisa ser mensurável

**Evidência:** contagens de duplicidade, ausência e limites permitiram separar problemas reais de hipóteses.

**Impacto:** avaliações apenas descritivas não formam uma linha de base reproduzível.

**Ação futura:** transformar verificações aprovadas em testes automatizados durante a implementação dos normalizadores.

### L-010 — Um bug descoberto deve gerar proteção permanente

**Regra de Compounding Engineering:** toda correção futura de parser ou regra deverá incluir uma amostra mínima do caso, um teste de regressão e atualização deste registro quando produzir aprendizado reutilizável.

## Regras de continuidade

- Não corrigir silenciosamente o dado bruto; preservar original e registrar transformação.
- Não introduzir fallback fictício para ausência de histórico.
- Automatizar verificações repetitivas quando passarem de descoberta para produção.
- Registrar decisões que alterem contratos de dados antes da implementação.
- Reavaliar este documento ao concluir cada especificação.

## Próximo aprendizado esperado

A SPEC-0002 converteu as diferenças observadas em invariantes e decisões explícitas de modelagem, mantendo a implementação fora do escopo.

## SPEC-0002 — Modelo canônico versionado

### L-011 — Identidade interna e identidade externa têm funções diferentes

**Evidência:** algumas fontes possuem número oficial consistente, outras possuem IDs sem contrato conhecido e outras não trazem ID.

**Impacto:** uma única chave natural não atende todas as loterias.

**Ação futura:** usar identidade interna opaca e preservar referências externas com namespace e fonte.

### L-012 — Regra matemática e calendário devem evoluir separadamente

**Evidência:** dias de sorteio podem mudar ou possuir exceções sem alteração dos limites numéricos.

**Impacto:** unir regra e agenda em uma única versão provoca revisões artificiais e dificulta auditoria.

**Ação futura:** manter `LotteryRuleVersion` e `ScheduleVersion` como conceitos separados.

### L-013 — Correção de fonte é uma nova interpretação

**Evidência:** fontes podem corrigir concursos depois da primeira captura.

**Impacto:** sobrescrever o concurso elimina a capacidade de explicar mudanças em análises históricas.

**Ação futura:** implementar revisões imutáveis de concurso ligadas ao raw e promover explicitamente uma revisão atual.

### L-014 — Extensibilidade não elimina código específico de integração

**Evidência:** XLSX, JSON e HTML possuem estruturas, paginação e semânticas diferentes.

**Impacto:** prometer cadastro totalmente dinâmico produziria configuração excessivamente genérica e difícil de testar.

**Ação futura:** tornar regras e metadados configuráveis, mas exigir adaptadores homologados para comportamentos de fonte inéditos.

## Próximo aprendizado esperado

A SPEC-0003 comprovou que o contrato conceitual pode ser representado com tipos da biblioteca padrão, sem dependência de banco ou framework web.

## SPEC-0003 — Contratos tipados e validação

### L-015 — Definição inválida e dado inválido pedem tratamentos diferentes

**Evidência:** uma regra com períodos sobrepostos é erro de configuração; um concurso com uma bola fora do limite é dado que precisa de diagnóstico e possível quarentena.

**Impacto:** usar apenas exceções impediria reunir todos os problemas de um registro; aceitar definições ruins contaminaria toda a validação.

**Ação futura:** continuar falhando cedo para definições impossíveis e acumular `ValidationIssue` para dados ingeridos.

### L-016 — O domínio pode permanecer independente de infraestrutura

**Evidência:** as seis modalidades foram representadas e validadas apenas com dataclasses, enums e tipos padrão.

**Impacto:** banco, API e parsers poderão depender do domínio sem o domínio depender deles.

**Ação futura:** manter imports de infraestrutura fora de `app/domain` e adicionar teste arquitetural se essa fronteira crescer.

### L-017 — Um fluxo vertical deve preceder a generalização dos parsers

**Evidência:** os contratos estão estáveis o suficiente para receber um caso real, mas XLSX, JSON e HTML têm riscos muito diferentes.

**Impacto:** implementar seis normalizadores simultaneamente esconderia erros do contrato e aumentaria retrabalho.

**Ação futura:** validar primeiro uma amostra da Mega-Sena de ponta a ponta, sem banco, antes de extrair abstrações compartilhadas.

## Próximo aprendizado esperado

A SPEC-0004 demonstrou como uma linha bruta real se transforma em candidato canônico, preservando origem, zero, ausência e erros sem modificar a fonte.

## SPEC-0004 — Normalizador da Mega-Sena

### L-018 — Separar leitura e normalização reduz o custo dos testes

**Evidência:** o normalizador recebe um mapeamento simples e pode ser testado com três fixtures, enquanto apenas um teste precisa abrir o XLSX.

**Impacto:** regras de negócio não dependem do mecanismo de planilha e falhas ficam mais fáceis de localizar.

**Ação futura:** manter leitores responsáveis por extração e normalizadores responsáveis por semântica.

### L-019 — Cabeçalho deve ser identificado por nome normalizado

**Evidência:** acentos apareceram degradados em alguns leitores durante a SPEC-0001.

**Impacto:** usar posição fixa ou correspondência literal frágil quebraria com pequenas diferenças de encoding.

**Ação futura:** mapear aliases normalizados, exigir campos essenciais e testar alterações conhecidas de cabeçalho.

### L-020 — Idempotência pode ser testada antes do banco

**Evidência:** concurso oficial fornece chave determinística e duas normalizações idênticas produzem o mesmo resultado.

**Impacto:** a futura persistência poderá usar esse contrato em vez de inventar identidade durante a escrita.

**Ação futura:** verificar unicidade das 2.954 chaves antes de modelar constraints físicas.

### L-021 — Dinheiro inválido não deve virar zero

**Evidência:** o parser consegue preservar o texto de origem e marcar o montante como desconhecido.

**Impacto:** análises financeiras futuras não confundem falha de parsing com valor real nulo.

**Ação futura:** reutilizar e ampliar testes de formatos monetários nas fontes seguintes.

### L-022 — Metadados estruturais do XLSX também precisam de teste de contrato

**Evidência:** o arquivo da Mega-Sena declara dimensão `A1:T1`, apesar de conter 2.954 linhas. O leitor otimizado inicialmente confiou nesse metadado e retornou somente o cabeçalho.

**Impacto:** abrir o arquivo sem erro não prova que suas linhas foram lidas.

**Ação futura:** redefinir dimensões nesse leitor e manter teste que exige concursos reais; verificar o mesmo comportamento antes de reutilizar o leitor em outras planilhas.

## Próximo aprendizado esperado

A SPEC-0005 confirmou os contratos e aliases nas 2.954 linhas históricas da Mega-Sena, com baseline coincidente e nenhum problema de parsing neste snapshot.

## SPEC-0005 — Histórico completo da Mega-Sena

### L-023 — Parseável não significa semanticamente certificado

**Evidência:** 1.069 registros possuem arrecadação parseável de `R$0,00`, inclusive em períodos históricos da exportação.

**Impacto:** chamar esses valores de receita realmente zero sem pesquisar a fonte distorceria análises financeiras.

**Ação futura:** distinguir disponibilidade da fonte e validade semântica em análises; preservar os zeros e confirmar sua interpretação antes de utilizá-los.

### L-024 — Baseline e saúde são verificações diferentes

**Evidência:** comparar somente contagem e período não impediria que um novo parsing produzisse candidatos inválidos.

**Impacto:** uma baseline coincidente não basta para aprovar a carga.

**Ação futura:** exigir conjuntamente conciliação, fonte inalterada, ausência de problemas e unicidade. Testar duplicidade, entrada vazia e fonte alterada.

### L-025 — Relógio operacional não deve alterar hash do conteúdo

**Evidência:** duas capturas locais com instantes diferentes representam os mesmos concursos e produzem o mesmo relatório.

**Impacto:** incluir o instante da execução no hash confundiria reprocessamento com correção de dados.

**Ação futura:** versionar hashes e separar metadados operacionais do conteúdo canônico, sem atribuir horário fictício ao download antigo.

## Próximo aprendizado esperado

A SPEC-0006 deverá testar o que realmente pode ser reutilizado no formato da Lotofácil (15 números e cinco faixas), antes de extrair abstrações comuns de ingestão.

## SPEC-0006 — Histórico da Lotofácil

### L-026 — Rateios históricos não devem ser constantes da regra atual

**Evidência:** rateio de 11 acertos varia de R$2,00 no concurso 1 a R$7,00 no 3571.

**Impacto:** inferir valores atuais corrompe cálculos financeiros históricos.

**Ação futura:** conservar o valor por concurso e pesquisar versões oficiais antes de análises de premiação.

### L-027 — Campo estruturado e observação podem discordar

**Evidência:** no concurso 1, estimativa estruturada é zero enquanto a observação informa R$250.000,00.

**Impacto:** parsing válido não resolve conflito semântico.

**Ação futura:** manter ambas as evidências e pesquisar a fonte, sem substituir silenciosamente o campo nem extrair números de texto livre indiscriminadamente.

### L-028 — A agregação é reutilizável antes do adaptador

**Evidência:** o relatório da SPEC-0005 agrega grupos e faixas nomeados, e aceitou a baseline da Lotofácil sem alterar o comportamento da Mega-Sena.

**Impacto:** reutilização limitada evita um framework prematuro. O módulo ainda tem nome legado e os resultados específicos são estruturalmente compatíveis.

**Ação futura:** a auditoria da Lotofácil reaproveita só a agregação, substituindo versão e identificando a loteria. Parsers específicos continuam locais, incluindo tratamento de dinheiro numérico/finito e validação de cabeçalhos. Eventual extração comum deve ter sua própria SPEC e regressões para ambas as loterias.

## Próximo aprendizado esperado após SPEC-0006

A SPEC-0007 deverá demonstrar a preservação e validação independente dos trevos da +Milionária, antes de qualquer persistência.

## SPEC-0007 — Histórico da +Milionária

### L-029 — Uma categoria de acumulação não representa um montante

**Evidência:** “Acumulado 6 acertos + 2 Trevos” contém Sim/Não em 314 concursos.

**Impacto:** aplicar parser monetário descartaria informação ou fabricaria valor.

**Ação futura:** guardar atributo booleano com texto original, distinguindo ausência, desconhecido e falso. Pesquisar fonte própria para obter montante acumulado.

### L-030 — Unicidade é local ao componente e faixas podem agregar condições

**Evidência:** trevos usam intervalo 1–6, sobreposto ao das bolas, e três faixas combinam “1 ou nenhum trevo”.

**Impacto:** unir oito valores perde significado; separar faixas agregadas inventa dados.

**Ação futura:** validar main/clovers independentemente e preservar combinações de premiação exatamente como fornecidas. Testes cobrem sobreposição entre grupos e trevos invertidos, sem ordenar silenciosamente.

### L-031 — Dados inválidos precisam ser interceptados antes do construtor

**Evidência:** tipos de domínio rejeitam montantes/ganhadores negativos na construção.

**Impacto:** um parser que apenas converte tipos pode interromper o lote, em vez de produzir diagnóstico.

**Ação futura:** o adaptador da +Milionária intercepta esses casos e registra problemas, preservando o candidato quando há identidade. Primitivas locais da Lotofácil foram reutilizadas sem alterar módulos anteriores. Esse acoplamento interno deve ser protegido por regressões até uma SPEC própria de extração de código comum.

## Próximo aprendizado esperado após SPEC-0007

A SPEC-0008 deve testar o HTML histórico da Powerball antes de generalizar leitores, mantendo Power Play e Double Play fora do grupo principal.

## SPEC-0008 — Contrato de extração da Powerball

### L-032 — Classes e blocos definem a semântica do HTML

**Evidência:** 3.742 linhas possuem 6, 7 ou 13 itens quando achatadas, mas formam exatamente três estruturas: simples, Power Play e Double Play.

**Impacto:** contar ou concatenar `li` transforma multiplicador e sorteio adicional em bolas.

**Ação futura:** selecionar primeiro bloco, `bonus`, `multiplier` e `extradraw` explicitamente; rejeitar classes e blocos desconhecidos. Fixtures cobrem as três formas.

### L-033 — Data pode ser identidade provisória, não número oficial inventado

**Evidência:** 3.742 links possuem caminhos de data distintos, mas o HTML não fornece número do concurso.

**Impacto:** criar sequência artificial confundiria identidade interna com um identificador externo inexistente.

**Ação futura:** usar namespace `drawing_path` e chave provisória por data, conciliando link e texto. Pesquisar identificador oficial antes da persistência.

### L-034 — Envelope observado não é versão de regra

**Evidência:** Powerball varia de 1 a 45; 860 linhas excedem o limite atual aparente 26 e pertencem a períodos antigos.

**Impacto:** uma regra única atual rejeitaria história válida; uma regra permissiva esconderia limites de cada época.

**Ação futura:** limitar a SPEC-0008 ao contrato/fixtures. A SPEC-0009 deve pesquisar versões oficiais antes da auditoria integral.

### L-035 — A finalidade financeira faz parte do dado

**Evidência:** o HTML apresenta valores Million/Billion como jackpot anunciado, sem ganhadores ou pagamento realizado.

**Impacto:** armazenar apenas o número permitiria tratá-lo indevidamente como prêmio pago ou arrecadação.

**Ação futura:** usar `advertised_jackpot`, Decimal, USD e texto original; manter origem contextual pendente de confirmação oficial.

## Próximo aprendizado esperado após SPEC-0008

A SPEC-0009 deve transformar pesquisa oficial em versões de regra datadas e decisão de fonte, eliminando o envelope provisório antes da carga completa.

## SPEC-0009 — Regras históricas e fontes da Powerball

### L-036 — Regra de números, recurso comercial e calendário são eixos independentes

**Evidência:** há sete matrizes desde 1992; Power Play começa em 2001, passa por período sem multiplicador sorteado e retorna em 2014; Double Play e a segunda-feira começam em 2021 sem mudança da matriz 69/26.

**Impacto:** uma única “versão da loteria” produziria combinações artificiais ou duplicação de regras.

**Ação futura:** versionar componentes e capacidades por vigência, compondo a regra aplicável na data do sorteio.

### L-037 — Fonte de transporte não é necessariamente autoridade

**Evidência:** a API estruturada da MUSL é primeira parte, mas seus termos declaram que o feed não representa a informação oficial; as páginas de resultado dizem que o registro oficial do sorteio prevalece.

**Impacto:** escolher apenas por conveniência técnica pode transformar um feed corrigível ou limitado na verdade do domínio.

**Ação futura:** usar API como candidata de coleta, resultado oficial para verificação e proveniência completa para divergências.

### L-038 — Ausência pode ser uma regra histórica válida

**Evidência:** resultados de 2012-01-18 a 2014-01-18 não têm multiplicador Power Play porque o desenho usava prêmios fixos; antes de 2001 o recurso nem existia.

**Impacto:** representar ambos como `null` sem motivo mistura “não aplicável”, “regra sem sorteio do atributo” e “dado faltante”.

**Ação futura:** usar estados semânticos distintos e decidir obrigatoriedade pela data/regra, não pela presença global da coluna.

### L-039 — Uma data solicitada pode devolver outro sorteio

**Evidência:** a documentação da API MUSL informa que uma data sem sorteio retorna o desenho imediatamente anterior.

**Impacto:** coleta diária ingênua pode criar duplicatas ou associar resultado a uma data incorreta.

**Ação futura:** comparar sempre `drawDate` retornada com a esperada, tornar a ingestão idempotente por identidade externa/data real e testar dias sem sorteio.

## Próximo aprendizado esperado após SPEC-0009

A SPEC-0010 deve demonstrar que as sete regras reproduzem o histórico local sem falsos positivos e transformar exceções reais em diagnósticos versionados antes de qualquer integração de rede.

## SPEC-0010 — Histórico da Powerball

### L-040 — Versões numéricas podem ter lacunas legítimas

**Evidência:** as sete matrizes terminam no último sorteio antigo e começam no primeiro sorteio novo; entre eles existem dias sem desenho.

**Impacto:** estender uma versão até o início da seguinte afirma uma regra em datas sem evidência e pode aceitar registros fabricados.

**Ação futura:** usar intervalos explícitos e permitir que `rule_for` não encontre regra nas lacunas; calendário e vigência não devem ser confundidos.

### L-041 — Opcionalidade estrutural não substitui obrigatoriedade temporal

**Evidência:** Double Play compartilha a matriz atual, mas só existe desde 2021-08-23; declará-lo apenas opcional aceitaria sua ausência após o lançamento e sua presença antes dele.

**Impacto:** o schema isolado não expressa todas as condições de vigência de recursos independentes.

**Ação futura:** manter série separada e aplicar política temporal explícita até o modelo de capacidades versionadas ser consolidado.

### L-042 — Validação histórica elimina falsos positivos sem afrouxar limites

**Evidência:** 3.742 linhas passam nas sete regras; Powerballs até 45 são legítimas no início, enquanto o limite 26 continua estrito na versão atual.

**Impacto:** um envelope 1–45 atual seria permissivo demais e a regra 1–26 global rejeitaria 860 registros históricos válidos.

**Ação futura:** toda análise e persistência deve carregar `rule_version_label`; nunca escolher limites pelo máximo global observado.

### L-043 — Baseline válido não equivale a certificação externa

**Evidência:** todas as linhas e jackpots são internamente parseáveis, mas o snapshot é secundário e não contém ganhadores, faixas ou identificador oficial.

**Impacto:** “válido” pode ser interpretado incorretamente como “confirmado pela loteria”.

**Ação futura:** expor proveniência e nível de confiança; reservar estados de publicação/certificação para reconciliação oficial posterior.

## Próximo aprendizado esperado após SPEC-0010

A SPEC-0011 deve verificar se a Mega Millions repete os mesmos formatos ou introduz novas estruturas HTML, sem copiar automaticamente o adaptador da Powerball.

## SPEC-0011 — Contrato de extração da Mega Millions

### L-044 — HTML parecido não torna modalidades intercambiáveis

**Evidência:** Powerball e Mega Millions usam marcação semelhante, mas os componentes são Powerball/Power Play/Double Play versus Mega Ball/Megaplier, com caminhos e transições distintos.

**Impacto:** reutilizar o adaptador inteiro por substituição de nomes acoplaria regras e poderia aceitar estruturas exclusivas da outra loteria.

**Ação futura:** manter adaptadores específicos; extrair apenas primitivas comprovadamente idênticas em uma SPEC própria, protegida por regressões das duas modalidades.

### L-045 — Ausência reaparece depois de longa presença

**Evidência:** Megaplier é observado de 2003-12-05 a 2025-04-04, mas está ausente nos resultados seguintes, apesar de o jogo continuar.

**Impacto:** “campo opcional” ou “ausência significa pré-lançamento” são modelos insuficientes; a semântica depende de versões históricas.

**Ação futura:** pesquisar a mudança oficial de 2025 e criar estados por vigência antes da auditoria integral.

### L-046 — Estrutura desconhecida inclui blocos, não apenas classes

**Evidência:** a fonte atual tem exatamente um `ul`; um parser que só fiscaliza classes poderia ignorar silenciosamente um segundo sorteio ou recurso futuro.

**Impacto:** mudanças estruturais podem produzir dados aparentemente válidos, porém incompletos.

**Ação futura:** contar blocos semânticos e falhar diante de qualquer bloco adicional até que seu significado seja especificado.

## Próximo aprendizado esperado após SPEC-0011

A SPEC-0012 deve explicar oficialmente as matrizes, a mudança de nome e o fim do multiplicador sorteado em 2025, além de separar fonte automatizada de autoridade de verificação.

## SPEC-0012 — Regras históricas e fontes da Mega Millions

### L-047 — Mesmo nome lógico pode atravessar mudança de marca

**Evidência:** The Big Game torna-se Mega Millions em maio de 2002, preservando continuidade de resultados e participantes enquanto muda matriz/consórcio.

**Impacto:** usar nome de exibição como identidade fragmentaria a série histórica ou criaria duplicidade.

**Ação futura:** manter `mega_millions` como identidade estável e versionar nomes comerciais e regras por vigência.

### L-048 — Multiplicador do sorteio e multiplicador da aposta são fatos diferentes

**Evidência:** até 04/04/2025 havia um Megaplier sorteado; desde 08/04/2025 cada aposta recebe seu próprio fator incorporado.

**Impacto:** um único atributo `megaplier` no concurso fabricaria um valor pós-2025 ou misturaria resultado com configuração do bilhete.

**Ação futura:** encerrar o atributo do sorteio em 2025; representar possibilidades/distribuições no contrato de prêmios e fator individual somente no contexto de uma aposta.

### L-049 — Fonte oficial estruturada pode começar no meio da história

**Evidência:** o CSV do Texas é estável e oficial, mas começa em 2003, sete anos depois do primeiro resultado.

**Impacto:** escolhê-lo como fonte única apagaria duas matrizes e a transição inicial do Big Game.

**Ação futura:** manter cobertura explícita por fonte e reconciliar múltiplas fontes sem preencher períodos silenciosamente.

### L-050 — Mudança de coluna pode representar mudança real de domínio

**Evidência:** o CSV oficial remove a coluna Megaplier exatamente quando o recurso sorteado é aposentado em 2025.

**Impacto:** forçar schema estático transformaria uma mudança legítima em `missing` ou perderia a razão da ausência.

**Ação futura:** versionar contrato de fonte e semântica juntos; testar ambos os lados de cada fronteira.

## Próximo aprendizado esperado após SPEC-0012

A SPEC-0013 deve demonstrar que as sete matrizes e três estados do multiplicador reproduzem as 2.984 linhas sem afrouxar os limites nem inventar fator pós-2025.

## SPEC-0013 — Histórico da Mega Millions

### L-051 — O raw pode corrigir a fronteira sem certificar a regra

**Evidência:** há desenho em 1999-01-12 entre a última data inicialmente documentada e o início da matriz seguinte; ele ainda pertence ao envelope 50/25.

**Impacto:** uma data final incorreta produziria `rule_not_found` em dado legítimo, embora o conteúdo sozinho não prove toda a regra oficial.

**Ação futura:** confrontar sempre cada fronteira pesquisada com todas as datas locais, corrigir inconsistências antes da carga e manter confiança da fonte separada da consistência observada.

### L-052 — Ausências iguais podem exigir estados diferentes

**Evidência:** 682 sorteios anteriores ao Megaplier e 75 posteriores à sua aposentadoria não têm atributo, por razões opostas.

**Impacto:** `null` isolado perderia a diferença entre recurso inexistente e multiplicador transferido para a aposta.

**Ação futura:** persistir estado da capacidade por vigência e reservar atributos somente para fatos do sorteio.

### L-053 — Limite global observado enfraquece a regra atual

**Evidência:** Mega Balls chegam a 52 historicamente, mas a versão atual permite somente 24; todas as 2.984 linhas passam com limites versionados.

**Impacto:** usar 1–52 em toda a série aceitaria resultados atuais impossíveis.

**Ação futura:** exigir `rule_version_label` em análises, persistência e API, como já demonstrado na Powerball.

### L-054 — Mudança de significado não deve reutilizar a mesma chave

**Evidência:** `megaplier` representa um fator único sorteado; o mecanismo de 2025 representa fatores possíveis atribuídos a bilhetes.

**Impacto:** reaproveitar a chave criaria métricas e filtros semanticamente falsos.

**Ação futura:** modelar o mecanismo novo no contexto de prêmio/aposta em uma SPEC futura, sem adicioná-lo ao resultado do concurso.

## Próximo aprendizado esperado após SPEC-0013

A SPEC-0014 deve revelar o contrato real do JSON EuroMillions, especialmente estrelas, identificadores, moeda e possíveis variações entre países/fontes.

## SPEC-0014 — Contrato de extração do EuroMillions

### L-055 — Dois IDs únicos ainda podem ter semântica desconhecida

**Evidência:** `id` e `draw_id` são únicos, mas `id` salta de 1.996 para 3.943 em novembro de 2024 e `draw_id` segue convenção própria.

**Impacto:** unicidade técnica não prova que um campo seja número oficial ou sequência estável.

**Ação futura:** preservar namespaces externos e usar data provisoriamente; promover um ID somente após contrato/fonte oficial.

### L-056 — Número monetário sem unidade não é montante normalizado

**Evidência:** `prize` contém números precisos e zeros, mas o objeto não declara moeda, finalidade ou abrangência geográfica.

**Impacto:** atribuir EUR ou jackpot por contexto pode produzir análises financeiras incorretas.

**Ação futura:** conservar texto/número de origem como desconhecido e pesquisar semântica antes de preencher `amount` e `currency`.

### L-057 — Horário serializado pode ser apenas marcador de data

**Evidência:** todos os registros usam exatamente `00:00:00 GMT`, embora isso não demonstre que o sorteio ocorra à meia-noite.

**Impacto:** converter diretamente em instante oficial deslocaria datas e agendamentos futuros.

**Ação futura:** extrair somente a data civil; horário e timezone exigem fonte oficial independente.

### L-058 — Contrato JSON deve falhar também por evolução aditiva

**Evidência:** os 1.906 objetos têm exatamente sete campos, mas a API de terceiros pode adicionar um campo com nova semântica.

**Impacto:** ignorar silenciosamente adições esconderia recursos, versões ou mudanças de moeda.

**Ação futura:** diagnosticar campos extras e revisar conscientemente cada evolução de schema.

## Próximo aprendizado esperado após SPEC-0014

A SPEC-0015 deve substituir o envelope de estrelas por versões oficiais e decidir se `prize`, IDs e vencedor podem ser promovidos semanticamente ou devem permanecer apenas evidência da fonte secundária.

## SPEC-0015 — Regras, campos e fontes do EuroMillions

### L-059 — Código aberto da fonte resolve semântica, não autoridade

**Evidência:** o parser da API mostra que `prize` vem de “Prize Per Winner” da faixa 5+2 em um quadro PT/ES e que `has_winner` testa ganhadores dessa faixa; o README declara raspagem de site não oficial.

**Impacto:** agora sabemos o que os campos querem dizer, mas não podemos promovê-los a fatos oficiais sem reconciliação.

**Ação futura:** registrar separadamente semântica, cadeia de proveniência e autoridade; exigir fonte oficial para certificação.

### L-060 — Identificador determinístico ainda pode ser privado do provedor

**Evidência:** `draw_id` concatena ordinal anual e ano e coincide nas 1.906 linhas, enquanto `id` é uma sequência do PostgreSQL.

**Impacto:** estabilidade dentro do snapshot não transforma nenhum deles em número oficial do concurso.

**Ação futura:** preservar ambos com namespace externo e manter loteria + data como identidade até contrato oficial.

### L-061 — Prêmio pan-europeu e publicação nacional são dimensões distintas

**Evidência:** operadores publicam a combinação comum junto de jackpots, ganhadores totais, ganhadores locais, moedas de exibição e raffles nacionais.

**Impacto:** um único `prize`, `winner_count` ou `raffle_code` mistura níveis incompatíveis e inviabiliza reconciliação.

**Ação futura:** exigir escopo geográfico, operador, moeda e definição da métrica em todo fato financeiro; modelar extensões nacionais separadamente.

### L-062 — Partições oficiais podem revelar fronteiras de regra

**Evidência:** a FDJ divide os arquivos históricos em maio de 2011 e setembro de 2016, os mesmos pontos em que o snapshot muda de estrelas 1–9 para 1–11 e depois 1–12.

**Impacto:** a estrutura editorial da fonte pode ser evidência de versionamento, mas precisa ser conciliada com linhas limítrofes e regulamentos.

**Ação futura:** testar primeiro e último sorteio de cada partição e conservar a referência ao arquivo/regra que justificou a seleção.

## Próximo aprendizado esperado após SPEC-0015

A SPEC-0016 deve demonstrar que as três matrizes validam as 1.906 linhas sem usar o limite máximo global e que valores financeiros ausentes não são convertidos em zero legítimo.

## SPEC-0016 — Histórico do EuroMillions

### L-063 — Limite versionado transforma envelope em regra testável

**Evidência:** estrela 10 é inválida na versão 2004, estrela 12 é inválida na versão 2011 e válida desde 2016; as 1.906 linhas reais passam em sua versão.

**Impacto:** o antigo limite global 1–12 aceitava resultados historicamente impossíveis.

**Ação futura:** toda análise deve agrupar ou filtrar por `rule_version_label` quando o espaço amostral afetar probabilidades.

### L-064 — Zero conhecido no transporte pode ser desconhecido no domínio

**Evidência:** nove registros trazem `prize=0`, mas o campo significa pagamento individual da faixa principal e não há ganhador principal nessas linhas.

**Impacto:** persistir EUR 0 como valor conhecido criaria médias, mínimos e séries financeiras falsas.

**Ação futura:** modelar ausência/falha separadamente do número zero e preservar o texto original para auditoria.

### L-065 — Renomear no limite evita ambiguidade interna

**Evidência:** `has_winner` da fonte significa ganhador 5+2, não existência de qualquer premiado.

**Impacto:** manter o nome genérico permitiria consultas semanticamente erradas, pois quase todo sorteio tem ganhadores em alguma faixa.

**Ação futura:** adaptar nomes externos para conceitos explícitos no domínio e conservar o nome original apenas na camada raw/proveniência.

### L-066 — Lacunas de chave técnica não são lacunas históricas

**Evidência:** `source_id` tem 2.152 lacunas, mas datas, chaves canônicas e `draw_id` cobrem 1.906 sorteios únicos sem duplicidade.

**Impacto:** medir completude por sequência de chave interna geraria milhares de falsos concursos ausentes.

**Ação futura:** métricas de cobertura devem usar calendário, regra, data e identificador oficial quando existir; nunca PK do fornecedor.

## Próximo aprendizado esperado após SPEC-0016

A SPEC-0017 deve identificar o núcleo realmente compartilhado pelas seis loterias e quais diferenças precisam virar configuração versionada antes do desenho do banco e do cadastro administrativo.

## SPEC-0017 — Pesquisa oficial e enriquecimento das loterias

### L-067 — Cadastro de loteria é uma linha do tempo, não uma ficha estática

**Evidência:** a Mega Millions alterou em 08/04/2025 preço, quantidade de Mega Balls e multiplicador; calendários atuais da CAIXA também diferem do padrão histórico observado.

**Impacto:** sobrescrever a regra atual invalida resultados passados e probabilidades históricas.

**Ação futura:** versionar matriz, calendário, preço e premiação com vigência, fonte e data de observação.

### L-068 — Regra comum e regra territorial precisam de escopos separados

**Evidência:** Powerball compartilha somente o jackpot com o Reino Unido; Califórnia usa rateio próprio; EuroMillions combina resultado pan-europeu com raffles e preços nacionais.

**Impacto:** atribuir um preço, pagamento ou ganhador local ao jogo global gera fatos contraditórios.

**Ação futura:** tornar jurisdição e operador dimensões obrigatórias de fatos comerciais e financeiros.

### L-069 — Adicional de aposta não é necessariamente parte do resultado principal

**Evidência:** Power Play e o multiplicador da Mega Millions afetam bilhetes; Double Play é outro sorteio; My Million e Ireland Only Raffle são extensões territoriais.

**Impacto:** colocar todos como “bola extra” corrompe frequência, identidade e probabilidades.

**Ação futura:** catalogar componentes do resultado, recursos da aposta e sorteios vinculados como capacidades distintas.

### L-070 — Agenda tem pelo menos três relógios

**Evidência:** a FDJ publica limite de aposta, horário do My Million, horário do EuroMillions e horário de publicação; operadores americanos usam ET e a CAIXA publica horas locais.

**Impacto:** um único campo `draw_time` não permite agendar coleta nem diagnosticar atraso com segurança.

**Ação futura:** separar fechamento de vendas, sorteio e disponibilidade esperada, todos com timezone IANA e exceções de calendário.

### L-071 — Fonte oficial não implica contrato técnico oficial

**Evidência:** páginas da CAIXA revelam campos dinâmicos úteis, mas não documentam publicamente estabilidade, versionamento ou limite do endpoint que as abastece.

**Impacto:** depender diretamente desse transporte pode quebrar o pipeline sem aviso e pode contrariar condições de uso.

**Ação futura:** executar uma SPEC de qualificação de fonte antes de automatizar: contrato observado, termos, limites, fallback e monitoramento.

### L-072 — Modelo de prêmio precisa suportar fixo, rateado, garantido e reserva

**Evidência:** Lotofácil mistura pagamentos fixos e rateio; +Milionária mantém RGP; jackpots americanos oferecem caixa/anuidade; Califórnia aplica pari-mutuel.

**Impacto:** `prize_amount` isolado não explica natureza, abrangência nem forma de pagamento.

**Ação futura:** modelar tipo de cálculo, faixa, moeda, escopo, ganhadores, opção de pagamento e fundos acumulados separadamente.

### L-073 — Conteúdo oficial também pode ficar editorialmente inconsistente

**Evidência:** em 20/10/2026, páginas da Powerball ainda formulavam a expansão de 21/07/2026 como evento futuro.

**Impacto:** autoridade da fonte não elimina necessidade de data de captura, reconciliação e alerta de divergência.

**Ação futura:** guardar `observed_at`, evidência e estado de verificação; nunca atualizar fatos críticos por uma única sentença volátil.

### L-074 — Previsão deve ser um experimento auditável, não uma promessa

**Evidência:** os sorteios têm espaços combinatórios publicados e a própria FDJ alerta que o jogo não se presta realmente a prognósticos.

**Impacto:** métricas aparentes podem incentivar interpretação causal ou expectativa financeira sem evidência.

**Ação futura:** comparar modelos com baseline aleatório, evitar linguagem de garantia e exibir incerteza, probabilidades e jogo responsável.

## Próximo aprendizado esperado após SPEC-0017

A SPEC-0018 deve converter diferenças de matriz, vigência, jurisdição, agenda, prêmio e extensões em um contrato de catálogo configurável, preservando a distinção entre configuração documental e fonte operacional.

## SPEC-0018 — Catálogo configurável de loterias

### L-075 — Catálogo deve compor o domínio, não copiá-lo

**Evidência:** as seis loterias já possuíam 20 versões de regra testadas nos normalizadores.

**Impacto:** copiar matrizes para outra configuração criaria duas verdades capazes de divergir.

**Ação futura:** o catálogo referencia os objetos `Lottery` existentes; persistência deverá manter uma única autoridade por conceito.

### L-076 — Autoridade e prontidão de coleta são independentes

**Evidência:** páginas oficiais possuem regras confiáveis, mas contrato de transporte e uso ainda não foram qualificados; snapshots secundários já têm parsers testados.

**Impacto:** um booleano `official` não decide se a fonte pode operar automaticamente.

**Ação futura:** manter autoridade, finalidade e prontidão como campos distintos, com promoção auditável.

### L-077 — Vigência desconhecida não deve ser inventada

**Evidência:** conhecemos o calendário publicado em 20/10/2026, mas nem sempre a data exata em que ele começou.

**Impacto:** usar o início da loteria como início do calendário falsificaria expectativas históricas.

**Ação futura:** registrar `observed_at` e permitir vigência aberta até que fonte histórica confirme a fronteira.

### L-078 — Cadastro futuro precisa de estados e gates

**Evidência:** nome, matriz e URL são insuficientes para coleta segura; faltam licença, timezone, fixtures, limites e reconciliação.

**Impacto:** um CRUD irrestrito permitiria ativar configurações incompletas.

**Ação futura:** criar fluxo `draft → validating → active` com aprovação e critérios testáveis.

### L-079 — Jurisdição é uma relação, não uma coluna singular

**Evidência:** Powerball ganhou participação britânica apenas no jackpot e EuroMillions possui resultado comum com produtos nacionais.

**Impacto:** `jurisdiction_code` único é útil como origem, mas insuficiente para ofertas e fatos financeiros.

**Ação futura:** manter mercados no catálogo e projetar fatos financeiros com escopo territorial explícito.

### L-080 — Extensão pode ocupar mais de um eixo

**Evidência:** Double Play é simultaneamente produto opcional e série de resultado; Mega da Virada é concurso especial sem nova matriz de bolas.

**Impacto:** classificar tudo em uma única hierarquia perde comportamento operacional.

**Ação futura:** combinar tipo de extensão com séries, agenda e oferta, evitando herança rígida.

### L-081 — Previsão ambiciosa exige avaliação mais rigorosa, não menos ambição

**Evidência:** o objetivo do produto é prever da melhor forma possível, embora os sorteios sejam jogos de acaso sem garantia de acerto.

**Impacto:** sem baseline, separação temporal e reprodutibilidade, sobreajuste pode parecer avanço.

**Ação futura:** versionar datasets e experimentos, medir fora da amostra e comparar todo método matemático, IA ou ML com referências aleatórias e heurísticas.

## Próximo aprendizado esperado após SPEC-0018

A SPEC-0019 deve definir as fronteiras arquiteturais e os requisitos não funcionais que orientarão o primeiro fluxo operacional, sem antecipar complexidade distribuída.

## SPEC-0019 — Arquitetura de referência

### L-082 — Separação por processo não exige microsserviço

**Evidência:** API, coleta e experimentos têm ciclos de vida diferentes, mas compartilham domínio e transações ainda em evolução.

**Impacto:** executá-los no mesmo processo causa interferência; separá-los por rede agora adicionaria complexidade distribuída.

**Ação futura:** usar a mesma base modular em processos de API, worker e scheduler.

### L-083 — Legado funcional não é automaticamente fundação

**Evidência:** Flask, downloader e pipeline analítico atuais demonstram intenção, mas misturam I/O, configuração, UI e resultados não calibrados.

**Impacto:** ampliá-los consolidaria dívida e poderia publicar previsões sem validade.

**Ação futura:** mantê-los disponíveis durante substituições verticais, sem adicionar novas responsabilidades.

### L-084 — Fonte externa deve terminar numa porta de aplicação

**Evidência:** normalizadores novos são puros, enquanto o downloader legado escreve e imprime diretamente.

**Impacto:** acoplamento de rede, filesystem e parsing impede retomada e testes determinísticos.

**Ação futura:** aquisição salva raw; caso de uso entrega o artefato ao normalizador por interface.

### L-085 — Worker e scheduler possuem responsabilidades diferentes

**Evidência:** horário determina quando tentar, mas idempotência, repetição e reconciliação determinam como executar.

**Impacto:** regra dentro do cron produz execuções invisíveis e difíceis de retomar.

**Ação futura:** scheduler cria jobs persistidos; worker os reivindica e executa.

### L-086 — Publicação precisa ser transacional e revisionada

**Evidência:** fontes podem corrigir concursos depois da primeira publicação.

**Impacto:** atualização destrutiva quebra auditoria, caches e datasets.

**Ação futura:** criar nova revisão, promover ponteiro atual e emitir outbox na mesma transação.

### L-087 — Dataset é um produto versionado

**Evidência:** previsão reproduzível depende das revisões e do instante exato disponíveis no treino.

**Impacto:** consultar “dados atuais” depois do experimento permite correções futuras e vazamento temporal.

**Ação futura:** snapshots têm manifesto, corte temporal, hashes e versão da transformação.

### L-088 — Segurança de fonte inclui SSRF e conteúdo hostil

**Evidência:** o cadastro futuro aceitará URLs e o worker processará conteúdo externo.

**Impacto:** validação apenas do formato da loteria não protege rede interna, memória ou parser.

**Ação futura:** allowlist, limites, timeouts, redirects controlados, isolamento e validação de MIME/tamanho.

### L-089 — Meta só vira SLO quando pode ser medida

**Evidência:** disponibilidade, latência e atualização foram definidas inicialmente, mas ainda não existe telemetria.

**Impacto:** chamar intenção de SLO cria segurança operacional falsa.

**Ação futura:** instrumentar indicadores antes de assumir compromisso e revisar metas com dados reais.

### L-090 — Arquitetura limpa também exige saber o que adiar

**Evidência:** Redis, microsserviços, Kubernetes e lakehouse não resolvem um gargalo atual demonstrado.

**Impacto:** adotá-los agora aumentaria superfície de falha, custo e carga cognitiva.

**Ação futura:** manter gatilhos explícitos de adoção e preferir componentes substituíveis.

## Próximo aprendizado esperado após SPEC-0019

A SPEC-0020 deve revelar o contrato operacional real da fonte incremental da Mega-Sena: disponibilidade, idempotência, correções, limites, termos e comportamento de falha.

## SPEC-0020 — Coleta incremental unitária da Mega-Sena

### L-091 — Indicador de navegação não é identidade

**Evidência:** a API devolveu `ultimoConcurso=true` inclusive ao consultar explicitamente o concurso histórico 2954.

**Impacto:** usar essa flag como descoberta de novidade produziria decisões erradas.

**Ação futura:** verificar número solicitado, data e conteúdo semântico; conservar flags de transporte somente como evidência raw.

### L-092 — Bytes iguais e fatos iguais são verificações diferentes

**Evidência:** captura formatada e resposta HTTP preservam os mesmos fatos com bytes e representação decimal distintos.

**Impacto:** comparar apenas hash raw transforma mudanças de formatação em correções de concurso.

**Ação futura:** manter SHA-256 dos bytes para auditoria e hash do conteúdo normalizado para reconciliação.

### L-093 — Reprocessar captura antiga não pode reverter uma correção

**Evidência:** o teste cria uma correção candidata e depois reexecuta o receipt original.

**Impacto:** comparação ingênua somente contra o último conteúdo criaria uma terceira revisão revertendo o estado.

**Ação futura:** preservar origem por revisão e reconhecer replay de receipt já processado.

### L-094 — Evidência deve existir antes da interpretação

**Evidência:** respostas HTTP de erro, MIME inesperado e JSON inválido são arquivados e recebem diagnóstico.

**Impacto:** sem raw, alterações da fonte não poderiam ser investigadas ou reprocessadas.

**Ação futura:** arquivar resposta limitada, gerar receipt e só então interpretar; não confundir falha sem corpo com artefato capturado.

### L-095 — Novo no workspace não significa novo na história

**Evidência:** a primeira consulta unitária ao 2954 gera `new`, embora ele já exista no XLSX histórico.

**Impacto:** estatísticas de importação não podem afirmar novidade absoluta sem reconciliar com o conjunto histórico.

**Ação futura:** ligar bootstrap e cursor a uma baseline explícita e verificar cobertura separadamente.

### L-096 — Fonte respondendo não significa fonte operacionalmente aprovada

**Evidência:** duas amostras públicas responderam corretamente, mas não foram localizados contrato público, SLA ou limites de uso; robots retornou 404.

**Impacto:** estabilidade ou autorização de frequência não podem ser inferidas de poucos GETs.

**Ação futura:** manter estado `contract_observed`, limitar execução manual e documentar qualificação restante antes do scheduler.

### L-097 — Atomicidade local exige retomada explícita

**Evidência:** o teste interrompe a substituição do histórico; a revisão anterior permanece e a próxima execução conclui a correção. Receipts e outcomes são arquivos independentes.

**Impacto:** crash pode deixar raw órfão, receipt sem outcome ou lock residual, mesmo com gravação atômica por arquivo.

**Ação futura:** preservar receipts, garantir replay idempotente, exigir lock e migrar operações relacionadas para transações quando houver banco.

## Próximo aprendizado esperado após SPEC-0020

A SPEC-0021 deve provar que um lote limitado avança cursor somente sobre concursos processados, retoma depois de falhas e distingue recuperação de lacunas de revisão de concursos antigos.

## SPEC-0021 — Sincronização incremental limitada

### L-098 — Maior concurso observado não é fronteira de continuidade

**Evidência:** na execução real, a descoberta capturou 3071 enquanto o cursor só pôde avançar de 2954 para 2955.

**Impacto:** marcar o maior ID como processado esconderia 116 identificadores intermediários ainda não reconciliados.

**Ação futura:** manter cursor contíguo separado de último observado e de candidatos antecipados.

### L-099 — Baseline não é carga histórica

**Evidência:** o hash do XLSX auditado permite ancorar em 2954 sem povoar o workspace com suas linhas.

**Impacto:** declarar os 2.954 concursos importados confundiria referência de cobertura com persistência efetiva.

**Ação futura:** documentar cobertura declarada, cobertura materializada e publicação como estados distintos.

### L-100 — Checkpoint vem depois do efeito idempotente

**Evidência:** interrupção entre revisão salva e checkpoint deixa cursor anterior; a repetição reconhece conteúdo idêntico e conclui o avanço.

**Impacto:** antecipar o checkpoint perderia concursos silenciosamente após crash.

**Ação futura:** raw, validação, reconciliação e diagnóstico precedem o cursor; futura transação reunirá os efeitos compatíveis.

### L-101 — Revisar e avançar competem pelo mesmo orçamento

**Evidência:** testes com três GETs distribuem uma descoberta, um concurso novo e uma revisão recente.

**Impacto:** recuperar backlog sem reserva de revisão poderia adiar indefinidamente a busca de correções.

**Ação futura:** tornar a alocação explícita e manter ponteiro circular de revisão; orçamentos muito pequenos precisam declarar prioridade.

### L-102 — Respeitar rate limit exige estado entre execuções

**Evidência:** após HTTP 429, uma nova invocação lê o cooldown e não consulta a fonte.

**Impacto:** uma pausa apenas em memória seria ignorada por reinícios manuais ou scheduler.

**Ação futura:** persistir bloqueio temporário e qualificar `Retry-After` antes da operação recorrente.

### L-103 — Reutilização de descoberta reduz consultas sem pular validação

**Evidência:** ao alcançar o último concurso dentro do lote, os testes reutilizam seu resultado já validado e preservado.

**Impacto:** buscar novamente o mesmo concurso gastaria orçamento e abriria uma janela extra de divergência.

**Ação futura:** reutilizar evidência da mesma execução quando identidade e processamento já foram confirmados.

### L-104 — Checkpoint válido precisa de evidência correspondente

**Evidência:** ao remover a revisão que sustenta o cursor em um teste, a sincronização falha antes de fazer nova consulta.

**Impacto:** JSON de estado bem formado não prova que o efeito persistido ainda exista.

**Ação futura:** validar identidade/hash da fronteira e acrescentar auditoria completa do intervalo na próxima SPEC.

## Próximo aprendizado esperado após SPEC-0021

A SPEC-0022 deve produzir um diagnóstico determinístico que concilie baseline, cursor, revisões, receipts e artefatos, sem promover candidatos nem reparar evidência silenciosamente.

## SPEC-0022 — Auditoria de cobertura e recuperação

### L-105 — Integridade não equivale a completude

**Evidência:** o workspace real não possui inconsistências, mas seu cursor está em 2955 e o último capturado é 3071.

**Impacto:** um indicador verde único poderia sugerir dados atualizados quando só comprova coerência local.

**Ação futura:** expor saúde da evidência, cobertura, atualização e publicação como indicadores independentes.

### L-106 — A cadeia importa mais que arquivos isolados

**Evidência:** testes recalculam o hash de uma revisão alterada, mas sua reprodução a partir do raw original continua divergindo.

**Impacto:** conferir apenas nomes ou hashes autodeclarados deixaria passar interpretação adulterada.

**Ação futura:** verificar raw → receipt → normalização → revisão → outcome → cursor, usando constraints e referências físicas no banco.

### L-107 — A fronteira íntegra não garante o intervalo íntegro

**Evidência:** ao remover a revisão 2956 em teste com cursor 2957, a fronteira permanece válida e a auditoria ainda encontra a lacuna intermediária.

**Impacto:** a checagem rápida do sincronizador é necessária, mas insuficiente para recuperação e migração.

**Ação futura:** executar auditoria de todo o intervalo antes da carga definitiva ou restauração de backup.

### L-108 — Diagnóstico precisa sobreviver à corrupção que procura

**Evidência:** JSON truncado, chaves duplicadas e tipos inesperados são acumulados como problemas sem interromper os demais arquivos.

**Impacto:** reutilizar um loader que aborta na primeira falha esconderia a extensão da perda.

**Ação futura:** separar leitores operacionais estritos de leitores diagnósticos tolerantes a falhas, mantendo validação rigorosa do conteúdo.

### L-109 — Reprodução exige um manifesto estável

**Evidência:** o relatório inclui hashes e paths relativos, omite relógio de auditoria e foi idêntico em duas execuções reais.

**Impacto:** timestamps de execução e paths absolutos fariam mudanças ambientais parecer divergência de dados.

**Ação futura:** versionar relatório e normalizador, comparar manifesto antes/depois e auditar cópia estável quando houver concorrência.

### L-110 — Órfão é pista de interrupção, não autorização de exclusão

**Evidência:** testes simulam raw sem receipt e receipt sem outcome; ambos recebem ação manual, preservando seus bytes.

**Impacto:** limpeza automática eliminaria evidência necessária à investigação ou recuperação.

**Ação futura:** definir retenção/quarentena e procedimentos explícitos; não fabricar metadados para fechar uma cadeia perdida.

### L-111 — Distância do cursor não é quantidade de arquivos ausentes

**Evidência:** há 116 identificadores pendentes até 3071, mas 115 sem candidato, porque 3071 foi capturado antecipadamente.

**Impacto:** a mesma contagem usada para progresso, downloads e cobertura geraria relatórios contraditórios.

**Ação futura:** manter métricas explícitas de continuidade, materialização e pendência, com faixas compactas.

## Próximo aprendizado esperado após SPEC-0022

A SPEC-0023 deve converter a cadeia de evidências e suas invariantes em modelo lógico de persistência, incluindo transações, constraints e política de revisão sem perda de auditoria.

## SPEC-0023 — Modelo lógico e contrato de persistência

### L-112 — Blob e captura têm cardinalidades diferentes

**Evidência:** um mesmo raw pode ser observado mais de uma vez, e o workspace já possui múltiplos outcomes para a mesma captura.

**Impacto:** atrelar fonte e instante diretamente a um blob deduplicado apaga observações distintas.

**Ação futura:** separar raw_artifact, capture_receipt, interpretação e tentativa de processamento.

### L-113 — Data corrigível não deve ser identidade interna

**Evidência:** três loterias usam identidade provisória por data e podem ganhar identificador oficial ou correção futura.

**Impacto:** PK baseada em data exigiria reidentificar toda a cadeia ao corrigir um fato.

**Ação futura:** usar draw_id opaco, aliases reservados e data na revisão; conflitos exigem conciliação explícita.

### L-114 — Imutabilidade exige bloquear inserção tardia de filhos

**Evidência:** impedir UPDATE da revisão não impede acrescentar bolas ou dinheiro em outras tabelas.

**Impacto:** o hash poderia ficar incompatível com seu conteúdo sem alterar a linha principal.

**Ação futura:** selar revisão e bloquear INSERT/UPDATE/DELETE dos filhos de conteúdo após o selo; observar e decidir continua permitido.

### L-115 — Idempotência não significa proibir o retorno de um conteúdo

**Evidência:** replay antigo deve reutilizar interpretação, enquanto capturas novas podem trazer mudança legítima A → B → A.

**Impacto:** UNIQUE de hash por draw confundiria mudança real com repetição técnica.

**Ação futura:** deduplicar comandos e receitas; ordenar revisões por ocorrência e comparar hashes com versão.

### L-116 — Cursor e revisão precisam da mesma unidade de trabalho

**Evidência:** os testes locais comprovaram a janela de interrupção entre arquivos de revisão e checkpoint.

**Impacto:** apenas trocar o repositório por SQL preservaria a janela se o cursor fosse confirmado separadamente.

**Ação futura:** gravar observação, revisão, step e cursor em T3, com fencing token e compare-and-swap.

### L-117 — CHECK não substitui validação relacional de agregados

**Evidência:** cardinalidade de bolas e vigência dependem de definições em outras linhas; a documentação PostgreSQL não permite tratar CHECK como garantia geral entre tabelas.

**Impacto:** uma constraint aparentemente rigorosa poderia não proteger futuras alterações ou restaurações.

**Ação futura:** combinar FKs compostas, EXCLUDE, validação no domínio e poucos constraint triggers diferíveis.

### L-118 — Escolher escala SQL pode introduzir arredondamento oculto

**Evidência:** PostgreSQL arredonda valores que excedem a escala declarada em numeric(p,s).

**Impacto:** um valor que deveria ser rejeitado pode chegar já alterado à validação da linha.

**Ação futura:** usar numeric exato com checagem explícita de escala/finitude/envelope e testar a entrada inválida no banco real.

### L-119 — Publicação é um evento temporal com efeitos próprios

**Evidência:** revisão candidata pode divergir da publicada e uma correção posterior não estava disponível no corte de um backtest.

**Impacto:** consultar apenas a revisão mais nova mistura descoberta, aprovação e conhecimento disponível no tempo.

**Ação futura:** separar ponteiros e decisões; publicar com auditoria/outbox transacionais e snapshots analíticos por revisão e corte.

### L-120 — Contrato documental não equivale a garantia já implementada

**Evidência:** a SPEC-0023 define 37 cenários, mas ainda não existe PostgreSQL com constraints e transações verificadas.

**Impacto:** declarar integridade física antes das migrations criaria confiança sem evidência executável.

**Ação futura:** vincular cada cenário ao incremento responsável e registrar testes reais antes de considerar a garantia operacional.

## Próximo aprendizado esperado após SPEC-0023

A SPEC-0024 deve comprovar em PostgreSQL real a viabilidade das primeiras migrations, vínculos compostos, exclusões temporais e integridade das revisões do recorte escolhido.

## SPEC-0024 — Migrations e integridade comprovada em PostgreSQL

### L-121 — As seis modalidades cabem no mesmo recorte relacional

**Evidência:** catálogo de teste inseriu seis loterias/20 versões; fixtures reais das seis modalidades passaram por séries/componentes/atributos/finanças e selo no PostgreSQL 17.11.

**Impacto:** não é necessário duplicar tabelas por loteria nem antecipar cadastro administrativo completo.

**Ação futura:** mapper/repositório continuam genéricos na estrutura, com contratos de fonte e validação por modalidade/versão. Double Play é série; multiplicadores são atributos; clovers/stars são componentes.

### L-122 — Constraints físicas exigem distinguir erro pretendido de erro incidental

**Evidência:** um teste que alterava todas as faixas para a mesma definição provocou UNIQUE antes de chegar à FK que pretendia provar. O teste passou a alterar uma única faixa e conferir SQLSTATE 23503.

**Impacto:** apenas esperar “algum erro SQL” pode aprovar a proteção errada.

**Ação futura:** cenários negativos devem construir o conflito mínimo, verificar categoria/código e conferir o estado preservado.

### L-123 — Trigger compartilhado precisa respeitar a estrutura de cada registro

**Evidência:** CASE com `NEW.checkpoint_id` falhou no trigger de sync_checkpoint, mesmo quando o ramo aparentemente não seria escolhido. A resolução do campo é anterior à execução do ramo SQL.

**Impacto:** nomes válidos numa tabela não se tornam portáveis por condição baseada em TG_TABLE_NAME.

**Ação futura:** usar ramos PL/pgSQL separados ou extração explícita de contexto com to_jsonb; manter funções específicas para invariantes, não criar um motor de regras.

### L-124 — SQL nativo versionado não deve ser reinterpretado como parâmetros da aplicação

**Evidência:** SQLAlchemy `text()` interpretou `:1` dentro de um literal JSON como bind. Execução via driver com no_parameters preservou o SQL estático da migration.

**Impacto:** testes só das primeiras versões do DDL não cobririam mudanças em literais JSON/PLpgSQL.

**Ação futura:** migrations usam arquivos estáticos versionados e explicitamente sem parâmetros; comandos com valores da aplicação continuam parametrizados, nunca interpolados como SQL.

### L-125 — Papéis mínimos influenciam até os locks de integridade

**Evidência:** travar regra com SELECT FOR SHARE requer privilégio adicional que o ingestor não deve receber no catálogo. Duas funções específicas de validação/guard usam SECURITY DEFINER do migrador não superuser, search_path fixo e EXECUTE público revogado.

**Impacto:** desenvolver apenas como proprietário mascara problemas de permissão e incentiva grants excessivos.

**Ação futura:** cada fluxo deve rodar nos testes sob o papel real de serviço; futuras funções privilegiadas precisam revisão dedicada e escopo mínimo.

### L-126 — O lote de migrations também precisa ser atômico

**Evidência:** upgrade/no-op, head→base→head vazio e downgrade recusado em banco preenchido são exercitados em PostgreSQL. O ledger/estrutura são preservados com o lote em uma transação e lock consultivo até o último passo.

**Impacto:** “downgrade falhou” não basta se passos anteriores já apagaram estrutura/ledger.

**Ação futura:** rollback preenchido será forward/backup, não deleção de evidências; manter teste de recuperação junto de cada nova migration.

### L-127 — Executor Windows pode travar por pipe herdado, mesmo com servidor pronto

**Evidência:** pg_ctl iniciou o cluster, mas subprocess.run(capture_output=True) aguardou handles herdados pelo processo persistente. Redirecionar para control.log eliminou a espera; finally confere/desliga o cluster específico.

**Impacto:** um problema do harness pode parecer falha do PostgreSQL e deixar processos órfãos.

**Ação futura:** serviços auxiliares usam logs em arquivo, porta/identidade isoladas, autenticação e encerramento explícito; não tocar serviços existentes para viabilizar testes.

### L-128 — Integridade de schema não substitui comportamento transacional da aplicação

**Evidência:** FK/EXCLUDE/selo/dinheiro/checkpoint foram exercitados, mas replay, idempotência após timeout, concorrência entre escritores e publicação continuam sem repositórios/T5.

**Impacto:** contar tabelas ou testes não autoriza declarar toda a matriz DB-01…DB-37 aprovada.

**Ação futura:** SPEC-0025 será repositórios/UoW, com duas conexões e falhas controladas antes de importar históricos; publicar/canonicalizar todas as modalidades mantém gates próprios.

### L-129 — Falha de commit exige fechamento explícito da conexão

**Evidência:** o cenário de cooldown confirmado seguido de cursor rejeitado expôs ResourceWarning: no Psycopg 3.3.6 qualificado, `Connection.__exit__` chama commit antes de close e não chega ao fechamento se o commit levanta erro. O teste usa commit explícito e close em finally.

**Impacto:** confiar somente no caminho feliz do context manager pode vazar conexão justamente nas falhas diferidas de integridade.

**Ação futura:** UnitOfWork deve assegurar rollback quando aplicável e liberação em finally, inclusive quando commit/rollback falharem; testes de pool/recursos entram com o adaptador.

## Próximo aprendizado esperado após SPEC-0024

Comprovar que a escrita vertical preserva identidade, observações, revisões e cursor em T3 sob concorrência e retry, com o coletor externo fora da transação. Antes de carga, qualificar mapper/canonicalização e os vetores exigidos, sem renomear hashes legados.

## SPEC-0025 — Escrita transacional, concorrência e recuperação

### L-130 — A disputa da identidade deve preceder referências externas auxiliares

**Evidência:** a reconciliação cria o agregado em savepoint, disputa o alias oficial e só então registra referência por fonte. Duas conexões reais perderam/ganharam UNIQUE sem deixar draw/revisão órfãos.

**Impacto:** disputar outra UNIQUE antes do alias quebraria o ponto previsto de arbitragem e poderia tornar o tratamento do perdedor incorreto.

**Ação futura:** preservar a ordem ao adicionar identidades por slot/provedor; conflitos diferentes não devem ser capturados como se fossem o mesmo alias oficial.

### L-131 — Bytes órfãos não recuperam metadados HTTP que não chegaram ao commit

**Evidência:** interrupção explícita após PUT preserva bytes, mas nenhum receipt/status/instante foi confirmado. A mesma chave devolve capture_in_progress sem novo GET. Já o retorno perdido após T2 confirmado encontra a captura e continua sem download.

**Impacto:** tratar toda falha “após raw” como replay automático fabricaria proveniência ou repetiria aquisição ambígua.

**Ação futura:** auditoria SQL/storage deverá distinguir essas janelas; nunca preencher receipt retroativo apenas porque existe um arquivo por hash.

### L-132 — Replay e correção têm efeitos temporais diferentes

**Evidência:** receita antiga retorna sua observação/revisão mesmo após B; nova captura A volta como revisão 3. finished_at original da interpretação fica preservado; a nova tentativa registra o replay.

**Impacto:** mover head ou reescrever o instante original em replay contamina disponibilidade temporal e auditoria.

**Ação futura:** imports e análises guardam interpretação/observação/revisão exatas, não apenas “último processamento”.

### L-133 — Um formato canônico relacional exige escolhas explícitas

**Evidência:** vetor real 2954 inclui escopo, forma de pagamento e extração 2/6/1/5/3/4 sobre lista crescente, com dinheiro decimal exato. UUIDs/transporte/source_text não definem o hash; zero e desconhecido não se confundem.

**Impacto:** hash raw, hash semântico legado e hash relacional não são intercambiáveis.

**Ação futura:** qualificar vetores de XLSX e demais loterias antes da carga. Não assumir que a igualdade dos números prova igualdade de todas as informações.

### L-134 — Teste de concorrência deve observar bloqueio, não adivinhar tempo

**Evidência:** os testes coordenam duas conexões com eventos/barreira; pg_blocking_pids confirma que a segunda correção espera a primeira antes de liberá-la.

**Impacto:** resultado aparentemente certo numa execução sequencial não prova que o head foi lido depois do lock.

**Ação futura:** manter essas provas ao refatorar portas/repositórios; novos writers devem respeitar comando→checkpoint→receita→draw.

### L-135 — Confirmar T3 não torna aquisição externa atomicamente repetível

**Evidência:** retries SQL limitados reutilizam receipt/bytes; perda simulada da resposta de commit retorna efeito único com a mesma chave, sem novo GET. Chave reutilizada com outro pedido é conflito.

**Impacto:** retry genérico de todo o coletor misturaria transação abortada, commit incerto e aquisição externa.

**Ação futura:** orquestradores conservam intenção/chave/contexto de avanço; nunca retentar rede como efeito colateral de deadlock ou timeout de commit.

### L-136 — Cooldown e captura precisam sobreviver à falha de reconciliação

**Evidência:** 429 confirmado bloqueia nova intenção de GET mesmo sem baseline; com checkpoint, cooldown confirma em transação independente e permanece após T3 falhar. Replay offline continua possível.

**Impacto:** associar throttling ao rollback do candidato criaria um ciclo de novas chamadas justamente quando a fonte pediu espera.

**Ação futura:** manter arbitragem por fonte e política qualificada antes do scheduler; 15 minutos é proteção local, não regra oficial pesquisada.

### L-137 — Crescer a suíte muda o custo do próprio harness

**Evidência:** clones descartáveis isolaram casos sem TRUNCATE/desabilitar triggers, mas aumentaram fsync/checkpoint de shutdown. Primeira rodada aprovou testes e ultrapassou o limite de 30 s do executor; o servidor terminou depois.

**Impacto:** resultado da suíte e término seguro da infraestrutura são verificações diferentes.

**Ação futura:** runner usa buffers de teste menores, prazo de 55 s e verificação de encerramento, sem alterar serviços existentes nem desligar fsync para obter teste rápido artificialmente.

### L-138 — Schema compartilhado não elimina qualificação por modalidade/fonte

**Evidência:** o adaptador opera no mesmo schema de seis loterias, mas recusa catálogo incompatível com o JSON Mega-Sena; as outras modalidades continuam sem carga/mapper relacional aprovado.

**Impacto:** generalizar um mapper de uma fonte como se fosse universal repetiria problemas de IDs privados, estrelas históricas, multiplicadores e finanças já descobertos.

**Ação futura:** próximo incremento qualifica mapeamentos/vetores das seis fontes históricas antes da importação, extraindo abstrações compartilhadas quando houver consumidores comprovados.

## Expectativa registrada após SPEC-0025

Demonstrar representações fiéis para os seis históricos, com hashes/versionamento e estados de ausência explicáveis, antes de materializar baselines ou publicar resultados. Vetor JSON Mega-Sena aprovado não certifica XLSX, Powerball, Mega Millions ou EuroMillions por semelhança estrutural.

## SPEC-0026 — Qualificação dos mapeamentos históricos

### L-139 — Representável não significa importado, completo ou publicado

**Evidência:** 15.471 registros atravessaram os normalizadores e o novo contrato em memória; 45 vetores cobrem as 20 regras e estados relevantes. Nenhum deles foi carregado pelo novo mapper no PostgreSQL nesta etapa.

**Impacto:** a palavra “qualificado” sem indicar a camada da prova esconderia a diferença entre parser, representação, persistência, cobertura e publicação.

**Ação futura:** manter gates separados e exigir roundtrip/retomada em piloto antes de batch. Não promover baseline só porque a quantidade de linhas coincide com um relatório.

### L-140 — Fonte parcial não pode apagar enriquecimento de outra fonte

**Evidência:** Mega-Sena 2954 tem 12 grupos compartilhados iguais no XLSX/JSON, mas cinco grupos exclusivos do JSON, incluindo extração e fundo final 0/5. Mesmo sob o contrato histórico, os hashes completos diferem legitimamente.

**Impacto:** comparar apenas hashes classificaria apoio parcial como correção; substituir head pelo histórico poderia eliminar informações mais completas.

**Ação futura:** piloto deve distinguir apoio, enriquecimento e divergência real com ponte explícita. Não implementar merge genérico por interseção de dicionários nem assumir que ausência é remoção.

### L-141 — Versões de canonicalização são fronteira de compatibilidade

**Evidência:** o vetor JSON v1 continua com hash `62755ae7c8057839aa4fcb97c2840afbc6e0a296844f7b02fb6d66f81bbe6477`. O mapper histórico tem contrato próprio; o writer SQL atual recusa outra versão de propósito.

**Impacto:** trocar uma constante para permitir importação contornaria validação de roundtrip e reinterpretaria revisões seladas.

**Ação futura:** comparar representações transitórias explicitamente, preservando versões/hashes originais e decisões rastreáveis. Nenhuma recanonicalização destrutiva ou alteração de migrations antigas.

### L-142 — Deduplicar conteúdo não permite descartar evidência por observação

**Evidência:** IDs EuroMillions, textos financeiros, observações e datas textuais ficam em evidência separada com hash próprio. Nove zeros originais continuam observáveis, embora os montantes normalizados sejam unknown. Revisões e seus source_texts já são imutáveis no SQL.

**Impacto:** anexar apenas o texto da primeira captura à revisão perderia a origem de uma observação posterior sem mudança de conteúdo.

**Ação futura:** conservar raw + localizador + diagnostic_payload versionado por observação; não atualizar filhos selados para guardar uma nova fonte. Provar esse caminho no writer piloto, incluindo limites de payload.

### L-143 — Codificação do transporte é diferente da serialização canônica

**Evidência:** a primeira gravação dos vetores via stdout Windows cp1252 substituiu acentos; o teste de igualdade/evidence hash revelou o problema. A regeneração por JSON com escapes Unicode preservou o texto e passou a ter teste explícito de transporte.

**Impacto:** uma saída visualmente parecida pode não representar os mesmos bytes ou textos; hash calculado antes do transporte não certifica o artefato salvo.

**Ação futura:** validar o artefato efetivamente salvo. CLI de qualificação usa JSON escapado portável; hashes continuam sobre JSON canônico UTF-8/Unicode. Não modificar normalizadores ou raw para “corrigir” problema de terminal.

### L-144 — Localizador e instante de inspeção não são IDs/horários históricos

**Evidência:** vetores são localizáveis por arquivo/hash e ordinal emitido pelo leitor versionado. Nos HTMLs a ordem física é inversa à cronologia; no EuroMillions o timestamp GMT à meia-noite é da representação da data, não do sorteio. Instante original de download dos seis arquivos não está comprovado.

**Impacto:** confundir posição da linha, ID privado e sequência oficial contaminaria retomada, datas e futuras avaliações temporais de previsão.

**Ação futura:** guardar proveniência honesta de importação legada; usar aliases oficiais/provisórios já qualificados e cobertura própria para cada fonte. Instantes de disponibilidade devem ser comprovados antes de construir snapshots/backtests sem vazamento.

## Expectativa registrada após SPEC-0026

Demonstrar em um piloto SQL limitado que a mesma importação pode ser interrompida e retomada sem duplicar efeitos, apagar enriquecimentos JSON ou regredir head. Especificar primeiro a ponte de contratos e a evidência por observação; somente depois ampliar o volume e as modalidades.

## SPEC-0027 — Piloto histórico Mega-Sena

### L-145 — Apoio entre contratos não usa o hash da entrada como hash da revisão

**Evidência:** o trigger exige observação/processamento/revisão na mesma versão de canonicalização e hash. XLSX apoiando JSON usa versão/hash da revisão no vínculo; payload guarda contrato/hash de entrada, conteúdo e evidência independentes. O teste SQL prova que os hashes diferem e que nenhuma revisão foi reescrita.

**Impacto:** reutilizar semantic_hash para representar simultaneamente entrada e revisão violaria integridade ou falsificaria a evidência.

**Ação futura:** preservar a distinção ao integrar a ponte no coletor. Políticas que mudam a representação de comparação precisam de versão própria e não podem alterar hashes selados.

### L-146 — Uma política conservadora pode resolver ordem de chegada sem merge genérico

**Evidência:** JSON→XLSX produz apoio sem revisão; XLSX→JSON acrescenta revisão com enriquecimentos. Disputa real de duas conexões termina com uma identidade e head JSON completo; perdedor de UNIQUE não deixa draw órfão. Divergência financeira é quarentena e plano stopped.

**Impacto:** impor prioridade apenas pelo horário de importação ou por igualdade de hashes apagaria dados. Entrada que simultaneamente remove e acrescenta fatos não é enriquecimento comprovado.

**Ação futura:** manter os quatro resultados explícitos da ponte e testar known/unknown/correções antes de ampliar fontes. Não transformar a comparação em “merge inteligente” sem política de autoridade.

### L-147 — Retomada precisa sobreviver à perda dos objetos Python e do caminho original

**Evidência:** receipt legado conserva manifesto; raw é arquivado por hash. resume recupera manifesto/bytes, reconstrói os candidatos e verifica o fingerprint, inclusive após perda de resposta de COMMIT do registro. O caminho XLSX original não é consultado.

**Impacto:** reexecutar só o loop que ficou em memória seria um teste de repetição, não prova de recuperação do trabalho registrado.

**Ação futura:** próximos importadores recebem intenção persistida e evidência disponível; mudar seleção/versão/entrada com a mesma chave é conflito. Manifesto é validado contra os bytes, não aceito como autoridade autossuficiente.

### L-148 — Progresso do plano é diferente de validade de cada linha

**Evidência:** interrupção após a primeira linha deixa uma observação válida e run running; retomada confirma só as linhas restantes. Finalização só ocorre com todos os localizadores registrados; quarentena resulta stopped, não completed. Tempos originais ficam estáveis no replay.

**Impacto:** max(concurso) ou número de revisões não representam cobertura; apoio pode não criar revisão, e um concurso alto isolado não completa intervalo.

**Ação futura:** cobertura integral/baseline exige auditoria própria e não pode ser inferida do resumo do piloto. Manter cursor/checkpoint fora desta importação experimental.

### L-149 — Reutilizar storage não significa que todos os históricos cabem nele

**Evidência:** storage atual tem limite de 256 KiB. XLSX Mega-Sena deste recorte tem 221.261 bytes e coube integralmente; três linhas importadas ainda exigiram preservar o arquivo inteiro como evidência.

**Impacto:** aumentar a seleção de linhas e ampliar tamanho de artefatos são problemas diferentes. Relaxar o limite HTTP global para aceitar outro arquivo misturaria políticas.

**Ação futura:** antes de outras fontes/cargas maiores, definir limites por uso, verificação de arquivos e testes de recuperação. Não alterar proteção do coletor JSON como efeito colateral de um importador.

### L-150 — Ponte comprovada no piloto ainda precisa ser integrada ao fluxo existente

**Evidência:** o teste SQL 13 confirma que ProcessMegaSena continua recusando head histórico; o piloto aceita os dois contratos por caminho explícito. Os 27 cenários anteriores do writer JSON permanecem separados e preservados.

**Impacto:** carga integral antecipada poderia criar uma base que o fluxo incremental atual não consegue atualizar. Ativar a ponte silenciosamente evitaria o erro visível sem comprovar leases/cursor, correções e replay.

**Ação futura:** SPEC-0028 integra a ponte explicitamente ao fluxo incremental, com regressão de continuidade e política de correções; somente depois ampliar carga. Não declarar pronto o ambiente operacional pelo sucesso de fixtures em cluster descartável.

## Expectativa registrada após SPEC-0027

Comprovar que o fluxo incremental atualiza head histórico sem apagar informações nem quebrar correções, idempotência, replay, evidência e avanço atômico de cursor. O piloto reduz incerteza, mas não substitui essa prova de integração.

## SPEC-0028 — Ponte no fluxo incremental

### L-151 — Política entre fontes não substitui política de correção da mesma fonte

**Evidência:** JSON sobre histórico compatível gera enriquecimento; diferença compartilhada fica em quarentena. JSON→JSON mantém correções A→B→A, inclusive depois de a primeira revisão ter vindo do histórico. A ponte pura do piloto é reutilizada apenas onde sua política conservadora se aplica.

**Impacto:** usar a mesma regra conservadora em todo caso bloquearia correções JSON legítimas; aceitar tudo como correção entre fontes apagaria discrepâncias relevantes.

**Ação futura:** novas fontes exigem política explícita de comparação/autoridade, não inferida de igualdade do formato ou de ordem de chegada. Manter provas distintas para enriquecimento, correção e divergência.

### L-152 — Versionar processamento sem preservar replay pode reordenar a história

**Evidência:** código/política novos mudam o fingerprint. O teste de upgrade reproduz fingerprints/receitas antigos em SQL, depois corrige o head e recupera o comando/receipt anterior sem regressão nem alteração de finished_at. Pedido com outro receipt continua conflito.

**Impacto:** uma receita nova para o mesmo raw antigo poderia parecer captura posterior e desfazer uma correção já aceita. Aceitar qualquer chave antiga sem conferir o pedido seria outro erro.

**Ação futura:** compatibilidade é uma lista interna finita de fingerprints completos, derivados do mesmo receipt/catálogo/intenção. Reinterpretação deliberada deve ter comando próprio; não usar replay para promovê-la silenciosamente.

### L-153 — Quarentena pode ser o resultado correto de um commit

**Evidência:** o normalizador aceita o JSON de teste, mas a comparação com histórico encontra divergência financeira. Observação/diagnóstico/issue confirmam, enquanto step/cursor não são chamados. A captura válida seguinte avança com a intenção autorizada.

**Impacto:** normalização bem-sucedida não implica aceitação semântica; tentar sync.advance sobre uma observação sem revisão faria o trigger reverter a própria evidência de quarentena.

**Ação futura:** distinguir erro de infraestrutura, rejeição de interpretação e observação aceita nos orquestradores. Resumos/retomadas não podem transformar quarantined em avanço ou em retry HTTP genérico.

### L-154 — Prova da ponte só está completa quando inclui continuidade

**Evidência:** enriquecimento/passo/cursor revertem juntos em sete pontos T3; token obsoleto e lease perdida no commit conservam head histórico/receipt. Duas capturas JSON serializam com bloqueio observado no servidor, e corrida piloto/incremental com checkpoint termina em identidade única e head JSON.

**Impacto:** testes do mapper ou de uma escrita isolada não detectariam salto de cursor, enriquecimento sem step, perda de evidência ou decisão sobre head lido antes do lock.

**Ação futura:** novas importações/correções devem preservar a ordem global de locks e manter testes de CAS/fencing. Baseline referenciada continua diferente de cobertura carregada, mesmo após um avanço bem-sucedido.

### L-155 — Mesmo conteúdo não torna redundante a evidência de cada captura

**Evidência:** duas respostas com valores monetários iguais, mas textos decimais diferentes, sustentam uma revisão e duas evidências/hash distintos. monetary_fact/source_text selado não é atualizado. Payload incremental registra também a versão/hash/número do head comparado.

**Impacto:** deduplicar raw, normalizar números e deduplicar revisão têm identidades distintas. Um hash único para todas as camadas impediria explicar qual captura apoiou qual decisão.

**Ação futura:** auditorias devem percorrer receipt→processamento→observação→revisão e conferir cada hash em seu contrato. Limites de diagnóstico precisam ser explícitos; não truncar silenciosamente nem alterar raw para caber.

### L-156 — Igualdade de projeção não autoriza declarar suporte em outra versão

**Evidência:** a receita incremental tem saída JSON v1. Um cenário negativo de projeções iguais com versão histórica é colocado em quarentena, não vinculado usando hash falsificado. O enriquecimento real conserva a revisão histórica e acrescenta JSON v1 com seu hash original.

**Impacto:** a representação transitória de comparação não é uma revisão persistida nem uma licença para ignorar o trigger de versão/hash.

**Ação futura:** manter suporte/ponte explicitamente versionados. Se outro produto precisar de apoio parcial entre contratos sem nova revisão, especificar sua receita de saída/evidência; não introduzir fallback implícito no writer.

## Próximo aprendizado esperado após SPEC-0028

Comprovar carga completa e retomável do histórico Mega-Sena, reconciliando cobertura por concurso e sobreposição JSON sem inferir completude do número de revisões. Só promover baseline mediante evidência/fluxo aprovado; demais modalidades e publicação continuam fases próprias.

## SPEC-0029 — Importação completa e auditoria histórica

### L-157 — Cobertura é uma relação verificável, não uma contagem de revisões

**Evidência:** a interrupção real após 100 commits produziu exatamente 100 registros verificados e 2.854 ausentes. O JSON pré-existente acrescenta uma observação, mas não preenche concursos ausentes. A auditoria relaciona cada localizador esperado a alias, comando, receita, evidência e revisão selada reconstruída das tabelas.

**Impacto:** uma revisão mais completa pode apoiar outra fonte sem nova revisão; correções podem criar várias revisões para o mesmo concurso. Nenhum desses totais equivale à cobertura histórica.

**Ação futura:** exigir manifesto e relatório qualificado para qualquer promoção de baseline. Conferir o universo de concursos, hashes de entrada/evidência e vínculo de suporte, não somente count(*) ou max(concurso).

### L-158 — Retomada e auditoria precisam limitar trabalho repetido

**Evidência:** o manifesto compacto tem hash em cache, testado por 6.000 leituras estáveis. O ledger seleciona pendências de uma só vez; cada linha confirma em transação própria. A verificação de storage ocorre por blocos, fora de SQL, e a reconstrução de conteúdo usa seis consultas em lote, com limite explícito de 6.000 revisões.

**Impacto:** reserializar todo o plano ou reler o arquivo por linha torna uma ampliação aparentemente simples cara e potencialmente quadrática. Uma transação gigante impediria conservar os commits comprovadamente feitos antes da interrupção.

**Ação futura:** medir e limitar custo por registro/consulta antes de ampliar fontes. Esse leitor suporta os dois contratos Mega-Sena, não é um mapper universal; arquivos maiores continuam exigindo política própria de storage.

### L-159 — Evidência passada não deve depender da autorização atual da fonte

**Evidência:** a revisão identificou que a auditoria comparava receitas antigas com o fingerprint atual, que inclui readiness e política. O receipt já registra o fingerprint original. A leitura histórica passou a validar esse registro, o manifesto e o request hash do run, separadamente do gate de escrita atual.

**Impacto:** aprovar ou bloquear uma fonte poderia invalidar uma evidência inalterada ou impedir sua investigação. No sentido oposto, conseguir ler uma evidência antiga não autoriza continuar importando com uma configuração incompatível.

**Ação futura:** manter dois controles explícitos: reprodução da decisão histórica e autorização de nova operação. Mudança de configuração/intenção não reutiliza silenciosamente uma chave anterior; não remover a qualificação de register/process para facilitar auditorias.

### L-160 — Estado terminal não é uma avaliação contínua da qualidade

**Evidência:** a revisão reproduziu retorno stopped para um run ainda persistido como completed. A finalização agora obtém o estado realmente atualizado e preserva estados/tempos terminais. Testes isolam completed com auditoria posterior reprovada e stopped/failed com avaliação posterior aprovada, sem UPDATE terminal.

**Impacto:** reescrever apenas o relatório ou promover automaticamente uma execução encerrada confunde o fato histórico do encerramento com a qualidade do snapshot atual.

**Ação futura:** consumidores devem exigir separadamente o encerramento adequado e a auditoria atual qualificada. Reabertura, reparo ou promoção administrativa precisam de fluxo explícito; não usar replay para reescrever finished_at ou esconder uma divergência.

### L-161 — Execução iniciada não é evidência de execução aprovada

**Evidência:** a execução anterior da SPEC-0029 não tinha resultado final recuperável; não foi contada como aprovação. No fechamento, o runner registra a saída completa em arquivo local além do log PostgreSQL; somente relatório positivo, saída final da suíte e desligamento confirmado autorizam a conclusão documental.

**Impacto:** progresso parcial, código implementado e testes que existem no repositório não provam que o cenário integral terminou. Dados de cluster descartável também não significam banco operacional provisionado.

**Ação futura:** preservar resultado, contexto da execução, contagens e relatório novo por etapa, sem sobrescrever auditorias anteriores ou confundir artefatos de teste com dados servidos pela aplicação.

## Próximo aprendizado esperado após SPEC-0029

Definir como uma execução encerrada adequadamente e uma auditoria atual qualificada autorizam um registro explícito de baseline e a passagem entre fonte histórica e incremental. A cobertura validada não cria checkpoint nem ativa sincronização por si só.

## SPEC-0030 — Baseline auditada e início seguro

### L-162 — Passagem entre fontes precisa preservar a origem, não disfarçá-la

**Evidência:** o raw completo é XLSX, mas o checkpoint de continuidade usa JSON. A FK anterior exigia a mesma fonte nos dois registros. A nova migration mantém a baseline no XLSX e registra um vínculo append-only com o checkpoint JSON; FKs de contexto e guardas substituem a igualdade de fonte, não a integridade da relação.

**Impacto:** atribuir source_id JSON a um arquivo XLSX ou remover a FK sem substituição perderia proveniência. A relação de passagem é um conceito real, não uma exceção escondida no coletor.

**Ação futura:** novas passagens entre fontes precisam de política/evidência e contexto explícitos. Usar FKs diferíveis somente onde o ciclo de criação atômica for necessário; não transformá-las em modelo universal de todas as loterias.

### L-163 — Relatório aprovado em um cluster não prova cobertura de outro

**Evidência:** a SPEC-0029 encerrou seus clusters. Nesta etapa, o XLSX foi importado novamente e a auditoria refeita no banco da aprovação. O mesmo manifesto de registros permaneceu estável, mas o snapshot tem todas as revisões históricas e uma referência anterior; não é o mesmo contexto do relatório que apoiava JSON no concurso 2954.

**Impacto:** um JSON de documentação com qualified=true não autoriza inserir baseline em banco vazio, parcial ou diferente. Hash do plano, manifesto de fatos e hash do relatório têm responsabilidades distintas.

**Ação futura:** aprovações futuras devem revalidar evidência/cobertura na instância de destino e preservar o relatório usado na decisão. Não usar arquivos de teste como certificado portável de uma carga operacional.

### L-164 — Inicializar continuidade é uma capacidade diferente de coletar

**Evidência:** o papel ingestor não pode inserir baseline, vínculo ou checkpoint. O bootstrap recebe somente a leitura e os três INSERTs necessários; fonte/catálogo, baseline e publicação não ganham UPDATE. A referência anterior permanece referenced enquanto uma nova baseline loaded é criada.

**Impacto:** conceder inicialização ao coletor permitiria criar fluxos para reiniciar cursor ou contornar cooldown. Uma credencial de bootstrap também não equivale a uma identidade administrativa autenticada na aplicação.

**Ação futura:** separar credenciais/capacidades de operação e coleta. Futura administração de usuários deve autorizar a ação e registrar identidade humana sem distribuir o papel SQL ao navegador ou ao worker comum.

### L-165 — Replay de inicialização não é leitura nem reconstrução do estado vivo

**Evidência:** o retorno conserva initial_cursor=2954 depois de o checkpoint avançar para 2955. Replay não altera cursor, row_version, lease ou instante da aprovação. Comando incompatível ou outro comando para fonte já inicializada é recusado.

**Impacto:** devolver o cursor inicial como se fosse o cursor atual, ou usar INSERT/UPDATE genérico para "garantir inicialização", poderia apagar progresso e evidência.

**Ação futura:** distinguir decisão inicial imutável de consulta de estado atual. A próxima orquestração deve carregar o checkpoint existente, não reaplicar baseline como rotina de cada lote.

### L-166 — Lock idempotente e snapshot consistente precisam tratar visibilidade concorrente

**Evidência:** duas inicializações disputam a mesma intenção; uma resposta de COMMIT é perdida deliberadamente e a mesma chave recupera a única aprovação. O vínculo usa ON CONFLICT e a UoW existente repete somente conflitos transacionais conhecidos. Baseline/vínculo/checkpoint não ficam órfãos quando há falha após qualquer INSERT.

**Impacto:** esperar por um advisory lock não torna um snapshot antigo automaticamente atual. E erro de resposta após COMMIT não autoriza repetir cegamente uma aprovação com outra chave.

**Ação futura:** manter unicidade, rollback, limite de retry e distinção entre aborto conhecido/resultado ambíguo. Testar concorrência real em SQL, não só chamadas sequenciais iguais.

### L-167 — Histórico de coleta ignorado pelo Git não é uma fixture reproduzível

**Evidência:** os JSONs reais 2955 e 3071 estavam somente no workspace de coleta local. Foram copiados byte a byte para fixtures versionáveis, preservando os dois SHAs e validando a normalização, sem editar os originais ou executar novos GETs.

**Impacto:** um teste que depende de data/collections poderia passar nesta máquina e falhar num checkout/CI novo. Alterar um payload apenas para criar o próximo concurso seria outra alegação, não continuidade com dados reais.

**Ação futura:** promover amostras locais necessárias aos testes por cópia íntegra e proveniência explícita. Distinguir bytes reais, transporte dublê e mutação negativa; não copiar segredos ou estado operacional inteiro para fixtures.

## Próximo aprendizado esperado após SPEC-0030

Orquestrar descoberta, avanço e revisão limitada no PostgreSQL usando o checkpoint aprovado, sem misturar o cursor com candidatos adiantados, sem resetar estado e sem ampliar automaticamente orçamento de HTTP, calendário ou autorização de publicação.

## SPEC-0031 — Orquestração SQL limitada

### L-168 — Não avançar cursor não dispensa fencing

**Evidência:** descoberta e revisão também interpretam dados e podem alterar revisões. O testemunho diferível da operação verifica lease/token no COMMIT, mesmo quando não há sync_step. A expiração simulada na descoberta reverte observação, dados e conclusão da operação, preservando o receipt de T2.

**Impacto:** proteger somente o avanço permitiria que um worker obsoleto continuasse corrigindo dados ou rotacionando a revisão depois de perder a lease.

**Ação futura:** toda operação do lote que interpreta dados precisa do mesmo contexto de posse. Não colocar verificação apenas antes do HTTP nem confundir leitura de transporte com processamento sem efeitos.

### L-169 — Depois de uma queda, orçamento de intenções é mais honesto que contador exato de GETs

**Evidência:** uma reserva possui chave estável antes do I/O. Falha de storage após transporte deixa T1 sem receipt; retomada não emite outro GET e encerra capture_unresolved. Uma reserva também pode consumir orçamento sem envio efetivo.

**Impacto:** não é possível deduzir somente do retorno local quantas consultas chegaram ao provedor. Somar novamente apenas chamadas que retornaram com sucesso poderia exceder a intenção autorizada após reinício.

**Ação futura:** expor request_slots_used como limite conservador e guardar evidência das capturas. Não apresentar a métrica como contador exato do servidor nem aumentar orçamento automaticamente para compensar erro.

### L-170 — Captura e interpretação têm identidades de retomada diferentes

**Evidência:** o receipt confirmado em T2 é reutilizado pela mesma chave de captura; a interpretação pending ganha chave ligada ao token novo. Operações done nunca são reinterpretadas, inclusive quando a confirmação de T3 foi perdida. Descoberta e avanço podem apoiar a mesma observação sem outro GET.

**Impacto:** usar a lease na chave de captura repetiria rede; usar sempre a chave antiga de processamento com lease nova produziria conflito ou autorizaria contexto obsoleto.

**Ação futura:** manter separados comando de captura, comando de processamento, identidade de conteúdo e progresso do lote. Retomada deve reconciliar esses registros, não simplesmente reexecutar uma função de coleta.

### L-171 — Resumo não é a autoridade de progresso

**Evidência:** step/cursor ou review_next e conclusão da operação são escritos junto com a interpretação em T3. O resumo terminal é outra transação. Assim, falha na geração/entrega do resumo não exige regredir cursor nem consultar de novo o provedor.

**Impacto:** um resumo parcial, log ou contador em memória não distingue commit perdido de operação não realizada. A trilha por operação reduz essa ambiguidade sem transformar a aplicação em um framework de jobs.

**Ação futura:** auditoria SQL deve cruzar operações, tentativas, receipts, observações e checkpoint. Não reconstruir cobertura a partir de report.status isoladamente.

### L-172 — Reutilizar fixture verificada não significa confiar em certificado de papel

**Evidência:** a execução focal importa/audita/aprova os 2.954 registros reais. Na suíte completa, os testes clonam uma cópia SQL consistente da aprovação comprovada na SPEC-0030, no mesmo processo/cluster, antes dos avanços posteriores. Cada caso usa outro banco e restaura o raw por hash no storage de teste.

**Impacto:** repetir carga integral em cada caso tornaria a regressão cara; substituir por qualified=true fictício eliminaria justamente a garantia testada.

**Ação futura:** compartilhar somente estado real e consistente, com fronteira/proveniência claras e fallback independente. Não usar metadados de outro cluster como autorização nem introduzir sorteios fictícios de sucesso para preencher lacunas.

### L-173 — Liberação de lease é limpeza, não motivo para esconder a falha principal

**Evidência:** cada invocação adquire posse exclusiva, renova só seu token e tenta liberá-lo no finally. Outro chamador não compartilha lease ativa, nem com mesma chave. Um teste puro provoca erro na limpeza e conserva a exceção original.

**Impacto:** liberar token de outro worker, resetar estado ou mascarar erro com falha de cleanup dificulta a recuperação. Aquisição de resultado desconhecido antes de devolver o token não autoriza adivinhar posse.

**Ação futura:** quando o processo morrer/posse for desconhecida, aguardar expiração e diagnosticar. Erros conhecidos são retomáveis pela mesma intenção; bloqueio/mudança de catálogo e captura inconclusiva precisam de decisão explícita, não de retry cego.

## Próximo aprendizado esperado após SPEC-0031

Auditar, em modo somente leitura, o encadeamento lote/operação→captura→interpretação→observação→step/checkpoint, distinguindo progresso confirmado, execução interrompida e captura de resultado desconhecido. Diagnóstico deve preceder qualquer ferramenta de reparo, reabertura ou ativação operacional.

## SPEC-0032 — Auditoria de sincronização sem efeitos

### L-174 — Consistência de leitura e permissão de escrita são contratos diferentes

**Evidência:** o auditor usa conexão própria, REPEATABLE READ READ ONLY, rollback e fechamento antes do storage. A configuração autocommit é recusada; os testes com PostgreSQL verificam que mesmo um login escritor não executa UPDATE nessa transação. O papel audit continua sem escrita.

**Impacto:** usar a UoW do ingestor ou apenas prometer que consultas não escrevem mistura duas responsabilidades. Um SET TRANSACTION sem transação efetiva também não estabelece a proteção pretendida.

**Ação futura:** composições administrativas devem explicitar conexão, permissões e efeitos; diagnóstico não adquire lease nem autoriza bootstrap. Snapshot SQL não é transação distribuída com os arquivos.

### L-175 — Interrupção operacional não equivale a corrupção

**Evidência:** o ledger diferencia captura não iniciada, T1 inconclusiva, receipt confirmado antes de attach, interpretação pendente e operação done. Cooldown, fonte bloqueada e lote interrompido geram atenção; divergência de vínculos, conteúdo, sequência ou resumo gera inconsistência.

**Impacto:** converter todo pending em erro de integridade incentiva reparos indevidos; tratar ausência de confirmação como permissão para repetir HTTP pode duplicar consultas.

**Ação futura:** mostrar a evidência e recomendar investigação/espera/retomada explícita, sem automatizar mudanças. Captura inconclusiva exige diagnóstico próprio, nunca novo GET implícito.

### L-176 — Cada resumo terminal pertence à sua fronteira histórica

**Evidência:** cursor/revisão ao final de um lote são reconstruídos da sequência de operações; comparar o resumo de um lote antigo ao checkpoint atual produziria falsos positivos. Token antigo não precisa continuar ativo para um fato confirmado permanecer verificável.

**Impacto:** estado vivo e fato passado têm referências temporais distintas. Lease ativa no snapshot também não prova que um processo continua vivo.

**Ação futura:** painéis e comandos devem exibir fronteira observada, progresso confirmado e instante do diagnóstico separadamente. Não inferir atualização ao presente por encontrar um candidato adiantado.

### L-177 — Auditoria limitada precisa declarar o que deixou de verificar

**Evidência:** lotes/steps/tentativas têm limites e truncamento impede healthy. A aprovação histórica e seus bytes são conferidos, mas o auditor não repete a prova relacional integral dos 2.954 concursos nem procura objetos órfãos fora do recorte.

**Impacto:** um relatório sem problemas pode omitir justamente a evidência relevante se limites e escopo forem invisíveis. Um certificado antigo não se transforma em reauditoria completa por ter hash válido.

**Ação futura:** manter limites e escopo no contrato, preservar o resultado anterior e produzir evidência nova. Reauditoria histórica, diagnóstico incremental e recuperação administrativa devem ser operações explícitas.

### L-178 — Uma guarda de teste deve observar o componente certo

**Evidência:** a primeira execução SQL aprovou nove cenários e acusou leitura de storage com SQL aberto no teste concorrente. O spy estava instalado no storage compartilhado: interceptou o I/O legítimo do escritor enquanto o snapshot do auditor estava aberto. O teste foi corrigido para injetar um leitor exclusivo no auditor, mantendo o escritor concorrente independente.

**Impacto:** uma asserção global pode confundir isolamento entre componentes com proibição de concorrência e produzir falso positivo. Não se deve alterar a aplicação para satisfazer uma observação que mede o ator errado.

**Ação futura:** dar portas/spies próprios a cada ator, registrar o contexto observado e repetir o cenário corrigido. Conservar o resultado falho no histórico da evidência, sem contá-lo como sucesso.

## Próximo aprendizado esperado após SPEC-0032

Compor uma entrada manual opt-in de sincronização SQL com conexão/checkpoint explícitos, diagnóstico prévio, espera real e limites, preservando o significado de erros e commits desconhecidos. Essa composição deve ser comprovada antes de introduzir agendamento ou coleta operacional.

## Reorganização após SPEC-0032

### L-179 — A conclusão de uma SPEC precisa se conectar a uma capacidade utilizável

**Evidência:** a revisão do roteiro encontrou dez etapas 0023–0032 concentradas em persistência/ingestão, com garantias reais comprovadas, mas ainda sem base operacional atualizada ou fluxo final online. A atualização de dados e a consulta pelo usuário ficaram além de sucessivos encerramentos técnicos.

**Impacto:** número de SPECs/testes concluídos não mede cobertura funcional do produto. Separar camadas em entregas independentes pode aumentar integração tardia e custo de coordenação, mesmo com código bem testado.

**Ação futura:** SPECs 0033–0036 agrupam cada capacidade de ponta a ponta, incluindo persistência, acesso, API/UI, operação e provas pertinentes. O comando manual antes proposto para a 0033 vira atividade do primeiro fluxo online. [Plano central](plano-entrega-quatro-dias.md) concentra escopo/prazo; SPEC registra aceite/estado, contrato registra decisão estável e evidência registra resultado, sem duplicação de narrativas.

### L-180 — Riscos externos e critérios de lançamento precisam aparecer no início

**Evidência:** no replanejamento, os históricos completos continuam em dezembro de 2025, hospedagem/orçamento não estão definidos e os perfis SQL adicionais ainda precisam ser implementados. Um prazo de quatro dias não resolve essas dependências por si só.

**Impacto:** adiar a verificação das fontes e a primeira implantação para depois da plataforma interna pode descobrir bloqueios quando já não há janela de correção.

**Ação futura:** verificar as seis fontes e preparar a decisão de infraestrutura nas primeiras quatro horas da execução. Mostrar fronteiras e atraso, começar CI/segurança/deploy no primeiro incremento e tratar requisito obrigatório bloqueado como pendência real. As novas SPECs permanecem planejadas até haver implementação/evidência; não marcar sucesso por cumprimento da data.

### L-181 — Gratuidade e execução próxima ao sorteio precisam ser validadas juntas

**Evidência:** em 27/10/2026 o usuário definiu custo inicial zero, conteúdo privado com aprovação e atualização próxima à publicação da fonte. A comparação oficial encontrou cron Hobby diário, atrasos possíveis no schedule do Actions, cotas de banco/storage e restrições de SMTP/backups no plano gratuito. A decisão de fornecedor isoladamente não fecha o fluxo operacional.

**Impacto:** prometer frequência, recuperação de conta ou disponibilidade como consequência automática de um plano gratuito esconderia dependências do lançamento. API leve e tarefas Python podem compartilhar o domínio sem compartilhar o mesmo processo/limite de execução.

**Ação futura:** validar a composição gratuita, medir uso incluindo CI/backup, manter atraso visível e bloquear gasto excedente. Separar autenticação do provedor da aprovação pelo proprietário e conferir acesso direto à API/storage. Fontes, restrições verificadas e decisões confirmadas ficam no [plano central](plano-entrega-quatro-dias.md), sem duplicar limites em cada SPEC.

## Verificação técnica das fontes atuais

### L-182 — APIs semelhantes ainda precisam de perfis por modalidade

**Evidência:** a verificação de 27/10 encontrou o contrato Mega-Sena compatível com o parser existente, mas +Milionária acrescenta `trevosSorteados` e oito posições na ordem, incluindo os dois trevos. As amostras por identidade antiga/atual e os ganhadores/rateios históricos conferiram; o retorno HTTP semelhante não produz compatibilidade automática do parser.

**Impacto:** parametrizar apenas quantidade/intervalo de dezenas poderia misturar série principal e trevos ou rejeitar resposta válida. Um novo nome de fonte no catálogo não implementa o adaptador.

**Ação futura:** construir os perfis específicos a partir das amostras preservadas, reutilizando domínio, money/identidade e validações pertinentes. Não repetir a descoberta nem promover esses formatos como parsers de produção já entregues. [Verificação e evidência](../data/verificacao-fontes-atuais-2026-10-27.md).

### L-183 — Posição vazia e valor zero exigem a semântica da fonte

**Evidência:** CSV Texas mantém a posição vazia do multiplicador em períodos nos quais ele não é sorteado; o arquivo FDJ diferencia rateio zero sem ganhador de jackpot anunciado. Os formatos observados foram conferidos em fronteiras históricas e amostras recentes.

**Impacto:** contagem rígida de colunas baseada só na descrição da página ou conversão genérica de zero para ausência produziria falsos erros ou fatos financeiros inventados. Campos franceses, europeus e extensões também não são intercambiáveis.

**Ação futura:** validar layout e aplicabilidade temporal juntos, conservar campos brutos e separar medidas/escopos no mapper. Calcular próximos ganhos analíticos apenas com dados realmente suportados pelo perfil. As condições de calendário e transporte estão centralizadas no relatório, em vez de espalhadas como regras implícitas.

## Fechamento da descoberta e qualificação dos dados

### L-184 — O portal pode mudar o host e manter o caminho da API

**Evidência:** os downloads no `servicebus2` retornaram 404. A cadeia de scripts/configuração do portal aponta para `servicebus3`, onde as três exportações responderam 200. Os JSONs desse host acrescentam `tituloConcursoEspecial`; o normalizador Mega-Sena conserva o candidato para diagnóstico, mas marca `source.schema_changed` e `is_valid=false`.

**Impacto:** um host legado indisponível não prova ausência dos dados. Trocar a URL silenciosamente também não garante compatibilidade de conteúdo. Dimensões incorretas dos XLSX continuam presentes e já são tratadas pelos leitores existentes.

**Ação futura:** SPEC-0033 deve qualificar deliberadamente o perfil novo usando as amostras preservadas. Separar descoberta de endereço, validação de schema e aprovação de conteúdo. Não ignorar qualquer campo desconhecido nem reimplementar os leitores por causa de um problema já resolvido. [Evidência](../data/fechamento-etapa-2.md).

### L-185 — Dois concursos oficiais podem compartilhar a data civil

**Evidência:** exportação e JSONs Lotofácil 3715/3716 indicam 20/06/2026 e combinações distintas. O comunicado oficial registra remanejamentos nos dias de jogos do Brasil. Mega Semana e eleições também explicam datas fora do calendário regular em outubro.

**Impacto:** deduplicar loterias brasileiras apenas por data excluiria resultado válido. Calendário genérico não pode deslocar datas oficiais, excluir concursos ou substituir sequência oficial. Loterias sem número qualificado continuam com identidade provisória contextualizada, sem copiar essa suposição brasileira.

**Ação futura:** manter número oficial como identidade brasileira, calendário com vigência/exceções e horários previstos separados de instantes efetivos. Preservar o caso 3715/3716 na integração das demais modalidades; não criar uma unicidade universal loteria+data.

### L-186 — Mudanças financeiras e de calendário não são mudanças na matriz numérica

**Evidência:** a CAIXA anunciou rateio ordinário novo desde 3073, mantendo 6/60; a Mega Semana também mantém a matriz. Texas publica detalhes de ganhadores estaduais, enquanto FDJ e Irlanda distinguem totais comuns e nacionais. A combinação EuroMillions de 27/10 concorda entre operadores, sem tornar seus valores financeiros intercambiáveis.

**Impacto:** “20 versões de regras” descreve as matrizes numéricas qualificadas, não uma certificação de toda regra financeira histórica. Reservas final 0/5 e especial não são novas faixas de acertos, e concordância de números não autoriza merge de prêmios.

**Ação futura:** versionar essas dimensões separadamente e calcular somente com moeda, território, medida e vigência comprovados. Reutilizar a matriz de disponibilidade no mapper e no painel, exibindo ausência em vez de números fabricados.

### L-187 — Concluir descoberta não concede permissão do fornecedor nem prontidão operacional

**Evidência:** os contratos técnicos e continuidade recente foram qualificados, mas políticas CAIXA/Texas/MUSL/FDJ/Irlanda não oferecem uma licença irrestrita presumível. O cliente Python não alcançou Double Play/NY nas sondagens, embora páginas centrais sejam legíveis pela ferramenta web. Nenhum SLA contratual foi identificado.

**Impacto:** uma avaliação pode terminar com restrição real de uso/transporte. Rotular HTTP 200 como fonte pronta esconderia condições de lançamento; repetir inventários tampouco obteria autorização externa.

**Ação futura:** manter separados os estados de conhecimento do contrato, permissão aplicável, compatibilidade do adaptador e execução operacional. Resolver a condição específica ou escolher alternativa qualificada nas entregas funcionais, sem prometer atualização instantânea ou avançar status/cursor só por haver documentação.

### L-188 — Falha de transporte precisa identificar cliente, método e camada

**Evidência:** na reanálise de 27/10, NY falhou em Python com `SSLCertVerificationError` código 20, mas respondeu 200 no cliente Windows com validação TLS habilitada. CAIXA, que entregara XLSX anteriormente, retornou 403 tanto em HEAD quanto em GET nesta nova consulta.

**Impacto:** erro local de cadeia de confiança não demonstra indisponibilidade da fonte. URL correta e teste offline aprovado não garantem que o executor atual consiga coletar; tampouco uma resposta 403 determina sozinha a causa. Não desativar certificados nem mudar endereços/headers em tentativas indiscriminadas.

**Ação futura:** qualificar no ambiente real de execução, preservar método/cliente/status e tratar indisponibilidade explicitamente. O cliente Windows serviu como prova diagnóstica, não virou dependência de produção. [Revisão e novas evidências](../data/reanalise-etapa-2-atualizacao-completa.md).

### L-189 — Cobertura deve ser medida por série e campo, além do concurso

**Evidência:** 131 principais Powerball de NY conferiram com Texas, mas só 63 têm Double Play preenchido. O CSV austríaco contém 1.118 linhas de faixas para 86 sorteios, usa `JP` e instrução textual de transferência. Colorado distingue ganhadores estaduais e mostrou jackpot diferente de uma observação anterior da página central.

**Impacto:** contagem de linhas e concordância das combinações não certificam integralidade das séries vinculadas ou equivalência financeira. Uma fonte mais rica ainda pode ter ausências seletivas ou outra definição de prêmio.

**Ação futura:** manifestos/painel devem informar completude por série, período, medida e território. Recuperar as 68 ausências Double Play com fonte complementar; preservar observações financeiras antes de reconciliar. Não reiniciar inventário nem adotar scripts exploratórios como coletores definitivos.

### L-190 — Controles de transporte evitam atribuir sucesso à mudança errada

**Evidência:** após a falha Python de certificados, tanto o contexto SSL padrão por conexão direta quanto `truststore` nativo responderam 200 em NY. CAIXA voltou a responder 200 tanto diretamente quanto em controle com configuração padrão de proxy; o cliente existente também validou 3075. A causa exata das falhas anteriores não foi estabelecida.

**Impacto:** instalar uma dependência de certificados ou fixar um proxy por associação temporal seria retrabalho e poderia criar um problema novo. Sucesso local não certifica o executor remoto ainda inexistente.

**Ação futura:** manter verificação TLS, limites e diagnóstico por camada. Reusar o transporte existente quando adequado e executar um smoke test seguro no ambiente escolhido durante a implantação. Não alterar trust store, dependências ou headers sem evidência de necessidade. [Controles preservados](../data/qualificacao-final-etapa-2.md).

### L-191 — Cobertura comprovada e condição de uso precisam de decisões próprias

**Evidência:** o export Colorado contém os 68 Double Play ausentes em NY, concorda com os 63 sobrepostos e com 131 principais/Power Play. Seus termos, porém, restringem automação. Já os termos gerais OPEN-NY apoiam reutilização, mesmo com campo de licença nulo nos metadados dos datasets.

**Impacto:** HTTP 200 não libera um canal e metadado de licença vazio não prova proibição. Repetir a qualificação numérica não resolve uma dependência de uso do fornecedor. Trocar coleta automática por manual tampouco resolve uma cláusula que menciona ambas.

**Ação futura:** priorizar NY para os principais recentes dos EUA; manter complemento Colorado não habilitado até canal permitido/alternativa qualificada. Registrar EXT-01/02/03 com escopo e evidência necessários, sem criar outra série de SPECs de inventário. A aplicação deve informar indisponibilidade das funções afetadas, e o aceite não pode alegar liberação global.

### L-192 — Comparar valores exige qualificar primeiro o significado da célula

**Evidência:** os ganhadores Europa concordam em 1.118 faixas de 86 sorteios FDJ/Áustria. Há 77 linhas com `JP`, quota austríaca positiva e rateio FDJ zero, enquanto as demais quotas numéricas conferem. Dez células contêm transferência para 5+0, em vez de valor monetário.

**Impacto:** um algoritmo que comparar todo número como “prêmio” produz divergências falsas; converter instrução textual em zero fabrica um pagamento. Concordância amostral também não comprova resgate efetivo ou regra financeira universal.

**Ação futura:** preservar valor bruto, medida, estado de ausência, fonte/instante, território, moeda e série/faixa. Usar decimal e conversão regional explícita. Gráficos e modelos devem escolher uma medida qualificada; dados não oferecidos ficam indisponíveis, sem inventar valores ou bloquear toda a engenharia para pesquisar campos sem uso definido.

### L-193 — Ausência de licença específica não demonstra necessidade de autorização individual

**Evidência:** o usuário escolheu os downloads públicos oficiais CAIXA; o bloqueio EXT-01 havia sido criado a partir da ausência de licença específica localizada, sem proibição concreta demonstrada para o uso factual privado. No EuroMillions, SELAE oferece um canal específico de apresentação de resultados em outros sites; seus termos gerais preservam outros direitos e preveem uso particular. A FDJ oferece arquivos para criar estatísticas próprias.

**Impacto:** ignorar a destinação específica de um canal gera bloqueios genéricos e rodadas de descoberta sem ganho. Acesso público tampouco equivale a licença irrestrita de todos os conteúdos do operador.

**Ação futura:** usar os canais oficiais selecionados para o escopo atual e distinguir dados factuais de marcas, peças publicitárias e reprodução integral de bases/sites. EXT-01 deixa de ser gate genérico e EXT-03 recebe a decisão SELAE do [encerramento vigente](../data/encerramento-etapa-2.md), substituindo a orientação pendente anterior. A proibição concreta Colorado continua registrada; não a remover por analogia. Não pedir ao usuário novamente autorização de desenvolvimento já dada.

### L-194 — Uma fonte rica precisa de perfis históricos e estados de conteúdo

**Evidência:** SELAE devolveu cinco resultados reais desde 2004 e 26 faixas recentes de ganhadores Europa iguais à FDJ. O primeiro sorteio tem 12 faixas e `ganadores_eu=null`; as amostras posteriores têm 13. A ordem 4+0/3+2 mudou entre amostras, e a data sem sorteio retornou HTTP 200 com uma string JSON. `premio_bote=0` em 2004 coexiste com primeiro prêmio publicado positivo. Rateios nacionais recentes também diferem, apesar de combinação/ganhadores Europa iguais.

**Impacto:** status 200, tamanho fixo de lista e posição da faixa não bastam para aprovar conteúdo. Reutilizar mapeamento recente como se fosse universal corromperia identidade, valores ou categorias históricas.

**Ação futura:** identificar modalidade/data/referência, mapear categoria por acertos, respeitar vigência e preservar ausência/território. Não inferir UTC do relógio sem offset, nem transformar marcadores/zeros legados em fatos financeiros atuais. Reutilizar as 18 novas provas offline na implementação; não levar scripts temporários de inspeção para produção.

### L-195 — Arquitetura modular não exige processos permanentes nem renomear o núcleo

**Evidência:** a fundação já está em `app/domain`, `application`, `ingestion`, `infrastructure` e `interfaces`. A implantação inicial escolhida usa uma função FastAPI e CLI efêmera, mantendo as mesmas fronteiras. A proposta anterior de containers obrigatórios e diretório `backend/` não era necessária a essa implantação.

**Impacto:** mover tudo ou dividir em funções por caso de uso criaria retrabalho sem entregar consulta, coleta ou segurança.

**Ação futura:** preservar imports e núcleo, construir adapters HTTP/Auth/Storage e frontend separado. Patch de biblioteca e lockfile entram no primeiro build compatível; nova abstração depende de capacidade real. [Decisão vigente](../architecture/decisions/ADR-0004-produto-privado-seis-loterias.md).

### L-196 — A preferência de atualidade deve orientar custo e estado, não virar promessa inflexível

**Evidência:** o usuário revisou a preferência para uma hora ou um dia após o sorteio. Dispatcher horário pode atrasar; fornecedores publicam campos em momentos diferentes. Consultar de cinco em cinco minutos e exigir uma confirmação humana por resultado não atende bem ao orçamento e à automação pretendidos.

**Impacto:** uma marca de sucesso do job não prova cobertura atual; esperar aprovação manual por todo sorteio impediria atualização normal em D+1.

**Ação futura:** +1h devido, reconciliação no dia seguinte e modo diário declarado; persistir jobs, recuperar disparos perdidos e distinguir modalidade/série. Aprovar baseline/política e promover acréscimos elegíveis por essa política; conflitos ficam em revisão. Medir cota/atraso na implantação em vez de prometer cinco/quinze minutos.

### L-197 — Um modelo multilateral precisa de aceite funcional para cada perfil

**Evidência:** o catálogo/modelo lógico contemplam seis modalidades, mas o writer/leitor mais desenvolvido continua Mega-Sena. O usuário exigiu funcionalidade para todas; a primeira consulta planejada foi ampliada às seis.

**Impacto:** seis slugs ou abas não comprovam persistência, regra, dinheiro, série e consulta corretos. Expandir escopo sem atualizar dependências de SPECs duplicaria trabalho ou esconderia os cinco perfis restantes.

**Ação futura:** 0033 entrega perfis/consulta histórica das seis; 0034 contratos atuais e agendamento; 0035 análises/previsões; 0036 operação. Reusar casos de uso com adaptadores qualificados, provar cada perfil e registrar o risco ampliado do prazo. Nomes históricos de arquivo não determinam o escopo vigente.

### L-198 — Auditar contratos exige procurar lacunas de comportamento além de links válidos

**Evidência:** a revisão final da etapa 3 encontrou quatro detalhes implícitos: vínculo da tentativa OAuth ao navegador, unicidade de jobs com escopos opcionais, corte único de banco/manifesto de backup e estado de qualidade quando uma correção ainda está em revisão. Links e imports válidos não verificavam esses comportamentos.

**Impacto:** sem contratos explícitos, implementações diferentes poderiam aceitar callback desvinculado, duplicar uma intenção global, montar backup de cortes diferentes ou apresentar dado recente sob revisão como válido.

**Ação futura:** os contratos foram complementados nos documentos proprietários, sem criar outro pipeline ou antecipar código. Testar os quatro cenários nas entregas de identidade/jobs/datasets/recuperação; distinguir aceite de desenho de prova operacional. A ausência de implementação futura não reabre a arquitetura, mas também não autoriza anunciar funcionamento já comprovado.

### L-199 — Um protótipo precisa separar simulação de dados reais

**Evidência:** a etapa 4 usa 30 sorteios preservados de cada modalidade (180 no total), reutilizando normalizadores brasileiros e amostras internacionais. Estatísticas são calculadas nesse recorte; acesso, MFA e ações administrativas mudam apenas memória local. As métricas preditivas permanecem indisponíveis.

**Impacto:** um cartão visual com acurácia inventada, uma data de job ou uma aba vazia poderiam sugerir uma capacidade que ainda não existe. Dados disponíveis no JavaScript também não se tornam privados porque a tela apresenta login.

**Ação futura:** reutilizar desenho e cenários, conectar dados autorizados reais na 0033/0035 e retirar controles demonstrativos. Manter distinção amostra/histórico/dataset aprovado, qualidade/atualidade e backtest/previsão emitida. [Proveniência e contratos visuais](../design/etapa-4-experiencia-visual.md).

### L-200 — Mesmo layout não significa mesma semântica de dados

**Evidência:** o layout acomodou Lotofácil com 15 principais, trevos, bolas e estrelas. OPEN-NY não trouxe faixas financeiras nesse recorte; FDJ trouxe ganhadores europeus e rateios publicados na França. O protótipo mantém os escopos e calcula principais/especiais separadamente.

**Impacto:** um painel por loteria duplicaria estrutura; um painel genérico sem disponibilidade e escopo inventaria equivalência entre valores.

**Ação futura:** componentes guiados pelo catálogo e DTOs com disponibilidade, origem, unidade, série e vigência. Não converter ausência em zero, multiplicador em bola especial ou taxa francesa em prêmio global. A fonte de uma amostra preservada não deve ser substituída na legenda por uma fonte escolhida para aquisição futura.

### L-201 — Verificar interação e tamanho real encontra falhas que screenshots isoladas não revelam

**Evidência:** a revisão da etapa 4 encontrou restauração de filtro que reaplicava a query antiga, foco perdido durante troca de aba e transbordamento do cabeçalho administrativo em 320 px. A circulação Tab/Shift+Tab também precisou de controle explícito no diálogo. Foram corrigidos; a prova registra navegação das 24 seções em desktop/celular, teclado e larguras adicionais.

**Impacto:** aparência inicial e sintaxe válida não comprovam uma jornada utilizável. Adiar foco com `requestAnimationFrame` não era necessário após substituir conteúdo já presente no DOM.

**Ação futura:** levar os cenários de filtro/vazio/restauração, permissão, foco/diálogo e menor largura para os testes do frontend real. Testar fluxos representativos e invariantes em vez de repetir inventários ou testar cada detalhe de CSS. [Validação](../design/validacao-etapa-4.md).

### L-202 — O runtime no PATH e a instalação anterior não comprovam reprodução

**Evidência:** o computador tinha Node 14 no PATH, embora a plataforma nova use Node 24. O Python anterior continha dependências misturadas do legado. A etapa 5 criou ambiente novo, fixou runtimes/lockfiles e comprovou importação da API com apenas 14 pacotes, sem pandas, Selenium, scikit-learn, pytest ou ORM.

**Impacto:** um teste que passa na máquina do autor pode depender de pacote ou arquivo gerado ausente no CI. `next-env.d.ts` passou a referenciar tipos gerados depois do build.

**Ação futura:** usar instalação pelo lock e `next typegen` antes do TypeScript; registrar runtime efetivo. Não alterar instalações globais para contornar a configuração do projeto. O perfil API não deve herdar todas as dependências de jobs/legado.

### L-203 — Grafo compatível e auditoria valem mais que apenas instalar a versão mais nova

**Evidência:** npm conseguiu instalar/lintar uma combinação que ainda tinha peers incompatíveis. A fundação foi ajustada para regras ESLint/TypeScript/Next/Hooks compatíveis, com menos dependências, sem forçar peers. pip-audit identificou alertas no Requests 2.32.3; a atualização para 2.33.0 eliminou os alertas do recorte API/jobs.

**Impacto:** build verde isolado não comprova que uma instalação limpa ou a auditoria passará. Silenciar o auditor ou forçar a árvore esconderia o problema.

**Ação futura:** comprovar `npm ci`, árvore válida, testes/build e auditoria; atualizar o lock como uma unidade revisável. Tratar separadamente perfil ativo e histórico legado, sem adicionar dependências pesadas ao pacote web.

### L-204 — Configurar CI e comprovar CI remoto são resultados diferentes

**Evidência:** o remoto era o repositório correto, mas a conexão do aplicativo estava em outra conta e tinha somente leitura; o Git local não tinha credencial. A base e verificações locais puderam avançar enquanto o usuário preparava a conta proprietária.

**Impacto:** criar um workflow local não autoriza anunciar uma execução no GitHub, proteção de branch ou deploy. Uma confirmação de que o usuário pode conectar a conta também não demonstra que a conexão já mudou.

**Ação futura:** verificar identidade/permissões, publicar numa branch de trabalho somente quando autorizado e disponível, registrar SHA/run/resultado e tratar a proteção da branch explicitamente. Após o merge, sincronizar o estado de fechamento no relatório, nas evidências e no roadmap; preservar a medição anterior à integração e acrescentar o CI da `main` com seu próprio commit, horário e resultado. Não pedir senhas/tokens no chat, ampliar permissões por suposição ou recriar o repositório.

### L-205 — Portabilidade inclui o bootstrap do banco e os bytes da evidência

**Evidência:** o primeiro CI passou em Python/frontend, mas falhou ao iniciar o cluster PostgreSQL Linux. O executor passou a usar somente TCP em loopback e emitir diagnóstico de bootstrap com senha removida; a inicialização corrigida passou também em cinco testes Windows. Na publicação inicial, o Git normalizou CRLF de dois arquivos do protótipo; as regras de atributos foram ampliadas e os bytes originais restaurados. O commit `7c9b841` foi comparado com os 149 hashes protegidos, sem divergência.

**Impacto:** testes locais não comprovam a inicialização do serviço no runner Linux. Conteúdo visualmente idêntico também pode ter hash diferente após o checkout. Repetir a bateria inteira no Windows sem mudança de comportamento não resolveria a diferença do ambiente remoto.

**Ação futura:** executar a suíte real em ambas as plataformas quando bootstrap for alterado; manter diagnóstico limitado ao cluster recém-criado e remover credenciais. Para ajustes apenas de inicialização, usar smoke local dirigido e bateria completa no CI. Verificar blobs publicados além dos arquivos locais quando existir evidência hashada; preservar byte a byte raws e artefatos anteriores.

## Próximo aprendizado esperado no plano de quatro dias

Comprovar o primeiro fluxo online reutilizando o núcleo existente, medir o custo de integrar os perfis restantes e registrar quais decisões/fixtures reduziram retrabalho sem enfraquecer as invariantes. Estado atual e sequência vigente: [roadmap](../architecture/roadmap.md).
