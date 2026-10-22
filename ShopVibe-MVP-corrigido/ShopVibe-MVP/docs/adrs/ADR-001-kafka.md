# ADR-001 — Apache Kafka como barramento de eventos

- **Status**: Aceito
- **Data**: 21/10/2026
- **Autoria**: \[nome da dupla\]
- **Requisito**: RF01 (obrigatório); latência e escalabilidade

## Contexto

A ShopVibe tem cerca de 15 mil pedidos por dia e picos de 20 vezes esse volume na Black Friday. Hoje o banco é copiado às 2h da manhã e o estoque é atualizado em lote a cada 4 horas. Na última Black Friday isso gerou 300 pedidos cancelados por estoque desatualizado e R\$ 180 mil em chargebacks de uma fraude só percebida no dia seguinte, além de 68% de carrinhos abandonados sem reação imediata. A diretora comercial, Mariana Costa, pediu saber "o que está acontecendo na loja agora, não amanhã".

Para reagir em segundos, cada pedido precisa viajar da origem até vários consumidores independentes (painel de vendas, antifraude, estoque, e-mail de carrinho abandonado), e o histórico precisa ficar disponível para ser relido.

## Decisão

Usar **Apache Kafka em modo KRaft** (sem ZooKeeper), com o tópico `shopvibe.public.orders`, **3 partições** e **retenção de 7 dias**. Os eventos chegam ao tópico pelo Debezium (ADR-002) e são lidos por um grupo de consumidores (`shopvibe-cg`).

## Alternativas consideradas

- **Manter o lote (situação atual):** simples, mas é exatamente a causa dos problemas relatados pela diretoria.

- **Chamada HTTP direta do site para cada sistema:** acopla origem e consumidores; se um consumidor estiver fora do ar, o evento se perde.

- **Redis Pub/Sub:** entrega rápida, mas não guarda mensagens; quem estiver fora do ar perde o evento e não há como reprocessar.

- **RabbitMQ:** ótimo para filas de tarefas, mas o modelo é de fila, em que a mensagem sai após o consumo; o histórico para releitura por vários consumidores é menos natural do que no log do Kafka.

## Consequências positivas

- Vários consumidores independentes leem o mesmo tópico no seu próprio ritmo (painel, antifraude, estoque, e-mail).

- Os eventos ficam em disco por 7 dias, permitindo reprocessar após uma falha ou mudança de regra.

- Escala por partições e por consumidores do mesmo grupo (ver ADR-005).

- Licença Apache 2.0: ferramenta open source, sem custo de licença (ver ADR-006).

## Consequências negativas e limitações

- Exige operação e monitoramento; a curva de aprendizado é maior que a de uma fila simples.

- A ordem das mensagens só é garantida dentro de cada partição.

- No laboratório há **um único broker com fator de replicação 1**: se o broker for perdido, os dados dele também. Isso é aceito só no MVP; o plano de produção está no ADR-005.

## Validação

No vídeo: listar o tópico e consumir mensagens com `kafka-console-consumer.sh`, vendo o evento de um pedido novo chegar em poucos segundos.
