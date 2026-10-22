#!/bin/sh
set -eu
BASE="http://connect:8083"
URL="$BASE/connectors"
NAME="shopvibe-postgres-connector"

echo "Aguardando Kafka Connect..."
i=0
until curl -fsS "$BASE/" >/dev/null; do
  i=$((i+1))
  if [ "$i" -gt 60 ]; then echo "Kafka Connect não ficou disponível"; exit 1; fi
  sleep 2
done

CONFIG='{
  "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
  "database.hostname": "postgres",
  "database.port": "5432",
  "database.user": "shopvibe",
  "database.password": "shopvibe_dev",
  "database.dbname": "shopvibe",
  "topic.prefix": "shopvibe",
  "plugin.name": "pgoutput",
  "slot.name": "shopvibe_slot",
  "publication.autocreate.mode": "filtered",
  "table.include.list": "public.orders",
  "snapshot.mode": "initial",
  "decimal.handling.mode": "string",
  "tombstones.on.delete": "false"
}'

# O Connect pode responder 409/500 logo depois de subir (rebalance em andamento).
# O PUT é idempotente, então basta tentar de novo.
echo "Registrando conector Debezium PostgreSQL..."
i=0
until curl -fsS -X PUT "$URL/$NAME/config" -H 'Content-Type: application/json' --data "$CONFIG"; do
  i=$((i+1))
  if [ "$i" -gt 20 ]; then echo "Falha ao registrar o conector após 20 tentativas"; exit 1; fi
  echo "Tentativa $i falhou; nova tentativa em 3s..."
  sleep 3
done
echo

# Só termina quando conector e task estiverem RUNNING. Assim, quem depende deste
# serviço (worker e simulador) só sobe com o pipeline CDC realmente ativo.
echo "Aguardando conector e task ficarem RUNNING..."
i=0
while true; do
  STATUS=$(curl -fsS "$URL/$NAME/status" 2>/dev/null || true)
  RUNNING=$(echo "$STATUS" | grep -o '"state":"RUNNING"' | wc -l | tr -d ' ')
  if [ "$RUNNING" -ge 2 ]; then break; fi
  if echo "$STATUS" | grep -q '"state":"FAILED"'; then
    echo "Conector em estado FAILED:"; echo "$STATUS"; exit 1
  fi
  i=$((i+1))
  if [ "$i" -gt 60 ]; then echo "Conector não ficou RUNNING a tempo. Último status: $STATUS"; exit 1; fi
  sleep 2
done

echo "Conector RUNNING. Confira em $BASE/connectors/$NAME/status (porta 8083 no host)."
