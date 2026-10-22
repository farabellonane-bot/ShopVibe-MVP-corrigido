# Comandos usados (PowerShell, Windows)

Lista na ordem em que a demonstração é reproduzida. Requisito: Docker Desktop aberto.

## 1. Preparar o ambiente

```powershell
docker --version
docker compose version
Set-Location C:\caminho\da\pasta\ShopVibe_MVP
```

## 2. Subir a infraestrutura (primeira vez baixa cerca de 5 GB)

```powershell
.\start.ps1
```

O script executa `docker compose up -d --build`, espera o conector ficar `RUNNING` e confere o fluxo até o MongoDB. Manualmente, os equivalentes são:

```powershell
docker compose up -d --build
docker compose ps
```

Esperado: Kafka, Redis, Mongo, Postgres e Connect como `healthy`; `kafka-init` e `connector-init` como `Exited (0)` (criam o tópico e registram o conector); `api`, `worker` e `simulator` como `Up`.

## 3. Conferir o conector Debezium e o tópico

```powershell
Invoke-RestMethod http://localhost:8083/connectors/shopvibe-postgres-connector/status | ConvertTo-Json -Depth 5
docker exec shopvibe-kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list
```

## 4. Demonstração (duas janelas do PowerShell)

Antes, pare o simulador (ele sobe junto com o ambiente), para o tópico mostrar só o pedido da demonstração. Alternativa: suba tudo com `.\start.ps1 -SemSimulador`.

```powershell
docker compose stop simulator
```

**Janela A:** consumir o tópico (uma linha só; deixe rodando)

```powershell
docker exec -it shopvibe-kafka /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic shopvibe.public.orders
```

**Janela B:** criar um pedido novo na origem

```powershell
docker exec shopvibe-postgres psql -U shopvibe -d shopvibe -c "INSERT INTO orders (customer_id, total, status) VALUES (999, 42.90, 'created');"
```

O evento aparece na janela A em poucos segundos. Encerre o consumidor com `Ctrl+C`.

## 5. Camada bronze (MongoDB, coleção `raw_events`)

```powershell
docker exec shopvibe-mongo mongosh shopvibe --quiet --eval 'db.raw_events.countDocuments({})'
docker exec shopvibe-mongo mongosh shopvibe --quiet --eval 'db.raw_events.find().sort({$natural:-1}).limit(1).pretty()'
```

## 6. Extras (opcional)

```powershell
Invoke-RestMethod http://localhost:8000/health
Start-Process "http://localhost:8000/docs"
docker compose start simulator   # religa o gerador de pedidos (sobe junto com o ambiente)
docker compose logs --tail=20 worker
```

## 7. Encerrar

```powershell
docker compose down
```

`docker compose down -v` também apaga os dados persistidos (irreversível); use só para recomeçar do zero.
