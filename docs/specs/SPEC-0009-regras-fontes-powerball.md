# SPEC-0009 — Regras históricas e fontes da Powerball

## Estado

Concluída em 2026-10-14.

## Objetivo

Substituir o envelope provisório da SPEC-0008 por uma especificação pesquisada das versões históricas da Powerball e decidir a hierarquia de fontes que deverá orientar a futura coleta e auditoria integral.

Esta é uma tarefa de pesquisa e documentação. Não altera normalizador, dados brutos, relatórios históricos, banco, agendamento ou interface.

## Critérios definidos

- Preferir MUSL/Powerball e loterias estaduais oficiais; usar fonte secundária somente para completar ou reconciliar fronteiras não publicadas de forma acessível nas fontes primárias.
- Registrar vigência por data de sorteio, não por anúncio ou início de vendas.
- Distinguir matriz numérica, Power Play, Double Play e calendário: são dimensões independentes.
- Atribuir nível de confiança e evidência a cada fronteira.
- Separar fonte automatizada preferencial de autoridade para verificação.
- Não tratar feed, página ou arquivo parcial como histórico oficial completo sem uma prova de cobertura.
- Deixar pendências explícitas para a implementação seguinte, sem inventar identificador de concurso.

## Decisões

### Matrizes versionadas

O domínio deverá admitir sete versões por data do sorteio:

| Versão | Vigência inclusiva | Principais | Powerball | Confiança |
| --- | --- | --- | --- | --- |
| `pb_1992_45x45` | 1992-04-22 a 1997-11-01 | 5 de 1–45 | 1 de 1–45 | média |
| `pb_1997_49x42` | 1997-11-05 a 2002-10-05 | 5 de 1–49 | 1 de 1–42 | alta |
| `pb_2002_53x42` | 2002-10-09 a 2005-08-27 | 5 de 1–53 | 1 de 1–42 | alta |
| `pb_2005_55x42` | 2005-08-31 a 2009-01-03 | 5 de 1–55 | 1 de 1–42 | alta |
| `pb_2009_59x39` | 2009-01-07 a 2012-01-14 | 5 de 1–59 | 1 de 1–39 | alta |
| `pb_2012_59x35` | 2012-01-18 a 2015-10-03 | 5 de 1–59 | 1 de 1–35 | alta |
| `pb_2015_69x26` | desde 2015-10-07 | 5 de 1–69 | 1 de 1–26 | alta |

As lacunas entre versões são dias sem sorteio, não intervalos desconhecidos. Os limites exatos por sorteio coincidem com o snapshot secundário existente; fontes oficiais sustentam a matriz e a mudança correspondente, conforme o dossiê de evidências.

### Recursos independentes

- Power Play: primeiro sorteio em 2001-03-07. O multiplicador sorteado aparece no período antigo, deixa de aparecer entre 2012-01-18 e 2014-01-18 porque os prêmios eram fixos, e retorna em 2014-01-22. Ausência nesse intervalo não é dado perdido.
- Double Play: série adicional iniciada em 2021-08-23, separada do resultado principal.
- Calendário: quarta e sábado historicamente; segunda-feira adicionada em 2021-08-23. O calendário não deve ser inferido da matriz.
- Moeda: USD. Jackpot divulgado é valor anunciado; não equivale a pagamento, arrecadação ou valor em dinheiro.

### Hierarquia de fontes

1. **Verificação autoritativa:** resultado individual em `powerball.com`, que declara que o resultado oficial é o registrado no sorteio sob observação independente.
2. **Coleta automatizada preferencial:** API estruturada da MUSL, condicionada a chave, aceitação dos termos e uma prova técnica de cobertura histórica. Ela oferece números, regras, ordem, identificadores e relatórios, mas seus próprios termos dizem que o feed não representa a informação oficial.
3. **Reconciliação oficial parcial:** arquivos e páginas de loterias estaduais. O CSV do Texas é estruturado, porém começa em 2010 e possui mudanças de colunas; não cobre a história completa.
4. **Fallback secundário:** USA Mega, inclusive o HTML local. Serve para continuidade e comparação, nunca para prevalecer sobre uma divergência oficial.

O sistema deverá guardar `source`, instante de coleta, URL/endpoint, identidade externa quando fornecida e, futuramente, hash do payload. Divergências não serão corrigidas silenciosamente.

## Fora do escopo executado

- Nenhuma chamada à API, cadastro de chave ou coleta em massa.
- Nenhuma alteração em `app/`, `tests/`, dependências ou dados brutos.
- Nenhuma auditoria integral das 3.742 linhas.
- Nenhuma implementação das versões no normalizador.
- Nenhuma decisão sobre retenção/licenciamento além do registro das condições que precisam ser validadas.

## Evidências e riscos

O [dossiê de regras e fontes](../data/powerball-regras-fontes.md) contém URLs, justificativas, confiança e lacunas. A versão inicial 45×45 permanece com confiança média: início oficial e fronteira do snapshot são confirmados, mas ainda não foi localizada nesta pesquisa uma regra primária histórica acessível que explicite ambos os intervalos.

A API pode mudar, limitar ou revogar acesso e exige chave. Antes de promovê-la a coletor de produção é obrigatório testar autenticação, paginação, limites, cobertura desde 1992, correções, estabilidade de identificadores, licenças de armazenamento/exibição e comportamento para data sem sorteio.

## Critérios de aceitação verificados

- Sete matrizes, vigências, limites e confiança documentados.
- Power Play, Double Play e calendário separados da matriz.
- Fontes oficiais e secundária classificadas por finalidade.
- Uma fonte preferencial de automação e uma autoridade de verificação definidas.
- Riscos da API, dúvidas e evidências incompletas registrados.
- Nenhum código, teste, dependência, dado bruto ou relatório anterior modificado por esta SPEC.

## Próxima tarefa recomendada

**SPEC-0010 — Implementar regras históricas versionadas e auditar integralmente o snapshot Powerball.**

Justificativa: as fronteiras necessárias agora estão explícitas. A próxima redução de risco é substituir o envelope provisório, validar as 3.742 linhas pela regra vigente em cada data e produzir diagnóstico reproduzível; integração de API deve esperar esse baseline local e uma SPEC própria de prova técnica da fonte.
