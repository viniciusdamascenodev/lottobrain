# SPEC-0022 — Auditoria de cobertura e recuperação da ingestão Mega-Sena

## Estado

Concluída em 20/10/2026 (America/Sao_Paulo). Critérios definidos antes da construção.

## Objetivo

Produzir diagnóstico determinístico e somente leitura do workspace de ingestão: baseline, checkpoint, revisões, receipts, artefatos, outcomes e resumos de sincronização. Gerar orientações de recuperação sem executar reparos.

## Critérios de aceitação

- Conferir hash da baseline auditada sem modificar o histórico.
- Auditar todos os arquivos e relações, acumulando erros em vez de parar no primeiro JSON inválido.
- Validar hashes raw e semânticos, identidade, sequência de revisões e reprodução do candidato a partir de sua captura.
- Conferir evidência de processamento e continuidade de todo o intervalo declarado pelo cursor.
- Distinguir baseline referenciada, candidatos materializados, capturas antecipadas e pendências; nunca chamar candidato de publicado.
- Detectar arquivos órfãos, referências ausentes, resultados incoerentes, checkpoint inválido e mudanças durante leitura.
- Não criar lock, corrigir cursor, apagar evidência, consultar rede ou escrever no workspace auditado.
- Diagnóstico reproduzível sem relógio de auditoria ou caminhos absolutos no conteúdo.
- Plano de recuperação manual orientado pelos problemas encontrados.
- CLI, testes offline de corrupção/interrupção e relatório do estado local real.

## Entregas

- `app/application/audit_mega_sena.py`: snapshot e auditorias puras de artefatos, receipts, outcomes, revisões, checkpoint e runs, com faixas compactas e ações manuais.
- `app/infrastructure/local_audit.py`: leitura sem escrita, sem seguir links detectados, com limites por arquivo e manifesto de conteúdo.
- `app/interfaces/audit_mega_sena.py`: CLI offline e exportação opcional para arquivo novo fora do workspace.
- `tests/test_mega_sena_audit.py`: 20 testes de integridade, cobertura, corrupção, reproducibilidade e não mutação.
- [Relatório do workspace real](../data/mega-sena-auditoria-ingestao.md) e [diagnóstico JSON](../data/mega-sena-auditoria-ingestao.json).
- [Procedimentos de recuperação manual](../engineering/auditoria-recuperacao-mega-sena.md).
- Aprendizados L-105 a L-111 em [learnings.md](../engineering/learnings.md).

## Verificação

- 20 testes novos e 54 testes relacionados ao domínio, catálogo, normalização, coleta e sincronização passaram.
- Duas auditorias reais consecutivas produziram saída idêntica.
- Manifesto verificado: `01c1e25c4cedc3e63b05aef2356bc28fdd18e2dc3a0188c5f790fc799a335324`.
- Workspace real: 3 raws, 3 receipts, 4 outcomes, 3 revisões candidatas e 2 resumos; zero inconsistências.
- Cursor verificado em 2955; 3071 identificado como candidato antecipado; 115 identificadores sem candidato no intervalo 2956–3070.
- Auditoria não alterou o manifesto do workspace nem os seis históricos originais.
- Nenhuma chamada de rede, reparo, coleta, publicação ou avanço de cursor.

## Limitações e decisões

- Verificação da baseline reusa a certificação local anterior por hash; não reexecuta normalização XLSX.
- A interpretação é reproduzida com a versão do normalizador registrada no relatório. Mudanças futuras podem exigir conciliação explícita de versões.
- O leitor faz duas capturas para detectar mudanças observadas; não promete snapshot transacional do filesystem. Deve operar sobre workspace parado ou cópia estável.
- A recuperação é um procedimento humano apoiado no diagnóstico. Não há reconstrução ou correção automática de evidência.
- O status de integridade não representa completude de dados atuais nem aprovação de publicação.

## Próxima tarefa recomendada

**SPEC-0023 — Modelo lógico e contrato de persistência PostgreSQL.**

Justificativa: o primeiro fluxo vertical já demonstrou aquisição, continuidade, revisão, rastreabilidade e auditoria. Agora suas invariantes devem orientar o modelo lógico, relacionamentos, constraints e transações, antes de implementar migrações e repositórios.
