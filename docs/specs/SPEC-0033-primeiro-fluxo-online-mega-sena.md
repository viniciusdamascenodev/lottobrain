# SPEC-0033 — Plataforma privada e consulta das seis loterias

## Estado e objetivo

Planejada em 26/10/2026; escopo ampliado em 27/10 pela etapa 3. **Em execução, com fundação da etapa 5 validada na branch de revisão, sem aceite da capacidade funcional.** Ambiente, testes, HTTP/frontend mínimos, CI real aprovado e proteção da `main` estão documentados na [entrega de engenharia](../engineering/etapa-5-desenvolvimento-ci.md); não há autenticação ou consulta operacional das seis comprovada por esse avanço. O nome histórico deste arquivo é preservado para manter referências. A primeira entrega deixa de encerrar com somente Mega-Sena: usuário aprovado deve consultar dados reais aprovados de Mega-Sena, Lotofácil, +Milionária, Powerball, Mega Millions e EuroMillions online.

Esta é a primeira capacidade funcional do [plano de entrega](../engineering/plano-entrega-quatro-dias.md), agora maior pelo requisito explícito das seis. As datas anteriores são metas originais, não prova de execução ou promessa nova de duração. Atualização recorrente e cobertura recente completa pertencem à SPEC-0034; painel analítico completo à SPEC-0035.

## Reuso e decisões fechadas

Desenho concluído na etapa 4: [jornadas](../design/etapa-4-experiencia-visual.md), [sistema visual](../design/sistema-visual.md) e [protótipo/uso](../design/prototipo/README.md). Reutilizar navegação, histórico/detalhe, estados de acesso e componentes; substituir cenários locais por sessão/autorização reais. A demonstração não implementa esta SPEC.

Usar [arquitetura consolidada](../architecture/visao-geral.md), [contratos do produto](../architecture/contratos-produto.md) e [fontes qualificadas](../data/encerramento-etapa-2.md). Reutilizar domínio, catálogo, seis normalizadores, regras, migrations e evidência. O writer/leitor SQL atual mais desenvolvido é Mega-Sena; esta SPEC inclui os perfis necessários à consulta básica das outras cinco, sem fingir que já existem.

Implantação escolhida: Next.js/TypeScript e FastAPI na Vercel, PostgreSQL/Auth/Storage privado no Supabase e CLI/CI no Actions. Autenticação Google/Supabase, aprovação interna e MFA administrativo. Leitura por conjuntos aprovados, sem expor candidatos ou remover `publication_not_implemented`. Fixar novas versões/lockfiles no primeiro build reproduzível. Não abrir nova rodada genérica de arquitetura ou inventário.

## Atividades integradas

1. Validar conta/cotas/elegibilidade, API Python mínima, callback de autenticação, SQL/TLS/pooling e storage privado da composição escolhida. Preparar execução local, configurações por ambiente e CI; segredos por canal seguro, sem assinatura paga autorizada.
2. Implementar cadastro via Google, pendência, aprovação/revogação pelo proprietário, sessão opaca, recuperação no provedor e MFA administrativo. Proteger API/SSR/arquivos contra acesso direto. Bootstrap seguro único do proprietário, nunca primeiro cadastrado automático.
3. Implementar conjuntos aprovados e perfis de gravação/leitura das seis, sobre o núcleo existente. Gerar/aprovar manifestos históricos reais com fronteira/diagnósticos; testar roundtrip por perfil e migrations forward. A baseline/política de promoção exige aprovação; acréscimos elegíveis futuros seguem essa política.
4. Compor API única por slug e páginas básicas compartilhadas para as seis: concursos, filtros, componentes, regras, fonte e atualidade. Sem cinco placeholders ou dados do protótipo; defasagem aparece honestamente até a carga recente da 0034.
5. Reutilizar sincronização/auditoria Mega-Sena como comando administrativo limitado e preparar CLI comum por perfil. Adaptar título JSON qualificado quando usado. Nenhuma entrada aceita shell, SQL, URL arbitrária ou perfil não suportado.
6. Demonstrar entrar→aguardar aprovação→ser aprovado→consultar cada modalidade→sair, com versão, CI e instruções. Configuração pronta sem execução externa não encerra a entrega.

## Aceitação

| ID | Prova necessária |
|---|---|
| S33-01 | Aplicação online revisável, versão/build/CI identificáveis e execução local reproduzível |
| S33-02 | Cadastro pendente, aprovação, login/logout, recuperação no provedor, revogação e MFA demonstrados; anônimo/pendente/revogado recusados também em API/arquivos |
| S33-03 | Seis conjuntos históricos reais aprovados no armazenamento persistente e consultas verificadas por perfil; cinco abas vazias ou SQL descartável não encerram |
| S33-04 | Paginação/filtros, especiais, regras e ausências preservados nas seis; fronteira verdadeira visível sem afirmar atualização ainda não entregue |
| S33-05 | Novos perfis SQL/leitura, autorização e migrations testados; nenhum candidato exposto por fallback, segredo em log ou cache público de dados |
| S33-06 | Comando limitado de sincronização/auditoria Mega-Sena existente integrado, infraestrutura comprovada e partes ainda não operacionais identificadas; agendamento das seis pertence à 0034 |

## Validação e limites

Reusar os 98 testes offline e fixtures anteriores conforme o código afetado, sem repetição por cerimônia. Acrescentar integração SQL dos perfis/datasets, testes HTTP/acesso e E2E da jornada das seis. Não recarregar todo histórico por componente; verificar acesso direto à API e storage.

O aceite de identidade inclui callback sem vínculo ao navegador, replay, tentativa expirada/substituída e revogação concorrente com comando administrativo. Esses cenários são critérios futuros de implementação; a auditoria documental da etapa 3 não os apresenta como testes já executados.

Esta SPEC não entrega gráficos completos, treino ou atualização recorrente; entrega consulta básica real das seis com acesso seguro. Fonte essencial inacessível, perfil faltante ou serviço indisponível mantém o critério pendente. Não reduzir silenciosamente para Mega-Sena. Seguir, após aceite real, para **SPEC-0034 — Seis loterias atualizadas e agendamento**.
