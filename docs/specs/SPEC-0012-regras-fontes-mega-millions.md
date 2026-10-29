# SPEC-0012 — Regras históricas e fontes da Mega Millions

## Estado

Concluída em 2026-10-14.

## Objetivo

Substituir o envelope provisório da SPEC-0011 por uma especificação pesquisada das matrizes históricas, da evolução Big Game/Mega Millions, do Megaplier e da fonte preferencial para futura coleta e auditoria.

Esta é uma tarefa de pesquisa e documentação. Não altera normalizador, testes, dados brutos, banco, coleta ou interface.

## Critérios definidos

- Preferir Mega Millions, loterias estaduais e regulamentos oficiais.
- Registrar vigência por data de sorteio, distinguindo anúncio, início de vendas e desenho.
- Separar matriz numérica, nome comercial, calendário e mecanismo multiplicador.
- Classificar evidência/confiança e não elevar a certeza de fonte secundária por concordar com o raw da mesma origem.
- Definir autoridade de verificação e fonte preferencial de automação separadamente.
- Registrar lacunas técnicas e jurídicas antes de qualquer coletor.

## Matrizes versionadas

| Versão | Vigência inclusiva | Principais | Mega Ball | Confiança |
| --- | --- | --- | --- | --- |
| `mm_1996_50x25` | 1996-09-06 a 1999-01-12 | 5 de 1–50 | 1 de 1–25 | alta |
| `mm_1999_50x36` | 1999-01-15 a 2002-05-14 | 5 de 1–50 | 1 de 1–36 | média |
| `mm_2002_52x52` | 2002-05-17 a 2005-06-21 | 5 de 1–52 | 1 de 1–52 | alta |
| `mm_2005_56x46` | 2005-06-24 a 2013-10-18 | 5 de 1–56 | 1 de 1–46 | alta |
| `mm_2013_75x15` | 2013-10-22 a 2017-10-27 | 5 de 1–75 | 1 de 1–15 | alta |
| `mm_2017_70x25` | 2017-10-31 a 2025-04-04 | 5 de 1–70 | 1 de 1–25 | alta |
| `mm_2025_70x24` | desde 2025-04-08 | 5 de 1–70 | 1 de 1–24 | alta |

As lacunas são dias sem sorteio. A fronteira de 1999 permanece com confiança média porque a pesquisa encontrou a matriz e as datas exatas em fonte secundária, mas ainda não localizou um regulamento primário acessível que documente a mudança para 36 Mega Balls.

## Dimensões independentes

- **Nome:** The Big Game desde 1996; Mega Millions a partir de maio de 2002. A troca de nome acompanha expansão do consórcio, mas não deve ser usada como identidade de uma loteria nova.
- **Calendário:** inicialmente sexta-feira; terça-feira adicionada em fevereiro de 1998. Calendário não determina matriz.
- **Megaplier sorteado:** introduzido pelo Texas em dezembro de 2003 e posteriormente disponibilizado em outras jurisdições. É uma opção de aposta e o número sorteado pode ser atributo do resultado.
- **Multiplicador incorporado:** desde o sorteio de 2025-04-08, cada aposta de US$5 recebe 2x, 3x, 4x, 5x ou 10x. Não existe um único multiplicador do sorteio.
- **Preço:** US$1 até 2017; US$2 na versão iniciada em 2017; US$5 desde abril de 2025. Preço não é prêmio nem atributo do resultado.

## Hierarquia de fontes

1. **Autoridade de verificação:** arquivo de resultados em `megamillions.com` e, quando necessário, a loteria oficial da jurisdição.
2. **Coleta automatizada preferencial:** arquivo oficial central de desenhos anteriores, condicionado a prova técnica de paginação, cobertura desde 1996, estabilidade e política de uso.
3. **Fonte estruturada oficial parcial:** CSV da Texas Lottery desde 2003. É ideal para reconciliação, mas não cobre 1996–2003 e muda de schema em 2025.
4. **Regulamentos/comunicados estaduais:** autoridade para regras, matrizes e mudanças; não são um feed de resultados.
5. **Fallback secundário:** USA Mega e o HTML local, somente para continuidade e comparação.

## Resultado

As sete versões e três estados do multiplicador estão especificados para a próxima implementação. O dossiê registra evidências, confiança, fonte e pendências.

Nenhum código, teste, dependência, relatório histórico ou dado bruto foi alterado por esta SPEC.

## Riscos e pendências

- Provar que o arquivo central aceita extração histórica completa e estável, sem depender de JavaScript ou parâmetros opacos.
- Descobrir se existe API oficial/documentada e quais são seus termos.
- Confirmar fonte primária da matriz 50/36 e fronteiras de 1999.
- Determinar identificadores externos estáveis; não inventar número de concurso.
- Definir reconciliação de resultados nacionais versus prêmios/ganhadores estaduais.
- Versionar faixas, preços, Megaplier e multiplicador incorporado antes de análises financeiras.

## Próxima tarefa recomendada

**SPEC-0013 — Implementar as sete matrizes e auditar integralmente o snapshot Mega Millions.**

Justificativa: as regras numéricas e os estados do multiplicador estão definidos. A próxima redução de risco é substituir o envelope provisório, validar as 2.984 linhas por vigência e produzir diagnóstico reproduzível antes de integrar qualquer fonte de rede.
