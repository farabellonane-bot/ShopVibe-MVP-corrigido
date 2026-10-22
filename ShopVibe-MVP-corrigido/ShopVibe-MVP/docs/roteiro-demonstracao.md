# Roteiro do vídeo (até 5 minutos)

O enunciado pede quatro coisas no vídeo: (1) ambiente em execução, (2) pedido novo criado na origem, (3) evento no tópico do Kafka em poucos segundos e (4) eventos gravados na camada bronze. Narre em voz ou legenda o que acontece em cada passo.

**Antes de gravar**

- Deixe o ambiente de pé (`docker compose up -d --build`) e **pare o simulador**: `docker compose stop simulator`. Com ele ligado, o consumidor do Kafka fica poluído e o pedido da demonstração se perde no meio dos outros.
- Abra duas janelas do PowerShell lado a lado (A e B) na pasta do projeto.
- Não use `docker compose down -v` antes de gravar: ele apaga os dados.

| Tempo | O que mostrar | Comando ou ação |
|---|---|---|
| 0:00 a 0:30 | O problema da ShopVibe (lote às 2h, fraude e estoque descobertos tarde) e o desenho da solução | Abrir `docs/desenho-solucao.png` |
| 0:30 a 1:15 | **Item 1:** contêineres ligados e conector registrado | `docker compose ps` e `Invoke-RestMethod http://localhost:8083/connectors/shopvibe-postgres-connector/status` |
| 1:15 a 2:45 | **Itens 2 e 3:** pedido novo na origem e evento no Kafka | Janela A: consumidor do tópico (sem `--from-beginning`). Janela B: `INSERT` do pedido. Narrar `op: c` e o bloco `after` |
| 2:45 a 4:15 | **Item 4:** evento gravado na camada bronze | `mongosh` em `raw_events` (contagem e último documento); explicar o `event_id` `topico:partição:offset` |
| 4:15 a 4:45 | Opcional: o dado servindo ao negócio | `http://localhost:8000/eventos/brutos` ou `/vendas/hoje` |
| 4:45 a 5:00 | Limitações e evolução | Broker único e fator de replicação 1 no laboratório; cluster e teste de carga como evolução (ADR-005) |

Os comandos exatos estão em [`comandos.md`](comandos.md).
