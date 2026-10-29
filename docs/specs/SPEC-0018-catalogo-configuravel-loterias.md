# SPEC-0018 — Catálogo configurável de loterias

## Estado

Concluída em 2026-10-20.

## Objetivo

Consolidar os contratos históricos das seis loterias em um catálogo único e definir a estrutura mínima necessária para cadastrar novas modalidades futuramente, sem criar banco de dados, API ou interface administrativa.

## Escopo aprovado

- Reutilizar, sem copiar, as definições históricas dos seis normalizadores.
- Representar mercados/jurisdições, fontes, autoridade, prontidão de coleta, agendas observadas, extensões e capacidades.
- Separar fatos atualmente observados de períodos cuja vigência inicial ainda não foi comprovada.
- Permitir o registro imutável de uma loteria em rascunho.
- Validar unicidade e referências internas do catálogo.
- Documentar o fluxo futuro de cadastro e as decisões de modelagem.

## Fora do escopo

- Persistência, migrações e esquema físico.
- CRUD, autenticação, autorização ou painel administrativo.
- Coleta automática ou troca das fontes históricas existentes.
- Alteração dos arquivos brutos.
- Modelos estatísticos e preditivos.

## Contrato implementado

### Núcleo reutilizado

`Lottery`, `LotteryRuleVersion`, `ResultSeriesDefinition` e `ComponentDefinition` continuam sendo a autoridade para identidade da modalidade, regras matemáticas, séries e componentes.

### Contexto acrescentado

- `MarketDefinition`: jurisdição, moeda e papel territorial.
- `DataSourceDefinition`: identidade, autoridade, propósitos, formato, URL e prontidão para automação.
- `ScheduleDefinition`: timezone, dias/horas, data de observação, evidência e vigência opcional.
- `ExtensionDefinition`: recurso de aposta, sorteio vinculado, raffle nacional ou sorteio especial.
- `LotteryCatalogEntry`: agrega núcleo, mercados, fontes, agendas, extensões e capacidades.
- `LotteryCatalog`: busca por slug e registro imutável de nova entrada.

## Invariantes

1. Slug de loteria é único no catálogo.
2. Entrada requer pelo menos um mercado e uma fonte.
3. Chaves de fontes, agendas e extensões são únicas dentro da entrada.
4. Toda extensão referencia mercados existentes na própria entrada.
5. Timezone usa identificador IANA; hora é civil e não carrega offset isolado.
6. Autoridade da fonte e prontidão para coleta são eixos independentes.
7. Agenda observada sem início oficial conhecido mantém `valid_from=null`.
8. Cadastro de rascunho pode começar sem regra, mas ativação continua exigindo regra validada.
9. O registro retorna um novo catálogo e não modifica silenciosamente o original.

## Consolidação das seis loterias

| Loteria | Versões históricas | Mercados catalogados | Extensões explícitas | Fonte histórica atual |
|---|---:|---|---|---|
| Mega-Sena | 1 | BR | Mega da Virada | CAIXA XLSX oficial |
| Lotofácil | 1 | BR | Lotofácil da Independência | CAIXA XLSX oficial |
| +Milionária | 1 | BR | — | CAIXA XLSX oficial |
| Powerball | 7 | EUA multiestadual; Reino Unido no jackpot | Power Play; Double Play | snapshot USA Mega secundário |
| Mega Millions | 7 | EUA multiestadual | multiplicador embutido | snapshot USA Mega secundário |
| EuroMillions | 3 | pan-europeu; França; Irlanda | My Million; Ireland Only Raffle | snapshot comunitário secundário; FDJ candidata oficial |

As 20 versões de regra existentes são referenciadas diretamente. O catálogo não cria uma segunda verdade sobre limites numéricos.

## Fluxo futuro de cadastro

```text
rascunho
   ↓ pesquisa de autoridade, jurisdição e licença
fontes qualificadas
   ↓ regra, agenda e extensões com evidência
validação com amostras reais
   ↓ aprovação humana e testes de fronteira
ativo para coleta
```

O painel futuro não deverá permitir ativação apenas porque nome e números foram preenchidos. A transição depende de fonte qualificada, regra sem sobreposição, timezone, amostras válidas e política operacional.

## Entregas

- `app/domain/catalog.py`: contratos e invariantes independentes de infraestrutura.
- `app/catalog.py`: catálogo inicial das seis modalidades.
- `tests/test_catalog.py`: sete testes do catálogo e do registro futuro.
- [Contrato documental](../data/catalogo-loterias.md).
- Aprendizados L-075 a L-081 em [learnings.md](../engineering/learnings.md).

## Verificação

- 7/7 testes específicos do catálogo passaram.
- Os testes do domínio e dos normalizadores que não dependem das bibliotecas ausentes continuaram passando.
- A suíte completa executou 95 testes e encontrou oito erros de ambiente: `pandas` e `openpyxl` não estão instalados. Não houve falha funcional atribuída ao catálogo.
- `requirements.txt` já estava modificado antes desta tarefa e foi preservado.
- Nenhum arquivo bruto foi modificado.

## Próxima tarefa recomendada

**SPEC-0019 — Definir a arquitetura de referência do LottoBrain.**

Justificativa: após a solicitação de uma visão estrutural completa, tornou-se necessário definir módulos, fronteiras e requisitos não funcionais antes do primeiro fluxo operacional. A coleta incremental passa para a SPEC-0020.
