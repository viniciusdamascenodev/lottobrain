# Encerramento da etapa 2

## Decisão vigente

**Etapa 2 concluída: conhecer e qualificar os dados das seis loterias.** Os históricos existentes, formatos, campos, problemas, regras numéricas, fronteiras recentes e caminhos de atualização estão documentados. A seleção de fontes para os resultados principais está definida; o próximo trabalho é integração funcional, sem repetir inventários.

Este documento e o [manifesto de encerramento](encerramento-etapa-2.json) são a decisão vigente. Os relatórios anteriores permanecem como fotografias datadas. O encerramento não afirma que os dados já foram carregados no PostgreSQL, que os agendadores estejam ativos ou que os fornecedores concederam licença irrestrita de seus sites.

## Fontes escolhidas

| Loteria | Fonte de resultados para a integração | Base de recuperação e conferência já qualificada |
|---|---|---|
| Mega-Sena | API pública oficial CAIXA; download histórico `servicebus3` | 3.075 concursos na fotografia de 27/10; perfil JSON adicional qualificado; cliente existente consultou 3075 |
| Lotofácil | API pública oficial CAIXA; download histórico `servicebus3` | 3.814 concursos; 3715/3716 mantêm IDs distintos apesar da data igual |
| +Milionária | API pública oficial CAIXA; download histórico `servicebus3` | 401 concursos; seis números e dois trevos; parâmetro do download com `%2B` |
| Powerball | OPEN-NY para principais recentes; histórico existente preservado | 131 resultados recentes conferidos com Texas; multiplicador e Double Play têm cobertura própria |
| Mega Millions | OPEN-NY para recentes; histórico existente preservado | 87 resultados recentes conferidos com Texas; multiplicadores históricos e do bilhete separados |
| EuroMillions | Serviço oficial SELAE por data, ligado ao canal de compartilhamento de resultados | Amostras desde o primeiro sorteio de 2004; arquivos oficiais FDJ para recuperação histórica em lote e reconciliação; Áustria como referência financeira complementar |

As quantidades são as fotografias qualificadas em 27/10/2026, não contadores de produção. As provas anteriores continuam válidas: 15.471 registros originais, 20 versões de matrizes numéricas, continuidade de 756 resultados posteriores às fronteiras originais, transporte Python seguro e exemplos reais dos perfis atuais. Não houve nova varredura dos seis históricos.

### CAIXA

**Manter os links oficiais públicos fornecidos pelo usuário como fontes selecionadas.** A exigência genérica de obter uma licença específica antes de avançar foi excessiva: a ausência de uma licença específica localizada não demonstrou uma proibição de consumir os resultados oferecidos publicamente. A antiga EXT-01 deixa de ser um bloqueio da etapa 2 e da integração factual privada definida para o projeto.

O [portal oficial](https://loterias.caixa.gov.br/Paginas/Mega-Sena.aspx) oferece consulta e download de resultados. O caminho dos três downloads já foi comprovado pela configuração do portal e pelas capturas preservadas, incluindo retorno 200 e hashes idênticos aos arquivos qualificados. Não repetir esses downloads para encerrar esta decisão.

Essa escolha cobre os dados de concursos usados no LottoBrain. Não constitui permissão para clonar o portal, reproduzir peças publicitárias ou apresentar o projeto como produto oficial CAIXA. Continuam os controles técnicos normais: limites de chamadas, cache, timeout, tratamento de 403/429/indisponibilidade e preservação de origem. Não há uma nova confirmação a pedir ao usuário.

### EuroMillions

**Escolher SELAE — Loterías y Apuestas del Estado, operador oficial espanhol — como fonte principal por data.** Seu [canal oficial de compartilhamento](https://www.loteriasyapuestas.es/en/resultados-ultimos-sorteos) oferece instruções para apresentar resultados em outros sites. O arquivo disponibilizado pelo operador usa diretamente o serviço JSON abaixo; não foi descoberto por contorno de proteção.

```text
https://www.loteriasyapuestas.es/servicios/fechav3?game_id=EMIL&fecha_sorteo=YYYYMMDD
```

O [módulo oficial oferecido](https://www.loteriasyapuestas.es/f/loterias/resultados/euromillones.html?game_id=EMIL&fecha_sorteo=20261027) demonstra essa ligação. As sondagens públicas não exigiram conta, chave ou pagamento. Os [termos gerais](https://www.loteriasyapuestas.es/es/centro-de-ayuda/informacion-pie/politica-de-uso-de-la-web-y-sitios-moviles-webs-juego-y-corporativa) permitem uso particular e preservam direitos sobre outros conteúdos. A decisão de engenharia é usar o canal para a integração factual e análise privada atuais, observando o escopo específico de compartilhamento oferecido. Não se declara uma licença aberta irrestrita para revender a base financeira inteira, copiar o site ou suas marcas.

Os [arquivos históricos oficiais FDJ](https://www.fdj.fr/jeux-de-tirage/euromillions-my-million/historique) continuam como caminho de carga histórica em lote e conferência. A página oferece os arquivos desde fevereiro de 2004 e convida à criação de estatísticas próprias. Essa destinação específica precisa ser considerada junto do aviso geral de direitos; não tratar todo download de resultados para análise como dependente de nova autorização individual. Os arquivos existentes e seus hashes foram reaproveitados, sem baixar todas as partições novamente.

A escolha resolve a antiga EXT-03 de seleção de uma fonte para este uso. Ela não equivale a um certificado jurídico para qualquer finalidade futura. Mudança para venda de dados brutos, reprodução integral de bases ou conteúdo protegido é outro escopo; não é condição para reiniciar a descoberta atual.

## Prova técnica do novo canal EuroMillions

| Data solicitada | Matriz aplicável | Faixas observadas | Conferência dos números |
|---|---|---:|---|
| 13/02/2004 | 5/50 + 2/9 | 12 | Coincide com o histórico local já qualificado |
| 10/05/2011 | 5/50 + 2/11 | 13 | Coincide com o histórico local já qualificado |
| 27/09/2016 | 5/50 + 2/12 | 13 | Coincide com o histórico local já qualificado |
| 23/10/2026 | 5/50 + 2/12 | 13 | Coincide com a amostra oficial FDJ preservada |
| 27/10/2026 | 5/50 + 2/12 | 13 | Coincide com a amostra oficial FDJ preservada |

As cinco respostas são JSONs reais HTTP 200, com a data solicitada e identidade da fonte preservadas. As **26 faixas recentes de ganhadores europeus** conferem com FDJ, sem conflito. A disponibilidade em 2004 e nas fronteiras de regras demonstra alcance histórico; não certifica individualmente todos os resultados intermediários. A carga integral e a reconciliação de seus manifestos são atividades da SPEC-0034, aproveitando os caminhos já identificados.

A data sem sorteio de **26/10/2026** retorna HTTP 200 com uma **string JSON informando ausência**, não uma lista vazia nem um sorteio. O adaptador futuro deve distinguir conteúdo de transporte, confirmar a data/identidade solicitadas e não substituir ausência pelo último resultado.

Foram dez GETs adicionais limitados, com timeout de 20 segundos, limite de 4 MiB, TLS e hostname verificados, sem retries, paginação ou varredura de concursos. Nove corpos novos foram preservados (217.718 bytes); a página de histórico FDJ tem receipt/hash sem duplicação de seu HTML completo. Os scripts de inspeção são temporários; nenhum coletor de produção foi criado.

## Contrato de campos EuroMillions

| Campos | Disponibilidade e interpretação para integrar |
|---|---|
| `game_id`, `id_sorteo` | `EMIL` obrigatório; referência SELAE como string. Não converter o ID composto em concurso ordinal nem misturar com IDs internos da API legada |
| `fecha_sorteo`, `dia_semana`, `anyo` | Data do resultado disponível. O horário não tem offset e não foi certificado como instante efetivo do sorteio; data local e instante de coleta permanecem separados |
| `combinacion` | Sete inteiros na ordem cinco principais + duas estrelas; validar segundo a matriz vigente na data |
| `escrutinio[].tipo` | Categoria de acertos principais/estrelas e ordinal da fonte. Preservar ambos; a ordem histórica não é universal |
| `escrutinio[].premio` | Prêmio publicado por faixa em EUR, como texto decimal com vírgula. Conservar o valor do operador; não substituir por rateio francês/austríaco nem chamar de valor resgatado |
| `escrutinio[].ganadores_eu` | Ganhadores europeus nas amostras recentes; `null` em 2004 continua desconhecido, nunca zero inferido |
| `escrutinio[].ganadores` | Contagem do operador/país nas amostras recentes. A abrangência de valores legados não foi estabelecida para todo o histórico; manter contexto da fonte e impedir agregação territorial indevida |
| `premio_bote`, `fondo_bote` | Observações diferentes de jackpot/fundo publicadas. Não são intercambiáveis com prêmio por ganhador, pagamento realizado ou estimativa do próximo concurso |
| `apuestas`, `recaudacion`, `recaudacion_europea`, `premios` | Campos adicionais existentes. Conservar seus valores brutos e contexto; abrangência, base financeira e auditabilidade históricas não estão certificadas. `-` é ausência, não zero |
| `millon`, `escrutinio_millon` | Rifa espanhola vinculada, com código, identificação, valor e faixas próprios; ausência em períodos anteriores não é erro da combinação comum |
| `lluvia`, `escrutinio_lluvia`, `mw_*` | Extensões nulas observadas. Preservar como metadados; conteúdo futuro não nulo requer interpretação específica antes de cálculo |
| `cdc` | Metadado da fonte; sem identidade universal presumida |

O manifesto guarda a classificação de cada campo. Ausências e semânticas não certificadas fazem parte do contrato de disponibilidade; o sistema deve mostrá-las assim, sem fabricar completude financeira. Não há uma tarefa genérica de pesquisar toda informação imaginável antes de implementar o produto.

**Exemplos que a integração deve preservar:** em 2004, `premio_bote="0"` coexiste com primeiro prêmio publicado de EUR 15 milhões; em 2011, as faixas 6/7 correspondem a 4+0 e 3+2, enquanto em 2026 aparecem na ordem inversa. Em 27/10/2026, a terceira faixa publica EUR 630.456,70 na SELAE e EUR 630.456,60 na FDJ. A combinação e os ganhadores Europa conferem; isso não torna os rateios nacionais iguais.

## Alternativas avaliadas

| Alternativa | Decisão |
|---|---|
| FDJ oficial | Manter o arquivo histórico oferecido para estatísticas e como referência; não depender de reprodução integral de conteúdo protegido do site |
| Áustria/win2day | Manter amostra complementar para ganhadores e estados financeiros; não fundir quotas de países |
| Bélgica oficial | Fonte rica identificada, mas não qualificada como canal operacional nesta sessão; a tentativa direta anterior retornou 405 |
| Loteria API comercial | Não escolhida para o orçamento zero: a [página de preços](https://loteriasapi.com/planes) informa 50 chamadas gratuitas totais e sete dias de histórico, contrariando material promocional sobre franquia mensal e histórico amplo. Nenhuma conta/chave/assinatura foi criada |
| APIs de terceiros no GitHub | Licença do software e alegação de histórico completo não substituem proveniência e contrato dos dados. Não preferir a um canal do operador oficial já verificado |

Nenhuma fonte observada oferece, como um único contrato certificado, todos os resultados, regras históricas completas, resgates, moedas e extensões nacionais de todos os países. A solução escolhida é ampla para os resultados comuns e tem complementos explícitos, com estados de indisponibilidade onde necessário.

## Aceite consolidado e limites de operação

| Critério da etapa 2 | Estado |
|---|---|
| Seis históricos, formatos, quantidades e qualidade conhecidos | Concluído; inventário e diagnóstico anteriores reaproveitados |
| Fontes, transporte e possibilidades de atualização conhecidos | Concluído para os perfis declarados; testes/receipts anteriores e novos ligados no manifesto |
| Campos existentes, ausentes e deriváveis separados | Concluído; matrizes anteriores e contrato SELAE acima |
| Regras numéricas históricas e diferenças entre modalidades registradas | Concluído; conservar versões e categorias independentes de seus ordinais |
| Caminho para recuperar a defasagem definido | Concluído; carga/reconciliação ainda será executada na entrega funcional |
| Fonte EuroMillions principal escolhida e base de uso explicitada | Concluído para o uso factual privado atual; canal oficial de compartilhamento verificado |
| Preservação e provas reproduzíveis | Concluído; hashes e testes offline no manifesto |
| Próxima entrega definida | SPEC-0033, sem novo inventário intermediário |

**Double Play/Colorado:** o complemento foi localizado e sua cobertura foi medida na qualificação anterior, mas os termos específicos do Colorado continuam restringindo automação. Não há nova consulta ou ativação Colorado nesta tarefa. O requisito operacional de obter um canal permitido para Double Play/enriquecimento Colorado permanece identificado na SPEC-0034; não foi resolvido por troca de rótulo ou retirado silenciosamente. Esse estado não invalida o conhecimento já concluído dos resultados principais Powerball. A interface futura precisa diferenciar as duas séries e sua disponibilidade.

Não se declara que todos os provedores concederam licença irrestrita, que há SLA gratuito ou que a atualização do banco já ocorreu. Esses fatos não são critérios de descoberta: são decisões/aceites específicos da integração, implantação e operação. Os bloqueios genéricos CAIXA/EuroMillions da versão documental anterior foram substituídos pelas decisões acima; a restrição concreta Colorado foi preservada.

## Validação e próxima tarefa

[Dezoito testes novos](../../tests/test_stage2_closure_samples.py) verificam bytes das amostras, componentes e identidades históricas/recentes, confronto com referências, faixas variáveis, estados financeiros, retorno sem sorteio e cadeia oficial de compartilhamento. Somados ao conjunto anterior, **98 testes offline foram aprovados**, sem alterações de produção. O manifesto contém a execução e a conferência de preservação dos arquivos existentes.

Os seis dados brutos, relatórios anteriores, dependências, migrations e código existente foram preservados. Foram atualizados somente os documentos de navegação/planejamento/aprendizados; esta entrega acrescenta evidências e testes de qualificação, sem carregar SQL ou ligar tarefas programadas.

**Próxima tarefa única: [SPEC-0033 — Primeiro fluxo online Mega-Sena](../specs/SPEC-0033-primeiro-fluxo-online-mega-sena.md).** Implementar o perfil já qualificado, preparar o ambiente persistente e o primeiro acesso privado funcional. A SPEC-0034 integra/importa/atualiza as demais modalidades usando este encerramento. Nenhuma delas foi executada por esta tarefa.
