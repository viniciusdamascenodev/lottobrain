# SPEC-0036 — Validação operacional e publicação

## Estado e objetivo

Planejada em 26/10/2026; não implementada. Meta do dia 4 do [plano de quatro dias](../engineering/plano-entrega-quatro-dias.md): concluir uma versão inicial online com as seis loterias, acesso controlado, análises/previsões e operação comprovada. Esta entrega integra e corrige o produto; segurança, CI e deploy começaram na SPEC-0033.

## Entradas

Critérios das SPECs 0033–0035 e [matriz obrigatória do lançamento](../engineering/plano-entrega-quatro-dias.md#critérios-obrigatórios-da-primeira-versão), configuração dos serviços, evidências por fonte, snapshots/modelos e instruções operacionais. Critério obrigatório bloqueado continua pendente, mesmo se os demais estiverem prontos.

## Atividades integradas

1. Executar as jornadas completas de conta pendente/aprovada/revogada, recuperação, usuário, administrador e operador, com acesso direto à API e testes negativos.
2. Verificar seis fronteiras, política +1h/D+1 (ou modo diário declarado), promoção automática autorizada, correção, retomada e alertas; não confundir status do job com dados atualizados. Exercitar falha de fonte/agendador e recuperação controlada.
3. Conferir dashboard/explicações, acessibilidade essencial e previsões/versionamento; retirar dependências do protótipo que apresentem números artificiais como reais.
4. Validar pipelines GitHub Actions, build e promoção de artefato para ambiente final, migrations compatíveis, health checks, TLS, segredos e privilégio mínimo. Rodar a regressão comum e SQL completa da release e E2E das jornadas críticas, com isolamento e tempo observado.
5. Gerar backup do banco e artefatos necessários, restaurar em ambiente isolado e conferir integridade/consulta; ensaiar rollback de aplicação compatível com o schema. Configurar a execução recorrente de backup, sem confundir teste manual com automação ativa.
6. Publicar a versão revisável e verificar a URL final, conexão persistente, disparo de jobs, controle de acesso e métricas. Ações externas dependentes de conta/custo/aprovação são preparadas antes da decisão do usuário, sem anunciar publicação antes da confirmação real.
7. Entregar runbook curto de deploy, reprocessamento seguro, fonte indisponível, gestão de acesso, backup/restauração e rollback, com responsáveis e referências dos serviços configurados.

## Aceitação

| ID | Prova necessária |
|---|---|
| S36-01 | Todos os critérios obrigatórios cumulativos 0033–0035 aprovados; nenhum bloqueio essencial escondido por status concluído |
| S36-02 | Usuário autorizado percorre o produto online; anônimo/pendente/revogado e usuário comum em administração são recusados; sessões, recuperação, MFA administrativo e revogação comprovados |
| S36-03 | Seis loterias com fronteira/instante de verificação atuais, jobs operacionais e alertas exercitados; alterações da fonte geram diagnóstico em vez de promoção indevida |
| S36-04 | CI obrigatório e execução de release identificáveis; testes de integração/E2E/regressão aprovados, segredos ausentes dos artefatos e erros sanitizados |
| S36-05 | Backup restaurado e consulta/integridade conferidas, backup recorrente configurado e rollback ensaiado com instruções utilizáveis |
| S36-06 | URL final/versão, serviços, resultado das jornadas, dashboards/alertas e runbook conferidos; configuração pronta ou preview local não equivalem a deploy final |

## Evidência e encerramento

Manter um registro de aceite com critério, resultado, referência da prova, instante e pendência. Referenciar as evidências anteriores, sem reescrever certificados históricos para parecerem atuais. Incluir duração observada dos procedimentos operacionais e limitações de fonte/modelo.

O aceite de recuperação prova dump e manifesto no mesmo corte, objetos requeridos verificados e dependências de schema recriáveis. Pacote com objeto faltante permanece `incomplete`, sem apagar/substituir o último backup completo. Restaurar e consultar conjuntos das seis, invalidando sessões; auditar esse comportamento em execução, não apenas pela presença de um arquivo de dump.

Só marcar concluída após os critérios. Se o prazo chegar com requisito obrigatório bloqueado, entregar o estado real e a decisão necessária para liberar ou replanejar; não substituir critério, inventar dados ou anunciar produto completo. Recursos adicionais e melhorias posteriores ficam em backlog priorizado, sem disparar uma nova implementação nesta SPEC.
