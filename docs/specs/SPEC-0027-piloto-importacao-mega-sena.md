# SPEC-0027 — Piloto histórico Mega-Sena

## Estado

Concluída em 21/10/2026 (America/Sao_Paulo). Critérios e política registrados antes da implementação.

## Objetivo e limites

Provar importação local limitada, reconciliação explícita XLSX/JSON e retomada no PostgreSQL descartável dos testes. Até três registros reais do XLSX (1, 2, 2954), mais JSON 2954 já disponível. Nenhuma rede, carga integral, banco operacional, baseline/checkpoint, publicação, API ou interface. Não modificar raw, relatórios anteriores, migrations aplicadas ou contratos/hashes anteriores.

## Política da ponte v1

- Aceitar somente Mega-Sena e os dois contratos qualificados nas SPECs 0025/0026. Revisões antigas mantêm sua versão/hash; projeção para comparação não é recanonicalização persistida.
- Sob lock da identidade/draw, reler e verificar conteúdo SQL. Compartilhado divergente ou entrada que simultaneamente remove e acrescenta fatos: quarentena, sem alterar head. Não fazer merge genérico.
- Entrada igual ou subconjunto compatível: observação de apoio, sem nova revisão nem remoção de enriquecimentos. Processamento de apoio usa a versão/hash da revisão apoiada; payload registra separadamente contrato/hash da entrada, comparação, evidência e política.
- Entrada estritamente mais completa, com fatos compartilhados iguais: nova revisão no contrato da entrada; revisão anterior permanece selada. JSON pode enriquecer histórico, histórico não rebaixa JSON.
- Regra conservadora para este piloto: diferença known/unknown é divergência, não inferência de substituição; nenhuma resolução automática de correção entre fontes.

## Critérios de aceitação

1. Plano limitado e determinístico fixa origem honesta de importação legada, SHA/tamanho, seleção/localizadores, normalizador/código/política e conteúdo/evidência por linha. Reutilizar leitores existentes; parsing e storage fora de SQL.
2. Arquivo integral arquivado por hash, receipt legacy_import sem GET/status HTTP fictício, registro idempotente da intenção. Mesma chave com outro plano falha explicitamente. Não usar instante local como download original comprovado.
3. Confirmar uma linha por transação; observação, tentativa, revisão e filhos atômicos. Interrupção não anuncia lote concluído; repetir plano/chave recupera efeitos confirmados sem duplicação/regressão de head. COMMIT ambíguo exige mesma intenção, sem aquisição automática.
4. Testar JSON→XLSX como apoio e XLSX→JSON como enriquecimento; roundtrip/hash SQL de cada contrato, projeção de ponte equivalente ao normalizador real, evidência por observação preservada sem modificar filhos selados.
5. Quarentena de divergência conserva entrada e diagnóstico, sem alterar números/prêmios/head; plano com quarentena é stopped, não completed. Versão desconhecida/catálogo alterado/fonte incompatível falham fechado.
6. Cobrir rollback antes do commit, commit confirmado com resposta perdida, concorrência com conexões reais, replay antigo e mesmo arquivo com outra seleção. Manter permissões restritas, sem superuser no writer.
7. Regressão comum/PostgreSQL, hashes protegidos e auditorias anteriores preservados; nenhum novo dado histórico fictício. Mutações negativas identificadas como testes. Nenhuma migration nova salvo necessidade demonstrada; não relaxar triggers para facilitar a ponte.
8. Documentar operação de teste, evidências, limites, aprendizados e uma única próxima tarefa. O coletor JSON operacional opt-in continua com gate atual; ponte é caminho explícito do piloto, não ativação silenciosa no coletor.

## Estratégia de implementação

Preparação/ponte puras na aplicação; SQL em adaptadores separados. Reutilizar unidade de trabalho, storage, qualificação de catálogo e escrita/leitura de conteúdo, extraindo somente responsabilidades com consumidores reais. Não adicionar framework/broker/tabelas de batch antes da prova. Plano e evidência versionados podem usar os campos existentes; o piloto deve provar sua reconstrução/retomada, não presumir que bastam.

## Entregas e comprovação

- Caso de uso e preparação/restauração imutável de plano, ponte conservadora pura e adaptador PostgreSQL próprio do piloto. Nenhum novo parser, dependência ou DDL; migrations/head `0024_03` preservados.
- Importação SQL limitada às linhas reais XLSX 1/2/2954 e comparação/enriquecimento com JSON 2954, somente em bancos descartáveis. Arquivo integral preservado como evidência; seleção e versões fixadas no manifesto.
- JSON→XLSX apoia sem alterar filhos selados; XLSX→JSON gera nova revisão no contrato JSON original. Hash v1 continua `62755ae7c8057839aa4fcb97c2840afbc6e0a296844f7b02fb6d66f81bbe6477`. Replay antigo não regride head.
- Entrada/hash/evidência separados do hash/versão da revisão apoiada, em payload versionado limitado a 32 KiB. Triggers de versão/hash e imutabilidade mantidos.
- Retomada por manifesto/bytes persistidos, transação por linha e ledger de localizadores. Provas de interrupção, cinco pontos de rollback T3, resposta perdida após commit real do registro/linha, catálogo alterado, corrupção e concorrência entre fontes/retomadas.
- **267 testes aprovados**: 191 comuns (173,07 s, dez novos) e 76 no runner isolado (220,977 s: 71 PostgreSQL reais + cinco UoW simulados, incluindo 13 SQL novos). Os 27 casos anteriores de ingestão JSON continuam, após extrair o harness compartilhado.
- Hashes dos **31 arquivos protegidos** conferidos sem mudanças: dados brutos, relatórios JSON anteriores e workspace de coleta. Auditoria Mega-Sena anterior reproduzida exatamente, healthy. Vetores e relatório da SPEC-0026 mantidos pela suíte comum.
- Compileall, whitespace e links locais verificados. Aviso CRLF em requirements.txt é preexistente; não foi editado nesta tarefa. Nenhum arquivo de dependência modificado.
- Runner final: `.local-postgres/runs/a541a4c077374faca7cbf1816e473434/server.log`; cluster desligado e postmaster.pid ausente. Primeira rodada isolada também desligada; serviços PostgreSQL 12/13 existentes preservados.
- [Operação, decisões e evidências](../engineering/piloto-importacao-mega-sena.md); aprendizados L-145…L-150 e roadmap atualizados.

## Limites e gate de integração

Não houve carga integral, provisionamento operacional, promoção de baseline, checkpoint, rede ou publicação. A fixture JSON é evidência legada formatada, não bytes originais HTTP. Mutações negativas ficaram exclusivamente nos testes/storage temporário. Piloto não certifica desempenho de batch, outras loterias ou recuperação física de infraestrutura.

Teste SQL 13 comprova que o coletor JSON da SPEC-0025 ainda recusa head histórico com outra versão. Esse gate não foi removido silenciosamente: o piloto ativa a ponte por caminho explícito. Não fazer carga integral antes de integrar/provar a política no fluxo incremental. O storage de 256 KiB atende este XLSX de 221.261 bytes, não certifica artefatos maiores.

## Única próxima tarefa recomendada

**SPEC-0028 — Integração da ponte XLSX/JSON ao fluxo incremental da Mega-Sena.**

Justificativa: comprovar atualização do head histórico no fluxo existente, preservando correções, replay, evidência, leases e cursor atômico, antes de ampliar a importação. O piloto demonstrou a ponte, mas não autoriza inferir que todos os writers já interoperam. Não executada nesta SPEC.
