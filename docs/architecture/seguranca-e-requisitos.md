# Segurança e requisitos não funcionais

## Modelo de acesso

Decisão vigente de 27/10/2026: **todo conteúdo do LottoBrain é privado**, inclusive resultados, catálogo, estatísticas, previsões, relatórios, exports e diagnóstico de jobs. O endereço do site pode ser alcançável pela internet; isso não torna os dados públicos.

| Papel | Permissões gerais |
|---|---|
| anônimo | apenas estrutura da entrada e início/callback de autenticação; nenhum dado do produto |
| autenticado pendente/rejeitado/revogado | somente estado da própria solicitação, saída e procedimentos de conta permitidos; nenhum dado do produto |
| usuário aprovado | consulta das seis loterias, análises e previsões disponibilizadas; preferências próprias |
| administrador aprovado com MFA | consultas e gestão de usuários, catálogo, aprovações e comandos operacionais auditados |
| identidade técnica | comandos de CI/jobs/backup estritamente necessários; não é conta de usuário nem administrador implícito |

Permissões são verificadas no caso de uso. A interface pode esconder ações, mas nunca é a barreira de segurança.

Papéis analista/operador separados ficam para necessidade concreta. Inicialmente usar usuário/administrador e identidades técnicas restritas, sem um editor universal de permissões. Usuários autenticados começam `pending`; somente o proprietário/administrador pode aprovar. O cadastro não herda acesso de e-mail confirmado ou login social. Revogação altera o perfil e invalida as sessões locais na mesma transação; toda consulta revalida o estado atual do perfil.

## Autenticação

- **Supabase Auth com Google OAuth/PKCE** é a integração inicial escolhida. Primeiro login cria solicitação de acesso interna; recuperação das credenciais ocorre no Google. Não implementar armazenamento próprio de senha nem prometer recuperação por SMTP não configurado. A aplicação terá cadastro por esse fluxo; e-mail/senha é extensão posterior se necessária. [Integração oficial](https://supabase.com/docs/guides/auth/social-sign-in/auth-google).
- Backend conduz o fluxo com o cliente oficial, estado de uso único, PKCE e callback em allowlist; redirects externos fornecidos pelo usuário são recusados. Estado de login expira em dez minutos. Tokens do provedor ficam no servidor, cifrados quando persistidos, com chave fora do banco e dos backups. Não armazenar tokens de acesso/refresh em `localStorage`, URLs, logs ou dados de página.
- A tentativa OAuth é vinculada ao navegador por cookie transitório `__Host-lb_login`, opaco, `HttpOnly`, `Secure`, `SameSite=Lax`, sem `Domain` e com digest associado à tentativa no servidor. Callback exige vínculo, estado válido e verifier correspondente; somente conhecer o ID/estado não basta para trocar o código. Consumir a tentativa atomicamente e remover o cookie, recusando replay, fluxo de outro navegador e tentativa anterior substituída. Usar uma tentativa ativa por navegador inicialmente, sem extensão experimental de fluxos sobrepostos. Respeitar a validade menor do código no provedor; dez minutos de tentativa local não prolongam o código. [PKCE e vínculo ao navegador](https://supabase.com/docs/guides/auth/sessions/pkce-flow).
- Sessão da aplicação usa identificador opaco aleatório em cookie `__Host-lb_session`, `HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/`, sem `Domain`. No banco, guardar digest do identificador, expiração e revogação. API e frontend usam origem única com encaminhamento de `/api/v1`.
- Escritas autenticadas por cookie exigem token CSRF vinculado à sessão e validação de Origin. OAuth usa suas próprias proteções de estado/PKCE; não reutilizar token CSRF como estado de login. Renovação é serializada para não disputar refresh do provedor; mudança de privilégio rotaciona a sessão.
- Sessão de usuário: inatividade máxima de 24 horas e prazo absoluto de sete dias, com autenticação upstream válida e renovada de forma segura. Administrador: uma hora de inatividade, oito horas absolutas; mudanças de acesso, aprovação de conjuntos e ativação de fonte exigem MFA recente de até quinze minutos. Expiração/revogação upstream detectada encerra a sessão local; não aceitar token vencido ou claims do navegador como autoridade.
- Rate limit em login, recuperação, cadastro e endpoints caros.
- MFA TOTP via Supabase é obrigatório para administradores; verificar evidência `aal2` validada pelo provedor no servidor. Enrollment/desafio/renovação usam a sessão limitada de conta; sem MFA administrativo completo não há operação administrativa. MFA para usuários comuns é opcional. [Contrato do provedor](https://supabase.com/docs/guides/auth/auth-mfa).
- Segredos exclusivamente no gerenciador do ambiente.

### Bootstrap e recuperação administrativa

O primeiro administrador é vinculado por comando administrativo único, executado pelo proprietário no ambiente seguro, ao identificador de identidade **já autenticado e verificado**. Não promover o primeiro cadastrado nem usar correspondência de e-mail enviada pelo cliente. O comando é idempotente, auditado e desabilitado no fluxo HTTP. Recuperação excepcional de MFA/admin repete uma operação controlada do proprietário, revoga sessões afetadas e registra motivo; não existe endpoint público de bypass.

### Banco, arquivos e cache

- API verifica sessão e aprovação antes de cada consulta/comando; `401` indica falta de autenticação, `403` acesso pendente/revogado ou privilégio insuficiente. Objetos fora do escopo podem retornar `404` para não revelar existência.
- O navegador não consulta tabelas de domínio no Supabase Data API. Schema da aplicação não é exposto; negar acesso a `anon`/`authenticated`, aplicar RLS defensiva às relações expostas e usar papéis SQL próprios com privilégios mínimos. Credenciais privilegiadas nunca são variáveis `NEXT_PUBLIC_*`.
- Bucket de raws/modelos/exports é privado. Downloads administrativos passam por endpoint autorizado que revalida perfil/objeto; não criar links públicos ou links duradouros que sobrevivam à revogação. Dados já baixados não podem ser apagados remotamente do dispositivo do usuário.
- Respostas com dados privados, SSR e erros de conta usam `Cache-Control: private, no-store`; não entram em geração estática pública, cache compartilhado/CDN, indexação ou logs de payload. Arquivos estáticos sem dados podem usar cache normal. Preview recebe as mesmas barreiras da aplicação.
- Registro de conta, atualização de regra e mudança de dataset têm autorização independente. ID de usuário, de loteria ou de dataset enviado na requisição não concede permissão.
- Comandos administrativos revalidam estado/versão de acesso e MFA dentro da transação que confirma o efeito, serializando mudanças concorrentes do perfil. Revogação prevalece sobre comandos que ainda não foram autorizados/confirmados; não prometer apagar respostas já recebidas ou interromper retroativamente uma transferência iniciada. Nova requisição após revogação confirmada é recusada.

## Ameaças prioritárias

| Ameaça | Controles principais |
|---|---|
| tomada de conta | provedor de identidade, rate limit, MFA administrativo, sessões revogáveis |
| elevação de privilégio | autorização central nos casos de uso e testes negativos |
| SSRF por fontes cadastradas | allowlist, resolução segura, bloqueio de redes privadas e redirects controlados |
| conteúdo malicioso da fonte | limites de tamanho, parser defensivo, sem execução de conteúdo |
| corrupção por coleta parcial | raw primeiro, transação, idempotência e revisão |
| vazamento em logs | redaction e proibição de tokens/senhas/PII |
| alteração de regra sem rastreio | aprovação, versionamento e auditoria append-only |
| dependência comprometida | lockfile, atualização controlada, análise de vulnerabilidades e SBOM futura |

## Privacidade

Coletar apenas dados pessoais necessários para conta, segurança e preferências. Definir antes do lançamento:

- base legal e política de privacidade;
- retenção por categoria;
- exportação e exclusão de conta;
- separação entre exclusão pessoal e auditoria legalmente necessária;
- minimização de IP e identificadores de dispositivo;
- fornecedores que processam dados.

Defaults técnicos iniciais: limpar estados OAuth após dez minutos, sessões revogadas/expiradas após 30 dias e logs operacionais após 30 dias. Solicitações rejeitadas sem uso podem ser removidas após 30 dias; auditoria administrativa sanitizada tem horizonte inicial de 180 dias, com pseudonimização ao excluir conta. Retenção de dados pessoais precisa corresponder à política entregue antes do lançamento; não remover evidência de loteria referenciada por dataset para limpar uma conta. Exclusão de conta revoga acesso imediatamente; limpeza e tratamento dos backups respeitam sua retenção documentada.

## Metas iniciais

Estas metas são proporcionais a um produto inicial e devem ser revisadas com dados reais:

| Aspecto | Meta inicial |
|---|---|
| disponibilidade da aplicação privada | objetivo interno de 99,5% mensal, ainda sem comprovação ou SLA de fornecedor gratuito |
| latência API de leitura | p95 abaixo de 500 ms sem incluir jobs |
| atualização de resultado | primeira tentativa devida em torno de uma hora após o sorteio; reconciliação às 09h locais do dia seguinte; alvo D+1 se a fonte publicou e os serviços estão disponíveis |
| RPO | objetivo de até 24 h para banco e artefatos com backup concluído; imutabilidade não implica perda zero em desastre do provedor |
| RTO | até 4 h |
| retenção de auditoria | horizonte técnico inicial de 180 dias, com dados sensíveis minimizados |
| acessibilidade | WCAG 2.2 AA nas jornadas principais |

Metas não devem ser chamadas de SLO operacional até existirem telemetria e capacidade de medição.

Não há mais compromisso de cinco/quinze minutos. Política detalhada, retentativas e exceções estão em [infraestrutura](entrega-e-infraestrutura.md). Resultado validado pode ser disponibilizado antes de D+1; fonte ainda não publicada fica `awaiting_source`, sem promoção de dado incompleto ou declaração falsa de atualidade.

## Observabilidade

Cada requisição e job recebe `correlation_id`. Logs estruturados devem conter evento, módulo, resultado, duração e identificadores técnicos seguros.

Métricas mínimas:

- sucesso, falha e duração por fonte;
- último resultado observado e publicado;
- candidatos novos, repetidos, corrigidos e em quarentena;
- tamanho e hash do artefato;
- fila e idade dos jobs;
- erros e latência da API;
- login, bloqueio e eventos administrativos;
- duração, custo e resultado de experimentos.

Alertas devem ser acionáveis. Ausência esperada de novo concurso não é incidente; atraso além da janela é.

## Estratégia de testes

| Camada | Objetivo |
|---|---|
| unidade | invariantes e transformações puras |
| propriedade | espaços combinatórios e limites |
| contrato | formatos externos e respostas da API |
| integração | PostgreSQL, storage e transações |
| arquitetura | dependências entre módulos |
| segurança | autorização, validação e abuso |
| frontend | componentes, acessibilidade e estados |
| E2E | jornadas críticas em ambiente efêmero |
| migração | upgrade e downgrade seguro quando suportado |
| restauração | comprovar backup e recuperação |

Cobertura percentual auxilia, mas não substitui testes de risco e fronteiras.
