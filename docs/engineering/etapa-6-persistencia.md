# Etapa 6 — Persistência das seis loterias

## Especificação e fronteira

Recorte de persistência da SPEC-0033, autorizado após o encerramento da etapa 5.
Reutilizar modelo, catálogo, normalizadores, contratos históricos e transações existentes.
Não executar carga histórica integral, coleta de rede, autenticação, interface, agendamento ou análises.

O PostgreSQL armazenará as seis modalidades no mesmo modelo relacional.
Perfis explícitos preservam identidades, versões de regras, componentes, atributos,
valores monetários, ausências e referências externas de cada fonte.
As revisões antigas e o caminho Mega-Sena existente permanecem compatíveis.

## Aceite

| ID | Evidência necessária |
|---|---|
| E6-01 | Bootstrap operacional idempotente das seis loterias e regras, sem importar helpers de teste |
| E6-02 | Gravação/leitura SQL de amostras reais das seis, incluindo fronteiras históricas e atributos |
| E6-03 | Proveniência verificável, replay idempotente, conflito em quarentena, revisão controlada e rollback |
| E6-04 | Conjuntos aprovados imutáveis, manifesto verificável, aprovação explícita, troca concorrente protegida e leitura paginada estável |
| E6-05 | Papéis distintos de ingestão, aprovação e leitura; consulta comum sem acesso a candidatos/raw; publicação individual continua bloqueada |
| E6-06 | Migrations forward, regressão anterior e novos testes PostgreSQL reais aprovados no CI |
| E6-07 | Procedimento executado em banco persistente do Supabase com configuração segura e evidência sanitizada |
| E6-08 | Contratos, operação, evidências e aprendizados atualizados; dados e evidências anteriores preservados |

## Plano de implementação

1. Bootstrap e qualificação do catálogo a partir das definições existentes.
2. Persistência comum de resultados qualificados, reutilizando conteúdo relacional e armazenamento raw.
3. Migration de conjuntos aprovados e papéis mínimos para consulta e aprovação.
4. Comandos administrativos limitados para preparar catálogo, persistir uma amostra e consultar/aprovar conjuntos.
5. Testes reais, validação de preservação e evidências de implantação controlada.

## Dependência externa

O usuário informou que ainda não criou o projeto Supabase.
A implementação e a prova em PostgreSQL isolado podem avançar; E6-07 exige projeto
persistente disponibilizado por canal seguro. Não confundir cluster descartável ou
configuração documentada com implantação executada.

## Estado

Implementação, validação local e regressão completa no GitHub executadas. A instalação
Supabase tem aceite separado. A etapa permanece em execução enquanto E6-07 estiver pendente.
Não iniciar a etapa 7 para contornar essa pendência.

## Entrega implementada

- Bootstrap idempotente do catálogo, com seis loterias, 20 regras e fontes históricas/atuais separadas.
- Uma transação por resultado, reutilizando escritor de conteúdo, finanças, leitor, raw e ledger existentes.
- Identidade oficial nas brasileiras e provisória nos históricos internacionais, com referências externas preservadas.
- Correção candidata explícita, quarentena por padrão e compatibilidade com enriquecimento JSON Mega-Sena.
- Conjuntos aprovados imutáveis com manifesto versionado e verificado também no SQL.
- Reutilização de conjunto equivalente, decisão auditada, ativação otimista e paginação estável por UUID.
- Política fixando fontes, versões de regras e catálogo/perfis autorizados.
- CLI operacional limitada e papéis separados para catálogo, ingestão, aprovação e leitura.

[Contrato físico](../database/persistencia-seis-loterias.md),
[operação controlada](etapa-6-operacao.md) e
[evidência estruturada](etapa-6-evidencias.json).

## Validação e passagem

As provas locais abrangem 413 testes comuns e 25 testes PostgreSQL novos.
O recorte SQL usa 45 vetores reais já qualificados, cobrindo as 20 regras, e executa
bootstrap em banco vazio com papel restrito. Testa também a CLI, compatibilidade
Mega-Sena, concorrência, rollback, permissões e reutilização de manifestos.
As medições e o estado do CI são mantidos na evidência estruturada.

Não foi repetido o inventário nem feita carga histórica completa operacional. A regressão anterior de carga Mega-Sena continua executada somente em bancos descartáveis. A CLI aceita um
registro por chamada e até 100 revisões numa aprovação controlada; não é o importador
em lote da próxima etapa. O backend HTTP continua recusando os dados.

O próximo passo desta mesma tarefa é disponibilizar o projeto Supabase e executar o
procedimento já preparado, com acesso seguro, registrando versão, TLS, migrations,
permissões e leitura dos seis conjuntos por conexões novas. Um CI verde não substitui
essa evidência persistente.

## Regressão remota aprovada

A [PR #11](https://github.com/viniciusdamascenodev/lottobrain/pull/11) permanece em rascunho enquanto falta a prova persistente. O [CI 40975784677](https://github.com/viniciusdamascenodev/lottobrain/actions/runs/40975784677), no commit fe312cfd1d87c11dc53a61424a070255055d120d, aprovou os quatro jobs: 413 testes Python, 162 testes PostgreSQL (137 anteriores e 25 novos), frontend e Quality gate. Foram usadas somente credenciais temporárias dos testes. As auditorias do recorte ativo não reportaram vulnerabilidades conhecidas nesse run.

E6-01 a E6-06 estão comprovados na implementação; E6-08 registra a entrega e os limites. E6-07 permanece pendente porque o projeto Supabase e o acesso seguro ainda não foram disponibilizados. Não houve merge, instalação persistente, carga integral ou início da próxima etapa.
