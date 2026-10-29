# SPEC-0005 — Normalização histórica completa da Mega-Sena em memória

## Estado

Concluída em 2026-09-15.

## Objetivo

Percorrer o XLSX histórico completo, manter candidatos somente em memória e produzir um diagnóstico reproduzível conciliado com a SPEC-0001.

## Critérios definidos antes da implementação

- Ler todas as 2.954 linhas do snapshot auditado.
- Conciliar SHA-256, concursos 1–2954 e datas 1996-03-11 a 2025-12-20.
- Contar candidatos, válidos, inválidos e identidades ausentes sem descartar linhas.
- Detectar chaves duplicadas e lacunas entre os concursos observados.
- Contar valores monetários conhecidos, desconhecidos e zero por finalidade.
- Conciliar cidade ausente (2.331) e observação ausente (2.059).
- Registrar cada problema com posição da linha e chave, quando disponível.
- Executar duas vezes e obter o mesmo diagnóstico e hash de conteúdo canônico.
- Verificar hash da fonte antes e depois.
- Adicionar regressões para duplicidade, identidade ausente e entrada vazia.
- Não escrever candidatos, alterar o raw, criar banco ou modificar relatórios legados.

## Entregas previstas

- módulo de auditoria histórica e comando somente leitura;
- testes de unidade e contrato do histórico completo;
- relatório diagnóstico separado em `docs/data/`;
- aprendizados reutilizáveis.

## Limites

Validade significa compatibilidade com o contrato e a regra baseline observada, não certificação por fonte oficial. Valores zero são preservados e não provam que a informação financeira estava efetivamente disponível. Não haverá pesquisa externa, novas loterias, coleta ou persistência de candidatos.

## Decisões e resultado

O fluxo foi implementado em `app/ingestion/mega_sena_history.py`. A CLI emite apenas diagnóstico JSON no stdout; candidatos não são gravados. Uma cópia do diagnóstico desta execução está em [`mega-sena-normalizacao-historica.json`](../data/mega-sena-normalizacao-historica.json), acompanhada do [relatório legível](../data/mega-sena-normalizacao-historica.md).

- 2.954 linhas, candidatos, válidos e chaves únicas.
- Zero identidades ausentes, inválidos, duplicidades e lacunas no intervalo.
- 17.724 valores principais, todos compatíveis com o contrato.
- Todas as oito comparações da baseline coincidiram.
- As sete finalidades monetárias observadas têm 2.954 valores parseáveis cada.
- Hash raw antes/depois idêntico.
- Duas execuções com instantes de captura local diferentes geram exatamente o mesmo diagnóstico.

## Reprodutibilidade

```powershell
python -m app.ingestion.mega_sena_history
python -m unittest discover -s tests -p 'test_mega_sena_history.py' -v
```

O comando resolve a fonte padrão a partir da localização do módulo, não do diretório corrente. Também aceita outro caminho como argumento. Código de saída zero exige fonte inalterada, baseline coincidente e todas as linhas elegíveis; divergência retorna 1, enquanto erro de leitura/normalização interrompe a execução explicitamente.

O `observed_at` passado à auditoria representa captura do snapshot **local** para a execução, não o horário original do download, que continua desconhecido. Esse instante é excluído do diagnóstico e do hash de conteúdo, evitando inventar proveniência histórica e evitando diferenças apenas pelo relógio.

## Semântica do diagnóstico

- `valid_rows`: linhas sem problemas de normalização e sem chave repetida.
- `invalid_rows`: linhas problemáticas, sem candidato/identidade ou duplicadas; todas as cópias de uma chave repetida são inelegíveis.
- `unique_keys`: chaves distintas observadas, inclusive de candidatos com problemas.
- Datas, faixas, valores e totais de ganhadores são observações dos candidatos, não uma publicação de dataset validado.
- `row_position`: posição de registro após remoção de linhas totalmente vazias, não número físico de linha Excel.
- `baseline_matches`: conciliação com o snapshot da SPEC-0001, não indicador isolado de saúde.
- `canonical_content_sha256`: impressão digital da interpretação atual, incluindo valores, estado e problemas. Não é uma API de serialização pública; mudanças no contrato podem mudar esse hash.
- O relatório contém versões explícitas para permitir interpretação de futuras diferenças.

## Verificações finais

- A suíte completa de descoberta executou 25 testes com sucesso, incluindo oito testes desta etapa. Duas verificações legadas de análise também passaram por execução direta; não foi uma execução via pytest.
- O diagnóstico JSON salvo coincidiu com uma nova auditoria completa; a compilação dos módulos e a verificação de whitespace passaram.
- [x] Todos os critérios definidos antes da execução foram atendidos.
- [x] Duplicidades, lacunas, registros inválidos, entrada vazia e fonte alterada possuem regressões.
- [x] Nenhum candidato canônico foi persistido.
- [x] Os relatórios legados e o pipeline não foram modificados.
- [x] Os seis arquivos brutos mantiveram os hashes da SPEC-0001.

## Próxima tarefa recomendada

**SPEC-0006 — Normalizador e validação histórica da Lotofácil.**

Aplicar o mesmo fluxo vertical à segunda planilha, cobrindo 15 números e cinco faixas de premiação. Reutilizar apenas os padrões que se mostrarem realmente comuns, sem criar um framework genérico de ingestão. Banco, coleta externa e interface continuam fora dessa próxima tarefa.
