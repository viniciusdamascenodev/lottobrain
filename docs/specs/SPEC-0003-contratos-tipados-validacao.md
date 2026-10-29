# SPEC-0003 — Contratos tipados e validação do domínio em Python

## Estado

Implementada em 2026-09-14.

## Objetivo

Materializar o modelo conceitual da SPEC-0002 em contratos Python independentes de banco, API e framework, provando com testes que as seis loterias podem ser representadas sem um esquema fixo de seis números.

## Escopo implementado

- enums para estados e semânticas do domínio;
- definições tipadas de loteria, regra, série e componente;
- resultados com componentes e atributos separados;
- montantes monetários com estado, decimal e moeda;
- faixas de premiação e referências externas;
- proveniência raw mínima;
- seleção temporal de regra;
- validação estruturada de concursos;
- exemplos testados das seis loterias;
- Double Play como série adicional e multiplicador como atributo.

## Decisão de implementação

Foram usadas `dataclasses` imutáveis, `Enum`, `Decimal` e tipos da biblioteca padrão. Isso evita acoplamento prematuro com ORM, Flask ou biblioteca de serialização. A conversão de payloads externos continua sendo responsabilidade futura dos adaptadores.

Há dois níveis de proteção:

1. definições estruturalmente impossíveis geram `ValueError` na construção;
2. dados de concurso incompatíveis geram uma coleção de `ValidationIssue`, que poderá sustentar quarentena e relatório de qualidade.

`assert_valid_draw` existe para consumidores que preferem falha imediata e lança `DomainValidationError` contendo os mesmos problemas estruturados.

## Códigos de validação iniciais

| Código | Situação |
|---|---|
| `draw.lottery_mismatch` | Concurso e definição pertencem a loterias diferentes |
| `draw.rule_not_found` | Não existe regra validada para a data |
| `draw.rule_mismatch` | Rótulo informado não corresponde à regra vigente |
| `draw.missing_provenance` | Publicação sem evidência raw |
| `series.missing` | Série obrigatória ausente |
| `series.unknown` | Série não prevista pela regra |
| `component.missing` | Componente definido ausente |
| `component.unknown` | Componente não previsto |
| `component.invalid_count` | Cardinalidade incorreta |
| `component.invalid_type` | Tipo incompatível |
| `component.out_of_range` | Valor fora do intervalo da regra |
| `component.duplicate_values` | Repetição proibida |
| `component.invalid_order` | Ordem incompatível com a definição |

## Invariantes comprovados

- Lotofácil aceita 15 números sem campos posicionais fixos.
- +Milionária mantém números e trevos separados.
- Powerball e Mega Millions mantêm a bola especial separada.
- EuroMillions mantém duas estrelas separadas.
- Double Play é uma série adicional opcional.
- Power Play é atributo, não bola.
- Versões validadas não podem se sobrepor.
- Loteria em rascunho pode não ter regras; loteria ativa exige uma regra validada.
- A versão correta é selecionada pela data do concurso.
- Zero monetário é preservado como conhecido.
- Montante conhecido exige moeda; desconhecido não aceita valor normalizado.
- Concurso publicado exige proveniência raw com hash e instante timezone-aware.
- Problemas podem ser coletados sem modificar o dado de entrada.

## Fora do escopo preservado

- banco, ORM e migrations;
- serialização JSON/API;
- parsers dos arquivos históricos;
- importação e persistência;
- pesquisa de regras históricas;
- scheduler e coletores;
- autenticação, frontend, análises e modelos.

## Arquivos

```text
app/domain/
├── __init__.py
├── errors.py
├── models.py
├── types.py
└── validation.py

tests/
└── test_domain.py
```

## Critérios de aceitação

- [x] Somente biblioteca padrão no domínio.
- [x] Contratos não dependem de persistência ou web.
- [x] As seis modalidades possuem exemplo válido testado.
- [x] Regras temporais e não sobreposição são testadas.
- [x] Cardinalidade, tipo, faixa, unicidade e ordem são validados.
- [x] Números especiais não são misturados aos principais.
- [x] Multiplicadores e sorteios adicionais têm representações próprias.
- [x] Zero, desconhecido e não aplicável têm semânticas distintas.
- [x] Falhas são estruturadas e não corrigem a entrada.
- [x] Proveniência é exigida para publicação.
- [x] Nenhum banco, parser ou coletor foi criado.

## Limitações conscientes

- Os exemplos usam regras contemporâneas aparentes somente para provar o contrato; não formam um catálogo oficial.
- O domínio ainda não oferece serialização estável.
- Não existe expressão executável para critérios complexos de faixas.
- Timezone e calendário ainda não foram materializados porque não participam dos casos desta implementação.
- IDs internos ficam para a camada de persistência.

## Próxima tarefa recomendada

**SPEC-0004 — Fixtures brutas e normalizador da Mega-Sena.**

Ela deverá implementar um primeiro fluxo vertical pequeno: ler uma amostra controlada da planilha da Mega-Sena, normalizar para os contratos desta etapa, produzir problemas estruturados e provar idempotência por uma chave canônica, ainda sem banco de dados. Começar com uma única fonte reduz o risco antes de generalizar os outros cinco adaptadores.
