# Auditoria do workspace de ingestão Mega-Sena — SPEC-0022

## Resultado

Diagnóstico offline executado em 20/10/2026 (America/Sao_Paulo), usando o normalizador `spec-0020-v1`. O workspace apresentou **integridade consistente (`healthy`)**, sem erros ou avisos.

O [diagnóstico JSON](mega-sena-auditoria-ingestao.json) contém manifesto, hashes, contagens, cobertura e plano manual. Duas execuções consecutivas produziram o mesmo conteúdo.

Manifesto das entradas: `01c1e25c4cedc3e63b05aef2356bc28fdd18e2dc3a0188c5f790fc799a335324`.

## Evidências encontradas

| Documento | Quantidade |
|---|---:|
| Artefatos raw verificados | 3 |
| Receipts verificados | 3 |
| Outcomes examinados | 4 |
| Revisões candidatas | 3 |
| Resumos de sincronização | 2 |
| Falhas de integridade | 0 |
| Avisos de recuperação | 0 |

Os dois resumos incluem uma descoberta interrompida pelo bloqueio de rede e um lote concluído por orçamento. A tentativa de rede sem corpo não precisa ter um raw correspondente; seu erro está registrado no resumo. Isso não foi confundido com corrupção de evidência.

## Cobertura efetiva

| Medida | Resultado |
|---|---|
| Baseline XLSX referenciada e conferida | concursos 1–2954, conforme auditoria anterior |
| Cursor declarado | 2955 |
| Cursor sustentado pela cadeia completa | 2955 |
| Candidatos locais consistentes | 2954, 2955 e 3071 |
| Sobreposição com a baseline | 2954, capturado na validação unitária |
| Candidato antecipado | 3071 |
| Último observado nas capturas locais | 3071 |
| Identificadores pendentes para o cursor alcançá-lo | 116 |
| Identificadores desse intervalo sem candidato verificado | 115: de 2956 a 3070 |

Não há contradição entre 116 pendentes e 115 ausentes: o 3071 já foi capturado, mas os concursos intermediários precisam ser processados antes de o cursor avançar até ele.

O histórico XLSX não foi reimportado nem novamente certificado linha a linha. O hash confirma que continua sendo o artefato auditado anteriormente. Os três registros do workspace permanecem candidatos, sem promoção a concursos publicados.

## Ação recomendada pelo diagnóstico

`continue_bounded_sync`: continuar manualmente os lotes com os limites já definidos. Essa recomendação não foi executada nesta tarefa.

Não foi necessário reparar, excluir ou reescrever arquivos operacionais. Não houve novas consultas à fonte, avanço do cursor ou geração de capturas.

## Limites

- Diagnóstico válido para o manifesto acima; futuras capturas mudam as entradas e exigem nova auditoria.
- O último disponível na web não foi consultado nesta etapa.
- A reprodução usa o normalizador identificado, não uma certificação externa de cada prêmio.
- Hashes e manifesto não substituem backup, controle de acesso ou assinatura do fornecedor.

Para repetir a verificação e tratar falhas futuras, consultar o [guia de auditoria e recuperação](../engineering/auditoria-recuperacao-mega-sena.md).
