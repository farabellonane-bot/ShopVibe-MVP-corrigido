# ADR-002 — Captura de mudanças (CDC) com Debezium e Kafka Connect

- **Status**: Aceito
- **Data**: 21/10/2026
- **Autoria**: \[nome da dupla\]
- **Requisito**: RF01 (obrigatório); latência e durabilidade

## Contexto

Os pedidos já são gravados pelo site e pelo app no PostgreSQL. É preciso levar cada pedido novo ao Kafka em segundos, sem esperar a cópia das 2h da manhã, sem alterar o código do site e sem sobrecarregar o banco que atende os clientes.

## Decisão

Configurar o PostgreSQL com `wal_level=logical` e usar o **Debezium PostgreSQL Connector** (executado no Kafka Connect) para ler o log de transações (WAL) e publicar cada mudança da tabela orders no tópico `shopvibe.public.orders`. A tabela usa `REPLICA IDENTITY FULL` e o conector é registrado automaticamente por um script na subida do ambiente.

## Alternativas consideradas

- **Aplicação grava no banco e depois publica no Kafka:** são duas operações separadas; se falhar entre elas, o pedido existe em um lado e não no outro.

- **Polling (consulta periódica à tabela):** adiciona latência e carga ao banco, e pode perder mudanças ocorridas entre uma consulta e outra.

- **Tabela outbox com publicador próprio:** é confiável, porém exige código e operação próprios; fica como alternativa futura.

- **ETL em lote:** latência de horas, o problema que queremos eliminar.

## Consequências positivas

- Baixa latência: a mudança é lida do log logo após o commit, sem consultas repetidas ao banco.

- Nenhuma alteração no site ou no app; a origem continua simples.

- **Durabilidade:** a posição de leitura do conector fica guardada no próprio Kafka e o PostgreSQL retém o WAL até ele ser lido; se o conector cair, retoma de onde parou, sem perder pedidos.

- Debezium e Kafka Connect têm licença Apache 2.0 (open source).

## Consequências negativas e limitações

- Mais um componente para operar (Kafka Connect) e configuração do PostgreSQL (slot e publicação lógica).

- Se o conector ficar parado por muito tempo, o PostgreSQL acumula WAL e o disco pode encher; é preciso monitorar.

- O snapshot inicial gera eventos com `op=r`, que não devem ser contados como vendas novas.

- Mudanças de esquema da tabela exigem cuidado com os consumidores.

## Validação

No vídeo: inserir um pedido no PostgreSQL e ver o evento no tópico. Também é possível consultar o status do conector em `http://localhost:8083/connectors/shopvibe-postgres-connector/status`.
