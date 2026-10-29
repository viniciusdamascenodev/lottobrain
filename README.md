# LottoBrain

Um sistema completo para análise e tentativa de previsão de loterias nacionais e internacionais usando ciência de dados e inteligência artificial.


# Aviso Legal

Este projeto tem finalidade exclusivamente analítica, voltada à exploração de técnicas de ciência de dados, estatística e aprendizado de máquina aplicadas a dados públicos de loterias.

Em hipótese alguma este repositório deve ser interpretado como incentivo, recomendação ou aconselhamento para participação em jogos de azar ou apostas.

Os dados e modelos aqui desenvolvidos não garantem nenhum tipo de acerto ou ganho financeiro, sendo baseados em eventos aleatórios e imprevisíveis.

O autor não se responsabiliza por quaisquer decisões tomadas com base nas informações ou resultados gerados por este projeto.

A prática de jogos de azar deve ser feita com consciência e responsabilidade, respeitando a legislação vigente de seu país.

Ao utilizar este repositório, você concorda que o faz por conta própria e risco.


## Loterias analizadas

- Mega-Sena BR
- +Milionária BR
- Lotofácil BR
- Powerball US
- Mega Millions US
- Euro Millions EU

## Desenvolvimento e documentação

- [Etapa 5 — ambiente, dependências, testes e GitHub Actions](docs/engineering/etapa-5-desenvolvimento-ci.md). Use os lockfiles e comandos dessa referência para a plataforma nova; o Flask/configuração Vercel antigos continuam legados.
- [Etapa 4 — experiência visual e jornadas](docs/design/etapa-4-experiencia-visual.md), [protótipo navegável](docs/design/prototipo/index.html), [como explorar](docs/design/prototipo/README.md) e [validação](docs/design/validacao-etapa-4.md). Protótipo local para as seis loterias e administração; login e operações são demonstrativos.
- [Mapa de evolução e gates de qualidade](docs/architecture/roadmap.md).
- [Etapa 3 concluída: arquitetura privada para as seis loterias](docs/architecture/visao-geral.md).
- [Contratos de API, frontend e fluxos do produto](docs/architecture/contratos-produto.md).
- [Plano de entrega em quatro dias](docs/engineering/plano-entrega-quatro-dias.md).
- [Etapa 2 encerrada: fontes escolhidas e contrato oficial EuroMillions — decisão vigente](docs/data/encerramento-etapa-2.md).
- [Verificação técnica atual das seis fontes em 27/10/2026](docs/data/verificacao-fontes-atuais-2026-10-27.md).
- [Fechamento da etapa 2: campos, continuidade recente, calendários e condições das fontes](docs/data/fechamento-etapa-2.md).
- [Reanálise da etapa 2: links conferidos e alternativas oficiais para completar os dados](docs/data/reanalise-etapa-2-atualizacao-completa.md).
- [Qualificação final da etapa 2: transporte, Double Play, financeiros e restrições reais de uso](docs/data/qualificacao-final-etapa-2.md).
- [SPEC-0033 — plataforma privada e consulta das seis, planejada](docs/specs/SPEC-0033-primeiro-fluxo-online-mega-sena.md).
- [SPEC-0034 — seis loterias atualizadas e agendamento, planejada](docs/specs/SPEC-0034-seis-loterias-atualizadas-e-agendamento.md).
- [SPEC-0035 — painel, previsões e catálogo, planejada](docs/specs/SPEC-0035-painel-analitico-previsoes-e-catalogo.md).
- [SPEC-0036 — validação operacional e publicação, planejada](docs/specs/SPEC-0036-validacao-operacional-e-publicacao.md).
- [SPEC-0024 — primeiras migrations PostgreSQL](docs/specs/SPEC-0024-migrations-integridade.md).
- [SPEC-0025 — persistência transacional Mega-Sena](docs/specs/SPEC-0025-persistencia-transacional-mega-sena.md).
- [SPEC-0026 — qualificação dos seis históricos](docs/specs/SPEC-0026-qualificacao-importacao-historica.md).
- [SPEC-0027 — piloto histórico Mega-Sena](docs/specs/SPEC-0027-piloto-importacao-mega-sena.md).
- [SPEC-0028 — ponte no fluxo incremental](docs/specs/SPEC-0028-ponte-ingestao-incremental.md).
- [SPEC-0029 — importação completa Mega-Sena](docs/specs/SPEC-0029-importacao-completa-mega-sena.md).
- [SPEC-0030 — baseline auditada e início seguro](docs/specs/SPEC-0030-baseline-auditada-sincronizacao-mega-sena.md).
- [SPEC-0031 — sincronização PostgreSQL limitada](docs/specs/SPEC-0031-orquestracao-sql-sincronizacao-mega-sena.md).
- [SPEC-0032 — auditoria somente leitura da sincronização SQL](docs/specs/SPEC-0032-auditoria-sincronizacao-sql-mega-sena.md).
- [Uso e limites da auditoria PostgreSQL](docs/engineering/auditoria-sincronizacao-sql-mega-sena.md).
- [Evidência da auditoria SQL — SPEC-0032](docs/data/mega-sena-auditoria-sql-spec-0032.json).
- [Lotes, operações e garantias SQL](docs/database/lotes-sincronizacao.md).
- [Operação, limites e recuperação da sincronização SQL](docs/engineering/sincronizacao-sql-mega-sena.md).
- [Evidência da sincronização SQL — SPEC-0031](docs/data/mega-sena-sincronizacao-sql-spec-0031.json).
- [Baseline, vínculo entre fontes e privilégios](docs/database/baseline-auditada.md).
- [Aprovação, checkpoint e reprodução dos testes](docs/engineering/baseline-sincronizacao-mega-sena.md).
- [Carga, retomada e auditoria de cobertura](docs/engineering/importacao-completa-mega-sena.md).
- [Evidência da cobertura histórica Mega-Sena — SPEC-0029](docs/data/mega-sena-cobertura-spec-0029.json).
- [Política incremental, compatibilidade e continuidade](docs/engineering/ponte-ingestao-incremental.md).
- [Ponte XLSX/JSON, evidências e retomada do piloto](docs/engineering/piloto-importacao-mega-sena.md).
- [Mapeamentos, evidências e plano de importação histórica](docs/data/qualificacao-importacao-historica.md).
- [Preparação do ambiente e testes de integridade](docs/database/migrations-ingestao.md).
- [Uso e recuperação do fluxo PostgreSQL opt-in](docs/engineering/persistencia-mega-sena.md).

A estrutura PostgreSQL e o fluxo de escrita transacional foram validados em testes isolados. O fluxo em arquivos foi preservado; SQL é opcional, sem banco operacional provisionado.

Os 15.471 registros dos seis históricos foram qualificados em memória, com 20 versões de regras e 45 vetores reais fixos. A SPEC-0029 comprovou também a importação completa e auditada dos 2.954 concursos Mega-Sena disponíveis (até 20/12/2025), com interrupção/retomada, replay e preservação do JSON mais completo.

A SPEC-0030 comprovou a baseline histórica loaded e o checkpoint JSON, preservando a proveniência XLSX. A SPEC-0031 adicionou sincronização limitada e retomável; a SPEC-0032 entregou sua auditoria somente leitura, com verificação de operações, continuidade e bytes, sem reparo automático. Na SPEC-0032 passaram 292 testes comuns e 19 do recorte da auditoria (13 PostgreSQL reais e seis dublês); os 79 arquivos anteriores protegidos permaneceram intactos. As provas ocorreram em bancos descartáveis, com clusters desligados, sem coleta externa, banco operacional ou sincronização automática.

O roteiro reorganizado em 26/10/2026 mantém a meta original de 30/10 e quatro entregas funcionais. Na consolidação arquitetural de 27/10, a primeira foi ampliada para plataforma privada e consulta real das seis loterias; seguem atualização/agendamento, painel/previsões/catálogo e validação/publicação. Conteúdo privado, aprovação do proprietário, atualização +1h/D+1 (modo diário aceito por cota/fonte) e custo inicial zero são as decisões vigentes. As SPECs 0033–0036 continuam somente planejadas, sem serviços provisionados; ampliar a primeira entrega aumenta o risco do prazo. A arquitetura escolhe Vercel, Supabase e Actions, com Google/Supabase Auth; implantação e qualidade operacional ainda precisam ser comprovadas. O arquivo da SPEC-0033 conserva seu nome antigo para preservar referências.

A verificação de fontes em 27/10 qualificou por amostra o resultado principal atual das seis loterias, com 62 verificações e 20 testes offline, aproveitando os históricos existentes. Não atualizou a base operacional nem ativou coleta recorrente. As fontes observadas e condições pendentes estão no relatório específico; a atividade inicial de fontes da SPEC-0033 já aproveita essa evidência.

O complemento de fechamento da etapa 2 conferiu continuidade de 756 registros posteriores aos arquivos originais, esclareceu calendários excepcionais e classificou campos financeiros e condições de uso. O host oficial configurado CAIXA agora observado é `servicebus3`; o novo campo JSON exige atualização deliberada do contrato. Passaram 43 testes offline das duas verificações. A descoberta está concluída, sem importação operacional, liberação irrestrita dos fornecedores ou ativação de agendamento. As SPECs 0033/0034 recebem os pontos concretos de integração e liberação, sem repetir o inventário.
