# Normalização histórica da Mega-Sena

## Snapshot validado

Execução: 2026-09-15. Fonte: `data/raw/mega_sena/mega_sena_resultados.xlsx`, lida sem alterações.

| Verificação | Resultado |
|---|---|
| Linhas lidas / candidatos / válidos | 2.954 / 2.954 / 2.954 |
| Chaves únicas | 2.954 |
| Inválidos / identidades ausentes | 0 / 0 |
| Duplicidades / lacunas no intervalo | 0 / 0 |
| Concursos | 1–2954 |
| Datas | 1996-03-11 a 2025-12-20 |
| Valores principais | 17.724, entre 1 e 60 |
| Cidade/UF não informada | 2.331 |
| Observação não informada | 2.059 |
| Comparações com a SPEC-0001 | 8 de 8 coincidentes |
| Problemas de parsing/contrato | Nenhum neste snapshot |

## Financeiro

Cada campo abaixo contém 2.954 valores parseáveis em BRL, preservados como `Decimal`.

| Finalidade | Valores zero |
|---|---:|
| Estimativa do próximo prêmio | 860 |
| Rateio por ganhador da sena | 2.308 |
| Rateio por ganhador da quina | 0 |
| Rateio por ganhador da quadra | 0 |
| Acumulado principal | 625 |
| Arrecadação | 1.069 |
| Acumulado especial | 1.009 |

Totais de ganhadores observados: sena 973; quina 325.645; quadra 20.959.319. São somas das quantidades da fonte, não pessoas únicas identificadas.

**Limitação:** `known` neste contrato significa valor informado e parseável, não certificação de que o número representa a realidade financeira. Zeros históricos de arrecadação ou estimativa podem ser placeholders da exportação. Não foram convertidos em ausência nem interpretados como receita efetivamente nula. Confirmar isso na documentação oficial antes de análises financeiras.

## Integridade e reprodução

SHA-256 raw antes/depois:

`0e1936e3ac94a35a89c13ef31d705d3fb363239779ad6224b5e41171a3238686`

SHA-256 da interpretação canônica:

`5fc87bbcb2fe9f8747fd41e2c0135a84ad04ce85e9e2bb572205413b40a12e4b`

Duas execuções com instantes locais diferentes geraram o mesmo diagnóstico. Nenhum candidato foi salvo. O JSON diagnóstico completo está em [`mega-sena-normalizacao-historica.json`](mega-sena-normalizacao-historica.json).

O período termina em 2025: esta validação não atualiza a base nem comprova resultados de 2026. Também não concilia a exportação com uma fonte oficial externa e não resolve a semântica dos zeros financeiros.

## Conclusão

O normalizador passou por todo o snapshot, e não apenas pelas fixtures. Há evidência suficiente para testar o mesmo padrão em uma segunda fonte sem introduzir banco ou coleta. As hipóteses de regra e origem continuam explicitamente limitadas ao que a SPEC-0001 observou.
