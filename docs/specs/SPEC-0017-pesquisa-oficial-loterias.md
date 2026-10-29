# SPEC-0017 — Pesquisa oficial e enriquecimento das loterias

## Estado

Concluída em 2026-10-20.

## Objetivo e limites

Consolidar conhecimento oficial e atual sobre Mega-Sena, Lotofácil, +Milionária, Powerball, Mega Millions e EuroMillions antes de definir o catálogo configurável. A tarefa foi exclusivamente de pesquisa e documentação: sem coleta em massa, banco de dados, alteração dos arquivos brutos, interface ou automação.

## Método

- Priorizar páginas dos operadores e consórcios oficiais.
- Registrar a data da consulta e o caráter volátil de preços, horários, calendários e premiações.
- Separar a regra comum da loteria de regras locais, extensões opcionais e promoções.
- Confrontar a regra vigente com as versões históricas já identificadas nas SPECs 0004–0016.
- Não tratar uma página pública como contrato técnico estável de API.

## Entregas

- [Dossiê oficial das seis loterias](../data/dossie-oficial-loterias.md), com regras, operação, premiação, fontes e lacunas.
- [Registro estruturado de conhecimento](../data/loterias-conhecimento-atual.json), datado e próprio para orientar o futuro catálogo.
- Aprendizados L-067 a L-074 em [learnings.md](../engineering/learnings.md).

## Constatações principais

1. Todas as seis modalidades têm dois ou mais conjuntos de números, faixas ou mecanismos que não cabem em uma tabela plana universal.
2. Preço, calendário, matriz, premiação e disponibilidade territorial mudam; portanto precisam de vigência temporal.
3. Powerball, Mega Millions e EuroMillions têm fatos comuns ao jogo e exceções por jurisdição.
4. Extensões como Double Play, Power Play, My Million e Ireland Only Raffle não devem ser confundidas com a combinação principal.
5. Horário de sorteio, limite de venda e horário de publicação são eventos diferentes.
6. As páginas oficiais brasileiras expõem campos úteis para coleta, mas isso não equivale a uma API pública documentada.
7. As fontes oficiais ainda não fornecem, em uma única origem e formato, todos os dados históricos financeiros e territoriais desejados.

## Critérios de aceitação verificados

- As seis loterias foram pesquisadas em fontes oficiais.
- Regras atuais, calendário, preço, moeda, probabilidades principais e premiação foram registrados quando publicados.
- Mudanças históricas relevantes e diferenças territoriais foram destacadas.
- Fatos confirmados, inferências e lacunas estão separados.
- Todas as afirmações externas têm URL e data de verificação.
- Nenhum arquivo bruto foi modificado e nenhum download em massa foi executado.

## Próxima tarefa recomendada

**SPEC-0018 — Consolidar os seis históricos e definir o contrato do catálogo configurável de loterias.**

Justificativa: agora existem evidências históricas e regras oficiais atuais. O próximo passo deve transformar as diferenças encontradas em um contrato versionado, sem ainda criar banco ou tela administrativa.
