# ADR-005 — Durabilidade e escalabilidade (20x, cerca de 300 mil pedidos/dia)

- **Status**: Aceito (argumentação; não demonstrado no vídeo, conforme o enunciado)
- **Data**: 21/10/2026
- **Autoria**: \[nome da dupla\]
- **Requisito**: Durabilidade e escalabilidade

## Contexto

Dois requisitos não funcionais: **nenhum pedido pode se perder se um componente cair** e a solução deve **suportar 20 vezes o volume normal**. O laboratório roda em uma única máquina, com um broker. Este registro explica por que a arquitetura escolhida atende aos requisitos e o que muda em produção.

## Dimensionamento

- 15 mil pedidos/dia equivalem a cerca de **0,17 pedido/s**; 300 mil pedidos/dia, a cerca de **3,5 pedidos/s** em média.

- Hipótese de pico: mesmo concentrando o movimento e chegando a 10 vezes essa média (cerca de **35 pedidos/s**), a carga é pequena para um cluster Kafka. Os gargalos prováveis são o worker e os bancos, e por isso o desenho escala cada camada separadamente.

- Esses números são estimativas; a capacidade real só se comprova com teste de carga, que fica como evolução.

## Decisão: como cada componente evita perda de pedidos

- **PostgreSQL:** o pedido só existe depois do commit, que já vai para o WAL. Em produção, adicionar réplica (standby).

- **Debezium:** a posição de leitura fica em tópicos do Kafka e o WAL é retido até ser lido; se o conector cair, retoma de onde parou.

- **Kafka:** em produção, **3 brokers**, `replication.factor=3`, `min.insync.replicas=2` e `acks=all`, com volumes persistentes. No laboratório: 1 broker e fator 1 (limitação declarada no ADR-001).

- **Worker:** só confirma o offset depois de gravar no MongoDB; se cair, relê o evento e a gravação idempotente evita duplicata.

- **MongoDB e Redis:** em produção, replica set no MongoDB e persistência/réplica no Redis; as métricas podem ser reconstruídas a partir do bronze.

## Decisão: como escalar

- **Partições e consumidores:** aumentar as partições do tópico (de 3 para 12 ou mais) e rodar vários workers no mesmo grupo (até um por partição).

- **Kafka Connect:** modo distribuído, para o conector sobreviver à perda de um nó.

- **API:** sem estado, replicável atrás de um balanceador.

- **Armazenamento:** replicação e, se o volume pedir, particionamento no MongoDB.

## Alternativas consideradas

- **Escalar um único servidor (vertical):** simples, mas continua sendo ponto único de falha.

- **Fila gerenciada em nuvem:** reduz a operação, mas tem custo recorrente e dependência do fornecedor, o que conflita com o critério de custo.

## Consequências

- Positivas: cada camada escala e falha de forma independente, e o histórico no Kafka e no bronze permite recuperar.

- Negativas: operação mais complexa e mais cara em produção; a ordem das mensagens só vale dentro da partição; o MVP **não comprova** os 300 mil pedidos/dia nem a tolerância à perda de um broker.
