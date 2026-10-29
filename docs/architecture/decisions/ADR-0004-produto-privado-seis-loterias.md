# ADR-0004 — Produto privado para seis loterias e execução sem servidor permanente

## Estado e contexto

Aceita como decisão de arquitetura em 27/10/2026, na consolidação da etapa 3. O usuário confirmou privacidade integral, aprovação pessoal dos cadastros, seis loterias funcionais e preferência por atualização cerca de uma hora ou um dia após o sorteio, com custo inicial zero. Fontes e diferenças foram qualificadas na etapa 2. Ainda não há ambiente operacional, API final, frontend final ou writer/leitor completo das seis.

## Decisões

1. Manter monólito modular Python e layout `app/`, com interfaces HTTP/CLI e infraestrutura substituível. Next.js/TypeScript é o frontend separado. Não migrar diretórios nem duplicar pipelines por estética.
2. Escolher Vercel para frontend e uma função FastAPI, Supabase para PostgreSQL/Auth/Storage privado e Actions para jobs efêmeros. A decisão de fornecedor não equivale a provisionamento; instalação/pacote/cotas/eligibilidade/conexões reais serão comprovados na implementação. OCI é opcional, não unidade obrigatória de hospedagem.
3. Usar Google OAuth/PKCE via Supabase como autenticação inicial, sessão opaca HttpOnly conduzida pelo backend e aprovação de usuário no domínio do aplicativo. MFA é obrigatório para administração. Login social não aprova cadastro; recuperação de credenciais fica no provedor, sem SMTP próprio nesta versão.
4. Expor somente conjuntos de revisões aprovados, com manifesto e ponteiro ativo por loteria. Baseline e política recebem aprovação administrativa; acréscimos elegíveis são promovidos pela política versionada, permitindo atualização automática. Preservar `published_revision_id`/constraint atuais; não implementar publicação individual só para alimentar a primeira tela.
5. Dispatcher horário seleciona jobs devidos após sorteio +1h e reconciliação D+1 às 09h da fonte. Modo diário é alternativa expressa para cota/fonte; sem compromisso de cinco/quinze minutos. Progresso, locks, idempotência e decisão são duráveis no banco, não no evento cron.
6. A primeira consulta funcional planejada cobre as seis loterias. SPEC-0033 entrega acesso/consulta e perfis persistentes básicos das seis; SPEC-0034 completa defasagem/fontes atuais e agenda; SPEC-0035 análises/previsões/catálogo; SPEC-0036 operação/release. Nomes antigos de arquivos de SPEC permanecem para preservar links, mas o escopo vigente é o corpo atualizado.
7. Manter formatos, identidades, componentes, dinheiro, calendários e vigências por perfil. Cadastro futuro escolhe perfis implementados e começa em rascunho; não gera coletores arbitrários. Double Play/Colorado permanece com restrição própria, sem falsa disponibilidade global.

## Consequências e revisão

Reduzir processos permanentes e novas dependências não dispensa recuperação, autorização, backup ou testes. A função web não treina modelos; disco do runner não guarda raw definitivo. Conta, Google OAuth/MFA e backup/restauração devem ser comprovados antes do lançamento. Uma falha de serviço/quota pode bloquear o aceite operacional sem invalidar a separação do núcleo.

Substituir esta decisão somente por evidência de incompatibilidade da implantação, elegibilidade/cotas insuficientes, mudança de produto ou carga medida. Não introduzir microsserviços, broker ou GPU por antecipação. A implementação usa os contratos abaixo e registra somente descobertas que mudem decisões futuras.

## Referências normativas

- [Visão geral e aceite da etapa 3](../visao-geral.md).
- [Contratos de aplicação e frontend](../contratos-produto.md).
- [Segurança e sessões](../seguranca-e-requisitos.md).
- [Infraestrutura, calendário e recuperação](../entrega-e-infraestrutura.md).
- [Modelo de dados complementar](../../database/modelo-logico.md#8-módulos-do-produto-para-a-primeira-versão).
