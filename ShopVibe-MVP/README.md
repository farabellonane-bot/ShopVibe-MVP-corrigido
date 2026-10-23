# ShopVibe — Ingestão de dados em tempo real (MVP)

Projeto didático para demonstrar o caminho **PostgreSQL → Debezium/Kafka Connect → Kafka → Worker Python → MongoDB/Redis → FastAPI**.


> Este é um MVP local de demonstração. Um único broker Kafka com fator de replicação 1 não oferece alta disponibilidade contra perda do broker. Não use as senhas deste ambiente em produção.

## Requisitos

- Docker Desktop com Docker Compose funcionando
- Aproximadamente 5 GB de espaço livre para baixar as imagens
- Navegador para acessar a API

## 1. Subir a infraestrutura

Abra o terminal (PowerShell no Windows, ou Bash) na pasta que contém `docker-compose.yml` e execute. Os comandos abaixo funcionam nos dois, exceto onde houver indicação:

```bash
docker compose up -d --build
docker compose ps
```

A primeira inicialização pode levar alguns minutos. Confira os logs se algum serviço não ficar saudável:

```bash
docker compose logs --tail=100 postgres
docker compose logs --tail=100 kafka
docker compose logs --tail=100 connect
docker compose logs --tail=100 connector-init
docker compose logs --tail=100 worker
```

O serviço `connector-init` registra o conector PostgreSQL no Kafka Connect. Para conferir o status:

- `http://localhost:8083/connectors`
- `http://localhost:8083/connectors/shopvibe-postgres-connector/status`

O tópico esperado é `shopvibe.public.orders`.

## 2. Criar pedidos de demonstração

Em outro terminal:

```bash
docker compose --profile demo up -d simulator
docker compose logs -f simulator
```

O simulador cria um pedido a cada dois segundos. Para parar apenas o simulador:

```bash
docker compose stop simulator
```

Também é possível inserir um pedido manualmente, em uma linha só (sem entrar no `psql`):

```powershell
docker exec shopvibe-postgres psql -U shopvibe -d shopvibe -c "INSERT INTO orders (customer_id, total, status) VALUES (999, 42.90, 'created');"
```

> Se preferir o modo interativo (`docker exec -it shopvibe-postgres psql -U shopvibe -d shopvibe`), lembre-se de que o prompt `shopvibe=#` é do PostgreSQL: comandos do Docker só funcionam depois de sair com `\q`.

## 3. Demonstrar a API

Abra:

- Swagger interativo: http://localhost:8000/docs
- Saúde dos serviços: http://localhost:8000/health
- Vendas de hoje: http://localhost:8000/vendas/hoje
- Pedido (troque `1` por um ID existente): http://localhost:8000/pedidos/1
- Alertas: http://localhost:8000/alertas/fraude
- Eventos brutos: http://localhost:8000/eventos/brutos

O processamento pode levar alguns segundos na primeira execução enquanto o conector e o worker iniciam.

## 4. Comandos de diagnóstico

```bash
docker compose ps
docker compose logs -f connect
docker compose logs -f worker
docker exec shopvibe-kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list
```

Para ver as mensagens do tópico (escreva em **uma linha só**; no PowerShell o `\` de fim de linha não funciona):

```powershell
docker exec -it shopvibe-kafka /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic shopvibe.public.orders --from-beginning
```

Sem `--from-beginning`, o consumidor mostra apenas eventos novos, o que é melhor para ver um pedido recém-criado chegando em tempo real.

Para conferir a camada bronze (eventos brutos no MongoDB):

```powershell
docker exec shopvibe-mongo mongosh shopvibe --quiet --eval 'db.raw_events.countDocuments({})'
docker exec shopvibe-mongo mongosh shopvibe --quiet --eval 'db.raw_events.find().sort({$natural:-1}).limit(1).pretty()'
```

## 5. Encerrar

```bash
docker compose down
```

Para apagar também os dados persistidos (**irreversível**; não use antes de entregar ou gravar a demonstração):

```bash
docker compose down -v
```

*/# Licenças

O código deste repositório usa a licença MIT (arquivo `LICENSE`). Kafka, Kafka Connect, Debezium, PostgreSQL, Python e FastAPI têm licenças open source. O MongoDB Community (SSPL) e o Redis 7.4 (RSALv2/SSPLv1) são gratuitos, 
