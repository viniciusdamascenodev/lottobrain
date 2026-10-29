# SPEC-0001 — Inventário e diagnóstico dos dados existentes

## Estado

Concluída em 2026-09-01.

## Objetivo

Estabelecer uma linha de base verificável dos dados históricos já presentes no LottoBrain, antes de projetar persistência, coleta incremental, análises ou cadastro de novas loterias.

## Escopo

Foram inspecionados, somente para leitura, os seis arquivos em `data/raw/` correspondentes a Mega-Sena, Lotofácil, +Milionária, Powerball, Mega Millions e EuroMillions.

Não fazem parte desta especificação:

- correção do pipeline atual;
- normalização ou importação definitiva;
- banco de dados;
- download de dados novos;
- interface, autenticação ou agendamento;
- estatísticas e modelos preditivos;
- desenho completo do cadastro de novas loterias.

## Método

1. Registro de tamanho e SHA-256 de cada arquivo bruto.
2. Leitura das três planilhas, preservando células e tipos originais.
3. Leitura estrutural do JSON do EuroMillions.
4. Inspeção das linhas, células e elementos de bolas dos dois HTMLs.
5. Verificações de quantidade, período, campos, duplicidade, ausência, validade de datas, repetição dentro do sorteio e limites aparentes.
6. Comparação das descobertas com as configurações existentes em `app/core/config.py`.

As verificações de limites usaram as regras aparentes conhecidas pelo projeto. Nas séries americanas, números fora dos limites **atuais** foram classificados como evidência de mudança histórica de regras, e não automaticamente como erro.

## Resultado executivo

| Loteria | Registros | Período | Núcleo do sorteio | Qualidade preliminar |
|---|---:|---|---|---|
| Mega-Sena | 2.954 | 1996-03-11 a 2025-12-20 | 6 números | Alta para resultados; média para metadados |
| Lotofácil | 3.571 | 2003-09-29 a 2025-12-24 | 15 números | Alta para resultados; média para metadados |
| +Milionária | 314 | 2022-05-28 a 2025-12-24 | 6 números + 2 trevos | Alta para resultados; média para metadados |
| Powerball | 3.742 | 1992-04-22 a 2025-12-24 | 5 números + Powerball | Média; HTML e regras históricas exigem cuidado |
| Mega Millions | 2.984 | 1996-09-06 a 2025-12-23 | 5 números + Mega Ball | Média; HTML e regras históricas exigem cuidado |
| EuroMillions | 1.906 | 2004-02-13 a 2025-12-26 | 5 números + 2 estrelas | Alta estrutural; origem e semântica precisam confirmação |

Os conjuntos somam 15.471 registros de sorteios. Nenhum deles alcança 2026; portanto, são adequados como carga histórica inicial, mas estão desatualizados em relação à data desta auditoria.

## Constatações que afetam loterias futuras

O futuro cadastro não poderá presumir uma estrutura única. Os dados demonstram diferenças em:

- quantidade de números principais: 5, 6 ou 15;
- presença de 1 ou 2 elementos especiais;
- nomes e semânticas distintas: Powerball, Mega Ball, estrelas e trevos;
- intervalos que mudam ao longo do tempo;
- sorteios complementares, como Double Play;
- multiplicadores opcionais, como Power Play e Megaplier;
- frequências e dias de sorteio diferentes;
- moedas e formatos monetários diferentes;
- identificadores de concursos consistentes, ausentes ou com semântica não documentada;
- fontes XLSX, JSON e HTML;
- profundidade desigual de prêmio, ganhadores e arrecadação.

Essas diferenças deverão orientar a próxima especificação, mas não foi projetada aqui a funcionalidade de cadastro.

## Critérios de aceitação verificados

- [x] As seis loterias foram analisadas.
- [x] Quantidades e períodos foram documentados.
- [x] Problemas de qualidade possuem contagens ou exemplos verificáveis.
- [x] Campos presentes e ausentes foram separados.
- [x] Diferenças relevantes entre loterias foram registradas.
- [x] Arquivos brutos permaneceram inalterados, verificados por SHA-256.
- [x] Nenhuma funcionalidade fora do escopo foi implementada.
- [x] Uma única próxima tarefa foi recomendada.

## Questões que exigem pesquisa externa

1. Confirmar se os arquivos da Caixa representam exportações oficiais completas e documentar termos de uso e estabilidade dos endpoints.
2. Confirmar a fonte oficial preferencial para Powerball e Mega Millions; os HTMLs atuais vieram do USA Mega, uma fonte secundária.
3. Levantar todas as versões históricas das regras de Powerball, Mega Millions e EuroMillions.
4. Confirmar a semântica de `id` e `draw_id`, a moeda e o significado exato de `prize` na API usada para EuroMillions.
5. Verificar se há APIs ou downloads oficiais com faixas de premiação, ganhadores, arrecadação e identificador do concurso para as loterias internacionais.
6. Confirmar se sorteios em dias incomuns nas séries brasileiras correspondem a calendários especiais ou exceções.
7. Determinar timezone e horário oficial de publicação de cada resultado.

## Próxima tarefa recomendada

**SPEC-0002 — Modelo canônico versionado para loterias e concursos.**

Ela deve definir, sem ainda implementar toda a coleta, como representar loteria, versão histórica de regra, concurso, números principais, elementos especiais, prêmio, faixas, fonte e metadados de ingestão. Essa é a próxima tarefa porque os dados comprovam que uma estrutura fixa de seis números é insuficiente e que regras atuais não validam corretamente todo o histórico.

