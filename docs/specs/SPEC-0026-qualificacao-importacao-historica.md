# SPEC-0026 — Qualificação da importação histórica

## Estado

Concluída em 21/10/2026 (America/Sao_Paulo). Critérios registrados antes da implementação.

## Objetivo e recorte

Qualificar a representação relacional dos seis históricos existentes antes de escrever um importador. Reutilizar leitores e normalizadores aprovados; realizar apenas leitura e transformação em memória. O contrato Mega-Sena JSON v1 da SPEC-0025 permanece intacto.

Não carregar históricos em SQL, provisionar banco operacional, modificar dados brutos/relatórios anteriores, coletar na rede, implementar publicação, agendamento, API, interface ou autenticação. Uma representação qualificada não significa importação realizada nem catálogo operacional aprovado.

## Critérios de aceitação

1. Mapear Mega-Sena XLSX, Lotofácil, +Milionária, Powerball, Mega Millions e EuroMillions, preservando as 20 versões de regras existentes.
2. Separar identidade oficial/provisória, referências privadas e evidência da fonte; não fabricar sequência, horário, ordem de extração, país, moeda ou ganhadores.
3. Preservar séries adicionais, atributos tipados, trevos, estrelas, multiplicadores históricos e estados financeiros; rejeitar representações inválidas para o envelope SQL.
4. Definir serialização/hash versionados e vetores reais fixos localizáveis nos arquivos, cobrindo início/fim de cada regra e ausência financeira EuroMillions. Testar estabilidade e mutações negativas explícitas.
5. Comparar o concurso Mega-Sena 2954 entre XLSX e JSON: fatos compartilhados, diferenças, ausências e enriquecimentos; não exigir igualdade de hashes entre contratos diferentes nem fundir automaticamente fontes.
6. Executar qualificação offline de todos os registros, contar representáveis/rejeitados/identidades duplicadas e produzir relatório reproduzível com hashes raw antes/depois, cobertura por regra e hash agregado dos mapeamentos.
7. Documentar correspondência com tabelas SQL, lacunas/bloqueios e plano de importação auditada e retomável, sem implementar sua escrita nesta SPEC.
8. Manter suíte comum, vetor Mega-Sena JSON v1, auditoria anterior e todos os arquivos protegidos inalterados. Testes desta etapa não serão anunciados como prova de importação/roundtrip PostgreSQL das seis fontes.
9. Atualizar aprendizados e posição no roadmap; indicar uma única próxima tarefa com justificativa.

## Estratégia de verificação

Mapper puro e restrito a perfis conhecidos, executado pelos mesmos normalizadores em uso. Vetores com conteúdo esperado e SHA-256 em fixture versionada; relatório completo gerado somente em stdout, sem escritor de arquivos de dados. Testes distinguem conteúdo de evidência, comparações entre fontes e limites da qualificação. Manter separado o futuro teste de roundtrip SQL/importador.

## Entregas e comprovação

- Mapper histórico puro com sete perfis explícitos: seis fontes históricas e JSON Mega-Sena apenas para comparação. Sem alteração do writer/contrato JSON v1, migrations ou normalizadores anteriores.
- Auditoria offline reproduzível em stdout, sem escrita de dados, SQL ou rede. **15.471/15.471 registros representáveis**, zero rejeições, zero identidades/referências duplicadas por histórico; 20 regras.
- **45 vetores reais fixos**, com entrada localizável, conteúdo/evidência e hashes independentes. Cobertura de fronteiras, multiplicadores, acumulação e ausência financeira EuroMillions.
- Comparação real Mega-Sena 2954: 12 grupos compartilhados iguais, cinco exclusivos do JSON, nenhuma divergência compartilhada. Hash JSON v1 original preservado.
- [Relatório e contrato detalhados](../data/qualificacao-importacao-historica.md) e [evidência JSON](../data/qualificacao-importacao-spec-0026.json), incluindo correspondência relacional, bloqueios e plano de importação.
- **244 testes aprovados**: 181 comuns (24 novos, 60,90 s) e 63 da regressão isolada (106,701 s: 58 PostgreSQL reais + cinco de UoW simulado). Os testes SQL são regressão existente, não certificação SQL do novo mapper histórico.
- Hashes dos 30 arquivos protegidos conferidos antes/depois, sem diferenças: raw, relatórios JSON anteriores e workspace local de coleta. Auditoria Mega-Sena anterior reproduzida exatamente, estado healthy.
- Compileall, links locais dos documentos afetados e verificação de whitespace aprovados. Aviso CRLF em requirements.txt é preexistente; arquivo não editado nesta tarefa.
- PostgreSQL descartável encerrado, sem postmaster.pid e com shutdown confirmado no log `.local-postgres/runs/d5a4156451fc414bba6e9e3a17e2a3f3/server.log`. Serviços PostgreSQL 12/13 existentes permaneceram Running e não foram alterados.
- Aprendizados L-139…L-144 e roadmap atualizados; nenhuma dependência, banco operacional, importação integral ou publicação criados.

## Descobertas e limites controlados

O mesmo schema suporta as diferenças, mas o writer existente deliberadamente recusa contratos de canonicalização incompatíveis. Antes da carga, precisa ser provada uma ponte XLSX/JSON que não apague enriquecimento nem altere revisões seladas. A evidência de observações sem nova revisão também exige implementação/teste no piloto, não atualização de filhos imutáveis.

A primeira passagem de vetores via terminal Windows alterou acentos no transporte. O teste de reprodução detectou; os vetores foram regenerados preservando Unicode e a CLI ganhou saída JSON escapada e teste dedicado. Dados brutos e hashes canônicos não foram alterados para contornar esse problema.

Representabilidade não comprova cobertura completa oficial, semântica econômica de zeros antigos ou atualização além do recorte. Nenhum parser definitivo adicional, importador operacional, política de merge genérico ou roundtrip histórico SQL foi entregue nesta tarefa.

## Única próxima tarefa recomendada

**SPEC-0027 — Importação histórica piloto da Mega-Sena, com reconciliação XLSX/JSON e retomada.**

Justificativa: provar ponte de contratos, evidência por observação, roundtrip e recuperação em poucas linhas reais num banco descartável antes de qualquer carga integral ou expansão para outras modalidades. Não executada nesta SPEC.
