# ADR-0001 — Monólito modular como arquitetura inicial

## Estado

Aceita em 2026-10-20.

Concretizada pela [ADR-0004](ADR-0004-produto-privado-seis-loterias.md) em 27/10: o backend modular executa como uma função FastAPI e CLI no Actions. A separação de responsabilidades não exige containers ou processos permanentemente ligados.

## Contexto

O LottoBrain precisa atender coleta, catálogo, resultados, análise, previsão, identidade e administração. Ainda não há tráfego, equipe ou perfil de carga que justifique serviços distribuídos.

## Decisão

Usar um monólito modular no backend, com domínio e casos de uso compartilhados, executado em processos separados de API, worker e scheduler. O frontend consome a API por HTTP.

Fronteiras de módulo serão verificadas por revisão e testes arquiteturais. Comunicação interna é por interfaces de aplicação e eventos transacionais, não por acesso cruzado a tabelas.

## Consequências positivas

- transações e consistência mais simples;
- menor custo de desenvolvimento e operação;
- refatoração segura enquanto o domínio amadurece;
- implantação reproduzível do mesmo núcleo por função HTTP e CLI, com imagem opcional;
- possibilidade de extrair módulo no futuro.

## Custos e riscos

- disciplina é necessária para evitar acoplamento interno;
- uma implantação atualiza vários módulos;
- jobs pesados precisam de processos e limites próprios.

## Alternativas rejeitadas agora

- Microsserviços: aumentariam rede, consistência distribuída, observabilidade e custo sem evidência de benefício.
- Aplicação Flask única com templates e jobs no processo web: mistura ciclos de vida e dificulta segurança, testes e escala.
- Serverless por função para todo o backend: amplia fragmentação e pode prejudicar jobs longos e transações coordenadas.

## Gatilhos para revisão

Escala independente comprovada, requisito forte de isolamento, equipes autônomas ou cadências de implantação incompatíveis.
