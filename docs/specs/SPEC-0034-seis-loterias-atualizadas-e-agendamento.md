# SPEC-0034 — Seis loterias atualizadas e agendamento

## Estado e objetivo

Planejada em 26/10/2026; não implementada. Meta do dia 2 do [plano de quatro dias](../engineering/plano-entrega-quatro-dias.md): Mega-Sena, Lotofácil, +Milionária, Powerball, Mega Millions e EuroMillions com cobertura atual conferida, atualização recorrente e situação operacional visível.

## Reuso e dependências

Usar ambiente/acesso/leitura e perfis históricos das seis entregues na SPEC-0033, normalizadores e catálogo versionado. O código existente antes dessas entregas continua mais desenvolvido para Mega-Sena; não confundir perfis planejados com implementação já presente. Esta SPEC completa adaptadores incrementais, cobre a defasagem e automatiza as seis, sem repetir a consulta básica da 0033.

Ponto de partida vigente: [encerramento da etapa 2](../data/encerramento-etapa-2.md), que reaproveita as amostras anteriores e acrescenta o contrato oficial SELAE por data para EuroMillions. CAIXA cobre as três brasileiras; OPEN-NY é a escolha para principais recentes dos EUA; históricos existentes e arquivos oficiais FDJ mantêm papéis próprios. Implementação dos adaptadores ainda é parte desta SPEC. Respeitar multiplicadores, trevos, encoding/escopos financeiros e calendários. Nenhuma captura de inspeção foi importada no banco ou promovida no catálogo.

O [fechamento complementar da etapa 2](../data/fechamento-etapa-2.md) esclareceu as exceções de calendário e conferiu 756 registros posteriores aos arquivos originais nos snapshots. Usar exportações CAIXA no host oficial configurado `servicebus3`; dois concursos Lotofácil compartilham 20/06/2026 e precisam manter identidades oficiais distintas. FDJ/SELAE têm amostras até 27/10. O rateio Mega-Sena desde 3073 tem vigência própria, sem novas faixas de acertos. O transporte local Python NY já passou; repetir apenas o smoke test necessário no executor real durante implantação.

A [qualificação técnica anterior](../data/qualificacao-final-etapa-2.md) comprovou os 68 Double Play ausentes em NY e 63 sobrepostos, além de 1.118 contagens de ganhadores Europa FDJ/Áustria. A restrição Colorado permanece: EXT-02 exige canal permitido ou alternativa qualificada para esse complemento, sem contorno manual ou falsa alegação de sincronização completa da série. O encerramento vigente substitui EXT-03 pela escolha SELAE, com canal oficial de compartilhamento e contrato para uso factual privado. Implementar seu perfil por data, inclusive HTTP 200 com string de ausência, referências externas, 12/13 faixas históricas e mapeamento por acertos, sem assumir ordem fixa. Não promover campos financeiros legados de abrangência incerta a totais auditados; conservar valores e proveniência de cada operador. O conjunto de qualificação passou em 98 testes offline.

## Atividades integradas

1. Reconfirmar a fronteira atual de cada fonte no momento da operação, reutilizando formatos, identidades, calendários/fusos e campos já qualificados na etapa 2. Resolver as condições de uso/transporte registradas ou qualificar alternativa quando necessário; conservar origem e limitações. Não repetir o inventário nem apresentar fonte restrita como liberada.
2. Integrar fontes atuais e reconciliação incremental aos perfis de gravação/leitura históricos entregues na 0033, com migrations somente quando necessárias. Preservar regras, moedas, identidades, especiais e séries vinculadas.
3. Carregar os históricos reais e completar o período faltante com coleta orçada e retomável. Avaliar snapshot histórico atualizado para grandes defasagens quando qualificado; conservar evidência anterior e reconciliar sobreposições em vez de sobrescrever o raw original.
4. Definir uma aprovação verificável por conjunto/modalidade e compor atualizações incrementais. Não copiar para Powerball/EuroMillions a estratégia de sequência oficial numérica da Mega-Sena quando a identidade disponível é outra.
5. Agendar segundo a [política vigente](../architecture/entrega-e-infraestrutura.md): primeira tentativa devida após sorteio +1h, reconciliação D+1 às 09h locais e modo diário quando necessário por cota/fonte. Garantir exclusão concorrente, idempotência, timeout, espaçamento, cooldown e recuperação de disparo perdido. Não prometer uma hora exata ou cinco/quinze minutos. Promover acréscimos elegíveis por política aprovada, sem exigir clique humano por sorteio; conflitos permanecem em revisão.
6. Integrar à API/interface o diagnóstico por modalidade: fronteiras observada/confirmada, última tentativa/sucesso, próximo job, atraso/lacunas e erros sanitizados. Habilitar alertas acionáveis ao operador.

## Aceitação

| ID | Prova necessária |
|---|---|
| S34-01 | As seis modalidades possuem manifesto/cobertura e fronteira conferida contra a fonte no instante registrado, sem lacunas não explicadas no conjunto declarado completo |
| S34-02 | Perfis de cada fonte/regra têm testes reais de mapeamento e roundtrip SQL/leitura; financeiros e séries especiais não são achatados nem inferidos sem evidência |
| S34-03 | Pelo menos uma atualização operacional real por fonte e um disparo real do agendador comprovados; não é necessário esperar um novo sorteio durante a SPEC para provar a execução, mas repetição sem novidade deve ser idempotente |
| S34-04 | Correção, fonte atrasada, retorno inválido, corrida, interrupção e limitação não promovem conteúdo inválido, não saltam cobertura e preservam a evidência |
| S34-05 | Consulta protegida e painel mostram atualidade/atraso por fonte com timestamp; scheduler parado ou fonte inacessível não mantém status atualizado indefinidamente |
| S34-06 | Job administrativo e disparo programado exigem autenticação própria e privilégio mínimo; registros permitem investigar falha sem expor segredos |
| S34-07 | Política +1h/D+1 ou modo diário explicitamente configurada, recuperação de disparo perdido e promoção segura demonstradas nas seis; nenhuma fonte restrita habilitada por contorno |

## Validação e evidência

Cada modalidade tem contrato do parser, teste de perfil SQL e prova operacional da cobertura declarada. Reutilizar fixtures reais e preparar bases isoladas uma vez por suíte. Agrupar testes compartilhados; manter testes específicos onde as regras diferem. Cobertura histórica integral roda no aceite de cada carga e quando mapeamento/parser/schema relevante mudar, sem repetição por cenário de interface.

Registrar por fonte último resultado disponível observado, último confirmado, instante da comparação, totais, intervalos faltantes, diagnósticos e execução agendada. Uma captura isolada recente não comprova atualização completa. Calendário esperado não substitui consulta à disponibilidade efetiva do resultado.

Exercitar chave de job global e por fonte sem brecha por NULL, conflito de parâmetros, lease expirado e troca de modo horário/diário respeitando o mesmo lock/cooldown. Conflito de revisão deve produzir qualidade `under_review` independente da atualidade, manter o último conjunto aprovado com aviso e suspender promoções/previsões afetadas até decisão.

## Limites e passagem

Fonte indisponível sem alternativa qualificada é bloqueio explícito do requisito de seis loterias, não motivo para fabricar sucesso ou reduzir o escopo silenciosamente. Não desenvolver painel analítico completo, novos algoritmos ou motor universal de scraping nesta SPEC.

Ao comprovar os critérios, registrar descobertas reutilizáveis dos novos perfis/jobs e seguir para **SPEC-0035 — Painel analítico, previsões e catálogo**.
