# Protótipo navegável do LottoBrain

Abra [index.html](index.html) em um navegador moderno. Não precisa instalar dependências, construir o projeto, configurar banco ou fornecer credenciais. Mantenha os quatro arquivos `data.js`, `model.js`, `app.js` e `styles.css` na mesma pasta do HTML.

Para servir localmente, a partir da raiz do repositório:

```powershell
.venv/Scripts/python -m http.server 8765 --bind 127.0.0.1 --directory docs/design/prototipo
```

Abra `http://127.0.0.1:8765/` e encerre o servidor com Ctrl+C ao terminar. Esse comando serve somente a pasta visual, sem expor o repositório inteiro. O servidor temporário da validação foi encerrado após os testes.

## Como explorar

1. A demonstração começa como usuário aprovado. Escolha qualquer uma das seis loterias e navegue por resumo, concursos, estatísticas e previsões.
2. Altere janela/datas, consulte concursos, abra `i`, tabelas dos gráficos e números para ver ocorrências. Os filtros constam da URL e sobrevivem ao recarregamento.
3. Em **Cenários e jornadas**, selecione visitante, cadastro pendente, revogado, administrador com/sem MFA e estados de carregamento, falha, atraso e qualidade.
4. Como administrador, use Pessoas e acessos, Catálogo, Execuções e Revisão. No celular esses destinos ficam no menu. Para ver MFA, abra uma área administrativa e mude para administrador sem MFA.
5. Use **Restaurar demonstração** para voltar ao início. Recarregar também descarta solicitações, rascunhos e decisões demonstrativas, preservando apenas filtros do endereço.

## O que é real e o que é demonstrativo

São reais os 180 registros preservados (30 de cada modalidade), suas datas, números e financeiros presentes na fonte. Contagens, médias, frequência e intervalos são calculados nesse recorte. [Proveniência](../proveniencia-prototipo.json) e [verificação](../validacao-etapa-4.md) documentam os limites. Não houve download novo ou alteração dos históricos.

São demonstrativos login, aprovação, MFA, cadastro/ativação, fila, conclusão e revisão. Não há chamadas à API, coletor, banco, Google, envio de e-mail, armazenamento persistente, cookies ou telemetria. O único link externo explícito permite ao usuário consultar a fonte; não é usado automaticamente. Não digite dados pessoais ou credenciais reais.

As previsões têm métodos e estados desenhados, mas nenhum modelo treinado, acurácia, probabilidade ou combinação prevista inventados. A amostra não é o histórico inteiro nem um dataset operacional aprovado. A interface mostra o que está ausente.

Este diretório é um artefato de UX, com os dados de referência disponíveis nos arquivos. As barreiras de acesso são cenários para revisão visual e não fornecem segurança real. Não publicar este protótipo como produto privado. Na implementação, reutilizar [desenho e jornadas](../etapa-4-experiencia-visual.md), [tokens e componentes](../sistema-visual.md); conectar as telas aos serviços autorizados da arquitetura planejada.
