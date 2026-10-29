# Qualificação final da etapa 2 — 27/10/2026

## Resultado e limite do aceite

**Concluída esta tarefa de qualificação técnica e documental das pendências conhecidas.** Os seis contratos aproveitam o inventário, as regras e as amostras anteriores. Foram resolvidas a dúvida de acesso Python a NY, a reprodução do acesso CAIXA, a existência de título especial não nulo e a localização dos 68 resultados Double Play ausentes. As medidas financeiras receberam decisões explícitas e conferência adicional.

**Não estão todas as fontes liberadas para operação no produto.** Há dependências externas de uso identificadas, especialmente a restrição explícita do Colorado. Se “etapa 2 completa” exigir também autorização de todas as fontes para coleta/exibição recorrentes, esse critério permanece pendente. Esta tarefa não fabrica essa autorização nem redefine silenciosamente o aceite como prontidão operacional.

O [manifesto verificável](qualificacao-final-etapa-2.json) reúne receipts, hashes, decisões, 131 referências de linhas Double Play e a matriz de dependências. Foram 14 GETs públicos limitados, sem paginação, retries ou ingestão. Cada sondagem exploratória teve timeout de 20 segundos e teto de 4 MiB; uma chamada usou o cliente existente com seus próprios limites. Pesquisa web de políticas é evidência separada dos GETs registrados. Os scripts de inspeção permaneceram temporários e ignorados; não são parsers ou coletores de produção.

## Reuso e situação das seis loterias

Não houve novo inventário dos 15.471 registros originais, nova auditoria de todas as regras históricas ou substituição dos relatórios anteriores. As fronteiras abaixo são **fotografias das fontes**, reutilizadas do [fechamento anterior](fechamento-etapa-2.md) e da [reanálise complementar](reanalise-etapa-2-atualizacao-completa.md); não são uma afirmação de que o banco está atualizado.

| Loteria | Fronteira da fotografia de 27/10 | Resultado desta qualificação | Passagem para implementação |
|---|---|---|---|
| Mega-Sena | 3.075 concursos; último 3075 em 26/10; 121 posteriores ao raw original | Download oficial novamente 200, bytes idênticos. Cliente existente consultou/validou 3075. Título textual real em 3010 qualificado | Adaptar deliberadamente o perfil JSON atual; resolver uso aplicável antes da ativação abrangida |
| Lotofácil | 3.814 concursos; último 3814 em 26/10; 243 posteriores | Download novamente 200, mesmo hash. Identidades 3715/3716 na mesma data permanecem distintas | Reutilizar contrato, trechos qualificados e exceções; implementar integração, sem deduplicar só pela data |
| +Milionária | 401 concursos; último 401 em 24/10; 87 posteriores | Download novamente 200, mesmo hash, usando `%2BMilion%C3%A1ria` | Manter seis bolas e dois trevos separados e as dez faixas; integrar perfil já conhecido |
| Powerball | 131 principais posteriores ao raw, até 26/10 | Python NY 200 com TLS seguro. Colorado cobre os 68 Double Play ausentes; 63 sobrepostos concordam | Preferir NY para principais recentes; complemento Colorado tecnicamente demonstrado, porém não habilitável automaticamente sob os termos encontrados |
| Mega Millions | 87 posteriores ao raw, até 23/10 | Python NY 200 com TLS seguro. Conferência NY/Texas anterior reutilizada | Integrar números recentes; preservar Megaplier histórico e multiplicador atual do bilhete como conceitos distintos |
| EuroMillions | 87 posteriores ao raw, até 27/10; comparação austríaca cobre 86 sorteios de 2026 | Mesmas combinações já comprovadas; agora 1.118 faixas de ganhadores europeus comparadas, sem conflito | Reusar FDJ/Áustria com escopo e estado financeiro explícitos; decidir canal de uso recorrente permitido |

Os históricos Texas começam na participação estadual, e o arquivo austríaco é anual. Não substituir os históricos anteriores por essas fontes menores. A comparação financeira austríaca não inclui o sorteio de 30/12/2025 que faz parte dos 87 registros recentes FDJ.

## Aceitação das pendências

| ID | Pendência | Evidência e decisão | Estado |
|---|---|---|---|
| QF-01 | CAIXA havia respondido 403 | Três XLSX responderam 200 às 19h41–19h42 de São Paulo, com os mesmos hashes das amostras anteriores; cliente real Mega-Sena 200 às 19h48 | Comprovado localmente, sem promessa de disponibilidade permanente |
| QF-02 | `tituloConcursoEspecial` só tinha amostra nula | 3075: `null`; 3010: texto `Mega-Sena 30 anos`, sorteado em 24/05/2026 | Perfil documentado e testado; adaptação de produção continua na SPEC-0033 |
| QF-03 | Python NY falhava em certificados | Dois datasets responderam 200 tanto com contexto SSL padrão quanto com confiança nativa, mantendo verificação de certificado/hostname | Transporte local qualificado; confirmar no executor de implantação quando existir |
| QF-04 | 68 lacunas Double Play | 68/68 localizadas no export Colorado; 63/63 Double Play sobrepostos concordam; principais e Power Play concordam nas 131 datas | Cobertura técnica resolvida; uso automático da fonte restrito |
| QF-05 | Ambiguidade financeira | 1.118 comparações de ganhadores; 77 marcadores de jackpot e dez transferências reconhecidos; contrato por medida/território/moeda | Concluído para os perfis/amostras declarados; ausências explicitadas |
| QF-06 | Critério único para as seis fontes | Contratos, fontes de referência, fronteiras e bloqueios consolidados neste documento e manifesto | Aceite documental concluído; liberação operacional global não obtida |

### Transporte: o que foi demonstrado

O erro anterior de certificados não demonstra que os dados NY estejam indisponíveis. Nesta sessão, Python 3.12.0 no Windows conseguiu os dois datasets por conexão direta com `ssl.create_default_context()`, `CERT_REQUIRED` e validação de hostname. A alternativa `truststore 0.10.5`, instalada somente na pasta temporária ignorada, também passou. **Não há evidência de que uma nova dependência seja necessária**; nenhum certificado foi ignorado, importado ou alterado.

Os downloads CAIXA funcionaram tanto no teste direto quanto em um controle posterior com configuração padrão de proxy. Portanto, **a causa exata dos 403 anteriores não foi estabelecida**; não atribuir o sucesso somente à escolha de proxy. Nenhum endereço de proxy ou segredo foi registrado. Não foram usados headers para se passar por navegador, redirecionamentos automáticos ou contorno de bloqueios.

O cliente `CaixaMegaSenaHttp`, sem alterações, buscou `servicebus2/.../megasena/3075` e seu normalizador aceitou o conteúdo antigo. Isso não prova que todos os endpoints do host legado continuem disponíveis. O host de download configurado permanece `servicebus3`. O JSON desse host tem um campo adicional, e a política conservadora do adaptador atual continua recusando mudança de schema. Não alterar host/configuração automaticamente com base em uma única resposta.

### Perfil adicional CAIXA, sem implementar o adaptador

O perfil de qualificação `caixa.mega_sena.json.title.v1` corresponde exatamente aos campos conhecidos mais `tituloConcursoEspecial`, com tipo `null|string`. Conservar o título original como metadado descritivo; ele não substitui concurso, matriz numérica ou regra financeira. O exemplo 3010 possui `indicadorConcursoEspecial=2`, mas não qualifica uma tabela universal de significados para esse indicador.

Os testes confirmam que a parte conhecida dos dois JSONs continua válida e que o normalizador existente rejeita o campo novo. A projeção usada no teste é exclusivamente uma prova de inspeção, não um parser instalado que descarte metadados. A implementação posterior deve preservar o título, aceitar os dois perfis deliberadamente e continuar recusando campos desconhecidos até qualificação. Lotofácil/+Milionária reutilizam suas amostras e contratos já preservados, sem presumir que todos os códigos de publicação sejam iguais entre modalidades.

### Double Play: prova de cobertura e restrição

Um único XLSX oferecido pelo Colorado possui 2.904 linhas de resultados e 61 colunas. Foram examinadas as **131 datas da janela 27/12/2025–26/10/2026**, não certificadas todas as linhas do arquivo. Todas têm cinco bolas Double Play distintas entre 1–69 e Powerball entre 1–26. Os 68 valores ausentes em NY, de 27/12/2025 a 01/06/2026, estão presentes; as 63 datas sobrepostas concordam. O manifesto registra a linha física de origem de cada combinação.

Os [termos do Colorado](https://www.coloradolottery.com/en/terms-of-service/), seção 3.11, incluem proibição expressa de acesso por robôs/scrapers e outros meios automatizados ou manuais. A exportação foi examinada antes de localizar essa condição; não se fizeram novas consultas Colorado após identificá-la. Não ativar a coleta desse canal sem esclarecimento/autorização do fornecedor ou alternativa permitida. Não usar atualização manual como suposta solução para a mesma restrição. Não houve importação dos 68 resultados no banco.

## Contrato dos dados financeiros

Toda medida deve conservar fonte, referência do concurso, data local, instante da coleta, moeda, território, série/categoria, natureza do valor, estado de disponibilidade e valor bruto. O valor monetário canônico usa decimal exato. `null` com motivo, zero observado, não aplicável e texto de transferência são estados diferentes.

| Família | Medida qualificada | Distinção obrigatória |
|---|---|---|
| CAIXA, BRL/BR | `valorArrecadado`, ganhadores e `listaRateioPremio[].valorPremio` | Arrecadação publicada, quantidade de ganhadores e prêmio por ganhador não são a mesma medida |
| CAIXA, próximo concurso | `valorEstimadoProximoConcurso` | Estimativa do próximo concurso não é pagamento realizado no atual; reservas especiais/0–5 mantêm medidas próprias |
| EUA, USD | Colorado `Jackpot` e `Jackpot Cash Value` | Estimativa anunciada na modalidade anuidade e opção cash separadas; nenhuma razão fixa entre elas nem inferência de pagamento efetivo |
| EUA, território | `CO Winners`, série base, Power Play/Double Play e fatores do bilhete MM | Ganhadores do Colorado não são totais nacionais; não somar séries/fatores como categorias equivalentes |
| EuroMillions, EUR nas amostras FDJ/Áustria | Ganhadores Europa e França/Áustria; rateio por faixa | Territórios e extensões locais separados; moeda desses dois operadores não determina a de todos os países |
| EuroMillions, jackpot | Áustria `JP` com quota positiva; FDJ zero em ganhadores/rateio | Marcador de jackpot/acumulação e valor de prêmio por ganhador são fatos distintos |
| EuroMillions, transferência | Texto austríaco de transferência para 5+0 | Valor numérico ausente com motivo `transferred`, destino preservado; não transformar o texto em prêmio zero |

No Powerball de 26/10, a observação Colorado de USD 687 milhões e a observação central anterior de USD 691 milhões permanecem ligadas a fontes/instantes diferentes. Não decidir qual é o pagamento definitivo por comparação de números. A distinção entre estimativa anunciada e valor efetivo de anuidade é prevista nas [regras oficiais Powerball do Colorado](https://static.coloradolottery.com/media/filer_public/75/09/75094167-56c1-4a8d-8dc4-be79c03f5099/rule_14a_powerball.pdf).

**Conferência EuroMillions:** 86 sorteios × 13 faixas = 1.118 comparações de ganhadores Europa FDJ/Áustria, sem divergência. Há 1.108 quotas numéricas e dez instruções textuais de transferência. Nas 77 linhas de primeiro prêmio marcadas `JP`, FDJ tem zero ganhadores/rateio e a quota austríaca é positiva. Nas demais quotas numéricas, os valores publicados conferem. Essa igualdade amostral não autoriza generalização a todos os países/períodos nem comprova pagamentos efetivamente resgatados.

O [operador austríaco](https://www.lotterien.at/spiele/lotteriespiele/euromillionen) descreve a acumulação da primeira faixa sem ganhadores e a passagem do montante de uma faixa inferior sem vencedores para a seguinte. Isso sustenta a distinção dos estados observados. Exemplo de 27/10: quota da primeira faixa `78.415.028,30` com `JP`; segunda faixa sem vencedores transfere para 5+0; terceira quota `630.456,60`. A leitura preserva espaços, codificação compatível cp1252 e separadores locais; o CSV não é UTF-8 válido.

**Fatos não oferecidos no contrato escolhido:** arrecadação nacional auditada PB/MM, arrecadação pan-europeia consolidada, timestamps efetivos de todos os sorteios históricos, pagamento efetivamente resgatado e regulamento financeiro integral de todas as épocas. Permanecem explicitamente indisponíveis, não convertidos em estimativas ou condições para repetir o inventário. Qualificar um novo fato somente se uma funcionalidade concreta depender dele. As 20 versões já qualificadas são matrizes numéricas, não todo esse regulamento financeiro.

## Condições de uso e dependências externas

| Fonte | Decisão para a implementação |
|---|---|
| OPEN-NY | Os [termos gerais oficiais](https://data.ny.gov/api/views/77gx-ii52/files/ef0c1840-ad54-4240-92fd-6397c49fde46?filename=OPEN-NY_20Terms_20of_20Use.pdf) apoiam reutilização, inclusive em projetos privados, sem pré-aprovação, observadas suas condições. O campo de licença vazio nos metadados não basta para concluir proibição. Priorizar para os principais recentes dos EUA; não garante Double Play completo, latência ou SLA |
| Colorado | Restrição expressa de automação encontrada. Fonte de evidência técnica; não habilitar coletor sem canal permitido. Dependência EXT-02 |
| CAIXA | Contratos técnicos conhecidos. Escopo de uso recorrente/exibição do produto ainda precisa ser esclarecido, conforme os [termos já identificados](https://www.caixa.gov.br/termos-de-uso/Paginas/default.aspx). A nova tentativa web de ler os termos encontrou redirecionamento, não uma licença nova. Dependência EXT-01 |
| FDJ | O [aviso oficial](https://www.fdj.fr/informations/reglements) exige autorização escrita para uso de elementos protegidos. A tarefa não concede essa autorização nem determina por conta própria sua aplicação a cada fato numérico. Dependência EXT-03 |
| Áustria | Fonte anual tecnicamente comparada e semântica de faixas esclarecida; isso não equivale a autorização de feed para o produto. Alternativa de EXT-03 somente após resolver as condições aplicáveis |
| Texas/MUSL/Irlanda | As condições específicas registradas no [fechamento anterior](fechamento-etapa-2.md) continuam; nenhuma fonte alternativa foi habilitada silenciosamente |

Não foram enviados contatos, contratados serviços, solicitadas chaves nem assumidos compromissos em nome do usuário. Permissão do proprietário do projeto para desenvolver não substitui permissão aplicável do fornecedor. O acesso privado aprovado pelo administrador também não muda, por si só, essas condições. Este registro é diagnóstico de fontes e decisão de integração, não parecer jurídico.

Para encerrar também o critério externo, EXT-01/03 precisam de condições aplicáveis confirmadas ou alternativa qualificada; EXT-02 precisa de canal permitido com cobertura Double Play e financeiros pretendidos. Cada resolução deve apontar evidência de uso, contrato e cobertura, sem reiniciar seis inventários. Até lá, a funcionalidade afetada permanece bloqueada de forma explícita.

## Verificação e passagem

Os 15 novos testes offline em [test_final_source_qualification.py](../../tests/test_final_source_qualification.py) verificam integridade das nove amostras referenciadas, perfis reais CAIXA, controles TLS, 68 lacunas/63 sobreposições Double Play, semântica das 1.118 faixas e preservação dos seis raws. Cinco amostras são reaproveitadas; somente quatro corpos novos foram preservados, somando 611.895 bytes. O manifesto registra recibo sem corpo para a página HTML Colorado, cujo conteúdo completo não foi duplicado.

Validação consolidada: **80 testes aprovados**, sem rede nos testes, reunindo catálogo, amostras atuais, qualificações anteriores e esta entrega. Conferência de preservação por SHA-256 sobre os 315 arquivos existentes no início: todos preservados, exceto cinco documentos de navegação/aprendizados atualizados intencionalmente. Os seis raws, relatórios anteriores, código de produção, dependências, migrations e testes anteriores permanecem idênticos. Detalhes da execução e lista de alterações estão no manifesto.

**Próxima tarefa única:** executar a **[SPEC-0033 — Primeiro fluxo online Mega-Sena](../specs/SPEC-0033-primeiro-fluxo-online-mega-sena.md)**, reaproveitando o perfil atual agora qualificado, com decisão concreta de hospedagem e resolução de EXT-01 antes da ativação abrangida. Não criar outra SPEC de inventário. A SPEC-0034 integra as seis modalidades e agenda atualizações depois, preservando EXT-02/03 como condições explícitas; não prometer que todos os dados já foram importados ou que todos os coletores estão prontos.
