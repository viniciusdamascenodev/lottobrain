# SPEC-0019 — Arquitetura de referência do LottoBrain

## Estado

Concluída em 2026-10-20.

Consolidação da **etapa 3 concluída em 27/10/2026**: privacidade integral, atualização +1h/D+1 e seis modalidades funcionais desde a primeira consulta. Referência vigente: [visão geral e aceite](../architecture/visao-geral.md), [contratos](../architecture/contratos-produto.md) e [ADR-0004](../architecture/decisions/ADR-0004-produto-privado-seis-loterias.md). Sem implementação, provisionamento ou alteração de migrations nesta consolidação. A próxima tarefa indicada ao final descreve a entrega original; a sequência vigente é 0033–0036.

## Objetivo

Definir uma arquitetura coerente para levar o LottoBrain da fundação de dados até um produto online seguro, observável e evolutivo, preservando simplicidade operacional e separação de responsabilidades.

## Escopo

- visão de contexto e contêineres;
- módulos e regras de dependência;
- fluxos críticos;
- estratégia de dados, backend, frontend, jobs e experimentos;
- segurança, observabilidade, testes, CI/CD e infraestrutura;
- requisitos não funcionais iniciais;
- tratamento explícito do código legado;
- decisões adotadas e adiadas.

## Fora do escopo

- implementar banco, API, frontend, autenticação, coletor ou infraestrutura;
- escolher provedor de nuvem definitivo;
- criar esquema físico ou componentes visuais;
- substituir código legado nesta tarefa.

## Decisões

1. **Monólito modular como arquitetura inicial.** Um repositório e uma aplicação backend, executados como processos de API e worker, com fronteiras internas rígidas.
2. **Frontend desacoplado por contrato HTTP.** Aplicação web TypeScript separada do backend, sem acesso direto ao banco.
3. **PostgreSQL como sistema de registro.** Objetos brutos permanecem imutáveis em armazenamento de artefatos; derivados analíticos não contaminam tabelas transacionais.
4. **Arquitetura em camadas por módulo.** Domínio não importa framework, ORM, rede ou UI.
5. **Jobs persistidos e idempotentes.** Agendamento dispara casos de uso; não contém regras de negócio.
6. **Previsões como experimentos reproduzíveis.** Promoção para produção depende de avaliação temporal e registro de linhagem.
7. **Segurança e observabilidade transversais.** Auditoria, métricas, logs estruturados e autorização entram nos casos de uso, não como remendos da interface.
8. **Evolução orientada por evidência.** Redis, filas externas, microsserviços, Kubernetes e lakehouse só entram diante de necessidade mensurada.

## Entregas

- [Visão geral](../architecture/visao-geral.md)
- [Módulos e fronteiras](../architecture/modulos-e-fronteiras.md)
- [Dados, análises e previsões](../architecture/dados-analises-previsoes.md)
- [Segurança e requisitos não funcionais](../architecture/seguranca-e-requisitos.md)
- [Entrega, infraestrutura e operações](../architecture/entrega-e-infraestrutura.md)
- [ADR-0001 — Monólito modular](../architecture/decisions/ADR-0001-monolito-modular.md)
- [ADR-0002 — Separação entre dados operacionais, raw e analíticos](../architecture/decisions/ADR-0002-camadas-de-dados.md)
- [Mapa de evolução](../architecture/roadmap.md)
- Aprendizados L-082 a L-090 em [learnings.md](../engineering/learnings.md)

## Critérios de aceitação verificados

- Componentes e responsabilidades estão definidos.
- Dependências permitidas e proibidas estão explícitas.
- Banco, backend, frontend, jobs, modelos e infraestrutura possuem direção arquitetural.
- Fluxos de coleta, consulta, administração e previsão estão descritos.
- Segurança, privacidade, auditoria, testes, observabilidade, backup e recuperação foram considerados.
- Código legado foi classificado sem remoção prematura.
- Complexidades adiadas estão documentadas.
- Nenhum arquivo bruto ou comportamento de produção foi alterado.

## Próxima tarefa recomendada

**SPEC-0020 — Qualificar a fonte e implementar a coleta incremental da Mega-Sena.**

Ela será o primeiro fluxo vertical sob a arquitetura: aquisição, artefato raw, normalização, idempotência, diagnóstico e contrato de persistência ainda substituível.
