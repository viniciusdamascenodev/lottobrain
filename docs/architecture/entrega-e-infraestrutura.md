# Entrega, infraestrutura e operações

## Implantação inicial decidida

Decisão arquitetural de 27/10/2026: **Vercel para Next.js e FastAPI, Supabase para PostgreSQL/Auth/Storage privado e GitHub Actions para execução Python efêmera**. Provedores não foram provisionados nesta etapa. Custos iniciais zero são requisito; elegibilidade, acessos, configuração, consumo e smoke tests são aceites de implantação, sem reabrir a decisão arquitetural por rotina.

| Unidade | Execução | Persistência/credenciais |
|---|---|---|
| Frontend Next.js | projeto Vercel web; `/api/v1` encaminha ao projeto API | sem dados privados estáticos, credenciais SQL ou tokens do provedor no navegador |
| FastAPI | projeto Vercel API, uma função contendo o backend modular | sessões, perfis e datasets no PostgreSQL; disco local só temporário |
| Worker/CLI | runner Linux efêmero Actions, código Python compartilhado | papéis de ingestão/análise limitados; objetos e progresso fora do runner |
| Dispatcher | workflow horário que chama CLI para selecionar jobs devidos | tabela de jobs e checkpoint são autoridade; cron não é histórico de execução |
| PostgreSQL/Auth/Storage | projeto Supabase por ambiente persistente | schema/buckets privados; portas evitam acoplamento do domínio ao SDK |

A [documentação Vercel](https://vercel.com/docs/frameworks/backend/fastapi) confirma FastAPI como uma função. Não fragmentar casos de uso em funções independentes nem executar treino/carga após resposta HTTP. O plano [Hobby](https://vercel.com/docs/plans/hobby) é destinado a uso pessoal não comercial; o uso privado atual é a hipótese de implantação, a confirmar na configuração da conta. Não contratar plano pago automaticamente.

Dependências da API terão instalação mínima separada do perfil de jobs; não incluir Selenium, treino e todo o legado no pacote web. Manter Python 3.12 existente; fixar novas versões/lockfiles no primeiro build conjunto. A API usa pool SQL limitado e conexão TLS através de pooling compatível com serverless; migrations usam conexão própria. Não depender de sessão SQL persistente entre requisições, `SET` de sessão ou locks de sessão. [Conexões Supabase](https://supabase.com/docs/guides/database/connecting-to-postgres).

## Ambientes

| Ambiente | Uso | Dados |
|---|---|---|
| local | desenvolvimento e testes | fixtures e snapshots controlados |
| preview | revisão por mudança de frontend/API | conjunto real controlado ou fixtures, com autenticação; sem credenciais de produção em PRs não confiáveis |
| staging | migração, integração e ensaio de deploy | projeto não produtivo, conjunto controlado e contas separadas |
| produção | aplicação privada online e operação real | somente usuários aprovados e papéis técnicos mínimos |

Credenciais e recursos são separados por ambiente. Nenhuma configuração de produção entra no repositório.

Dentro da cota gratuita inicial, preview compartilha o ambiente não produtivo controlado, não um projeto Supabase por PR. Callback OAuth usa domínios fixos autorizados; não liberar wildcard de previews para redirecionar sessões. PostgreSQL local/CI é descartável. Nomes de buckets, chaves de sessão, origens confiáveis e papéis são específicos do ambiente.

## Unidades de implantação

- `web`: frontend estático/SSR.
- `api`: backend HTTP sem estado local persistente.
- `worker`: jobs de ingestão e análise.
- `scheduler`: agenda e criação idempotente de jobs; pode compartilhar imagem com o worker.
- PostgreSQL gerenciado.
- Supabase Storage privado através da porta de artefatos.

O mesmo código backend atende a função HTTP e a CLI. Imagens OCI podem apoiar testes/reprodução local quando úteis, sem pressupor serviço de containers no ambiente gratuito escolhido. Migração de provedor exige trocar adaptadores/configuração, não reescrever regras.

## Política de atualização das seis loterias

1. `initial_due_at` é o horário esperado do sorteio **mais uma hora**, calculado a partir do calendário versionado e suas exceções. Brasil usa `America/Sao_Paulo`; EUA, `America/New_York`; EuroMillions, `Europe/Paris`. Horário de verão é resolvido por timezone IANA. Usar o calendário qualificado, não o relógio sem offset de um payload como instante físico comprovado.
2. Um dispatcher horário, preferencialmente fora do minuto zero (minuto 17 como default), executa apenas trabalho devido. A primeira tentativa ocorre no primeiro disparo disponível após `initial_due_at`; logo, pode ocorrer entre cerca de uma e duas horas após o sorteio, além do atraso do executor. Não prometer exatidão de uma hora.
3. Reconciliação devida às **09h no fuso da fonte no dia seguinte** verifica ausência, publicação tardia e financeiros complementares. Também é selecionada pelo dispatcher horário. Alvo de produto: resultado validado até D+1 quando publicado/acessível; fonte indisponível ou série restrita permanece sinalizada.
4. Resposta sem resultado é `awaiting_source`; não valida candidato incompleto, não avança cursor nem apaga a revisão aprovada. Retentativas técnicas elegíveis têm backoff/limite; ausência de publicação pode aguardar a reconciliação. `Retry-After`, cooldown e orçamento da fonte sempre prevalecem.
5. Disparo perdido é recuperado pelo próximo dispatcher consultando `due_at`, sem depender da existência de um evento cron antigo. Sem calendário confiável, usar reconciliação diária e estado explícito, sem inventar um horário. Exceções de múltiplos concursos no dia mantêm suas identidades oficiais.
6. Após D+1 sem resultado elegível, marcar atraso e notificar o administrador; uma tentativa diária limitada continua buscando recuperação. O administrador pode disparar execução limitada pelo mesmo caso de uso. Não há polling contínuo nem job no processo do site.

GitHub informa que [disparos agendados podem atrasar ou ser descartados](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule). Persistir execução/lease no banco, além do controle de concorrência do workflow. A execução manual e a agendada disputam o mesmo lock por fonte/fluxo; um lease vencido exige recuperação baseada em receipts/commits, nunca repetir aquisição confirmada por reflexo.

Um job canonicaliza `(kind, scope, logical_slot, policy_version)` em `idempotency_key` não nula e única, com `request_hash` para detectar reutilização indevida; o escopo inclui modalidade/fonte/fluxo ou o valor global explícito para backup. Campos opcionais nulos não podem permitir jobs duplicados. `logical_slot` identifica a intenção, não uma chave universal por data de concurso. Seleção/claim ocorrem em transação curta; rede/treino ficam fora dela; conclusão e enfileiramento de derivados são transacionais. [Modelo de jobs](../database/modelo-logico.md#8-módulos-do-produto-para-a-primeira-versão) define estados/recuperação. Checkpoints e fencing atuais da Mega-Sena não são substituídos pela fila; troca de modo horário/diário não contorna lock/cooldown da fonte.

Limites iniciais configuráveis: dispatcher com no máximo seis jobs de fonte por ciclo e dez minutos de duração; operações incrementais respeitam limites próprios por fonte e retomam em outro ciclo. Carga histórica é comando separado orçado; treino usa fila/prioridade separada, sem atrasar atualização. Reprocessar receipt existente não faz um GET novo. Double Play/Colorado não é ativado enquanto a restrição concreta registrada na etapa 2 não tiver canal permitido.

Fronteira confirmada, última disponibilidade observada, instante de verificação, `next_due_at`, falha e atraso ficam visíveis por modalidade/série. Job bem-sucedido sem novidade não prova que a fonte está atualizada indefinidamente. O relógio de atualidade não usa somente `last_success_at`.

## Pipeline de CI

A fundação implementada na etapa 5 e suas provas locais estão em [desenvolvimento e CI](../engineering/etapa-5-desenvolvimento-ci.md). O workflow foi preparado no repositório; execução remota e proteção de branch só serão consideradas comprovadas com as evidências de acesso/run. Os contratos de CD/operação abaixo continuam exigindo implementação e prova nas entregas funcionais.

```text
checkout
  → validação de formato e lint
  → análise de tipos
  → testes unitários e arquiteturais
  → testes de integração com serviços efêmeros
  → build reproduzível
  → análise de dependências e segredos
  → artefatos e relatório
```

Pull requests não fazem deploy de produção. Mudanças de schema devem incluir migração e teste.

## Pipeline de CD

```text
artefato aprovado
  → deploy staging
  → migração compatível
  → smoke tests
  → aprovação/política de promoção
  → deploy de versão identificada e promoção do endereço de produção
  → health checks
  → monitoramento reforçado
```

Rollback de aplicação não pode depender de reverter imediatamente uma migração destrutiva. Mudanças de banco seguem expand/contract: adicionar, migrar consumidores e somente depois remover.

## Infraestrutura como código

Deverá declarar:

- serviços e redes;
- banco e parâmetros de backup;
- buckets, versionamento e retenção;
- identidades de serviço e permissões;
- segredos por referência;
- domínio, TLS e políticas de borda;
- métricas, alertas e dashboards;
- budgets e tags de custo.

A composição acima é a escolha inicial. Configuração como código deve ser proporcional: configuração de deploy, migrations, workflows e inventário de variáveis/recursos; não introduzir Terraform/Kubernetes apenas para cadastrar três serviços. Provisionamento manual inevitável terá passos reproduzíveis e verificação, com segredos somente por referência.

## Backup e recuperação

- backups automáticos e recuperação pontual do PostgreSQL quando disponível;
- versionamento/imutabilidade dos raws;
- exportação de configuração crítica;
- teste periódico de restauração em ambiente isolado;
- runbook com responsáveis, tempo observado e validações pós-restauração.

Backup sem teste de restauração não conta como proteção comprovada.

No [Free Supabase](https://supabase.com/docs/guides/platform/backups), não depender de backup automático gerenciado. Escolha inicial: exportação diária consistente do schema aplicativo e manifesto de artefatos, cópia dos objetos necessários e configuração não secreta; cifrar com chave pública do proprietário (ferramenta auditada, como age) antes de enviar como artefato a **repositório de operação privado** no Actions, retenção inicial de sete dias. A chave privada e as chaves para decifrar segredos de sessão ficam fora dos serviços de origem e dos artefatos; não são commitadas. Não armazenar backups privados em repo público nem alterar sua visibilidade automaticamente.

O histórico de raws é copiado por hash e reconciliado com o manifesto. Backups de banco sem objetos não recuperam o produto. Após restauração, invalidar sessões e reautenticar usuários; reconfigurar Auth/OAuth e verificar vínculos de identidade. Se o provedor gerar novos IDs, o proprietário deve reconciliar identidades verificadas, sem promover usuários por coincidência de e-mail. A restauração deve provar leitura de conjuntos das seis loterias antes do lançamento. RPO/RTO são objetivos de 24h/4h, não capacidade já demonstrada.

O dump e o manifesto de objetos precisam refletir **o mesmo corte consistente do banco**. Usar conexão de backup apropriada para snapshot exportado: manter a transação exportadora enquanto `pg_dump --snapshot` e a leitura do manifesto utilizam esse corte, fechando-a depois dessas leituras, antes da transferência dos objetos. Copiar somente objetos imutáveis necessários ao corte, validar hash/tamanho e dependências de schema/extensões/papéis a recriar. [Snapshot sincronizado do PostgreSQL](https://www.postgresql.org/docs/17/app-pgdump.html). Não considerar um dump parcial de schema autossuficiente nem copiar todos os arquivos de um instante diferente como se fossem a mesma fotografia.

Identificar backup com versão do schema/código, corte, hashes do dump/manifesto e inventário de objetos. Promover estado `complete` somente após todos os objetos requeridos estarem presentes/verificados e o pacote cifrado ter sido confirmado no destino independente. Falha mantém `incomplete`, alerta e preserva o último backup completo; retenção nunca remove a única cópia completa antes de confirmar a substituta. Chaves de decifragem são verificadas na restauração, sem incluir seus valores no pacote.

## Operação

Runbooks mínimos antes da produção:

- fonte indisponível;
- formato externo alterado;
- concurso atrasado ou corrigido;
- fila parada;
- migração com falha;
- comprometimento de credencial;
- restauração de banco;
- rollback de release.

## Custos e escala

Começar com serviços gerenciados pequenos e escalonamento vertical. Avaliar otimização por métricas:

- custo por ambiente e por job;
- armazenamento raw e retenção;
- tempo e memória de normalização;
- consultas mais caras;
- duração de experimentos;
- tráfego e cache hit rate.

Redis, broker dedicado, GPU permanente e cluster distribuído ficam adiados. Experimentos pesados podem usar execução efêmera sem alterar a arquitetura do produto.

O [Free Supabase](https://supabase.com/pricing) informa 500 MB de banco, 1 GB de arquivos e até dois projetos ativos, com pausa após inatividade. [GitHub Free](https://docs.github.com/en/billing/reference/product-usage-included) informa 2.000 minutos/mês e 500 MB de artefatos, compartilhados com CI/backup. Um dispatcher horário gera cerca de 720 disparos em 30 dias, mesmo sem trabalho; custo real depende de duração e arredondamento. Medir antes de ativar e reservar franquia para CI/restauração. Retenção de sete backups exige dimensionar tamanho comprimido; não pressupor que sete cópias de um banco de 500 MB cabem na cota.

Alertar em 80% das cotas e impedir cobrança por excedente nas configurações dos serviços; a conta precisa comprovar bloqueio de gasto antes de ativar jobs. Se a franquia não comportar o perfil horário, reduzir o dispatcher para reconciliação diária, mantendo a meta D+1 e sinalizando `daily` na interface. Essa alternativa foi autorizada pela preferência do usuário por uma hora **ou** um dia. Não excluir silenciosamente evidências para caber; pausar novas cargas/treinos, preservar o mínimo recuperável e reportar limitação. Nenhum trial pago, domínio comprado ou assinatura é criado por esta arquitetura.
