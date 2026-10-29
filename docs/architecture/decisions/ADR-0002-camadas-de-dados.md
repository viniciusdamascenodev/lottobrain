# ADR-0002 — Separar raw, dados operacionais, analíticos e experimentos

## Estado

Aceita em 2026-10-20.

## Contexto

O sistema precisa reprocessar fontes, preservar correções, servir consultas e treinar modelos sem misturar evidência externa, interpretação atual e features derivadas.

## Decisão

Usar quatro camadas com linhagem explícita:

1. artefatos raw imutáveis em object storage;
2. registro normalizado e revisionado no PostgreSQL;
3. snapshots analíticos recriáveis e versionados;
4. experimentos e modelos ligados ao snapshot exato.

## Consequências positivas

- auditoria e reprodução;
- correção de parser sem novo download;
- prevenção de vazamento temporal;
- banco transacional não sobrecarregado por blobs e matrizes analíticas;
- comparação justa entre modelos.

## Custos e riscos

- mais metadados e políticas de retenção;
- necessidade de manifesto e hashes;
- cuidado para não publicar derivado de revisão superada.

## Alternativas rejeitadas agora

- Apenas arquivos locais: não oferece concorrência, durabilidade ou operação multiambiente.
- Tudo em PostgreSQL: possível em pequena escala, mas mistura blobs, transação e workloads analíticos.
- Lakehouse completo: complexidade prematura para o volume atual.
