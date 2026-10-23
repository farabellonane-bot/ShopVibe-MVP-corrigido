import json
import os
import signal
import time
from datetime import datetime, timezone
from decimal import Decimal
from confluent_kafka import Consumer, KafkaError, KafkaException, TopicPartition
from pymongo import MongoClient, ASCENDING
import redis
from app.common import parse_debezium_value, today_key

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9094")
TOPIC = os.getenv("KAFKA_TOPIC", "shopvibe.public.orders")
MONGO = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
DB = MONGO[os.getenv("MONGO_DB", "shopvibe")]
RAW = DB["raw_events"]
ORDERS = DB["orders_current"]
ALERTS = DB["fraud_alerts"]
R = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)

RAW.create_index([("event_id", ASCENDING)], unique=True)
ORDERS.create_index([("order_id", ASCENDING)], unique=True)
ALERTS.create_index([("alert_id", ASCENDING)], unique=True)

running = True
def stop(*_):
    global running
    running = False
signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)

def as_int(value):
    return int(value) if value is not None else None

def process_message(msg):
    value = msg.value()
    if value is None:
        return
    parsed = parse_debezium_value(value)
    # Guarda todos os envelopes CDC brutos, inclusive eventos que não alteram métricas.
    try:
        envelope = json.loads(value.decode("utf-8"))
    except Exception:
        envelope = {"unparsed": value.decode("utf-8", errors="replace")}
    event_id = f"{msg.topic()}:{msg.partition()}:{msg.offset()}"
    RAW.update_one(
        {"event_id": event_id},
        {"$setOnInsert": {
            "event_id": event_id, "topic": msg.topic(),
            "partition": msg.partition(), "offset": msg.offset(),
            "received_at": datetime.now(timezone.utc).isoformat(),
            "payload": envelope
        }},
        upsert=True
    )
    if not parsed:
        return

    row = parsed["row"]
    order_id = as_int(row.get("order_id"))
    if order_id is None:
        return
    # Snapshot inicial ('r') carrega histórico para consulta, mas não deve inflar vendas do dia.
    is_new_order_event = parsed.get("op") == "c"
    total = Decimal(str(row.get("total") or "0"))
    created_at = row.get("created_at")
    doc = {
        "order_id": order_id,
        "customer_id": as_int(row.get("customer_id")),
        "total": float(total),
        "status": row.get("status"),
        "created_at": created_at,
        "last_cdc_op": parsed.get("op"),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    ORDERS.update_one({"order_id": order_id}, {"$set": doc}, upsert=True)

    # Redis idempotency: event key derives from Kafka offset. Metrics only increment once.
    if is_new_order_event:
        metric_event_key = f"shopvibe:processed:{event_id}"
        if R.set(metric_event_key, "1", nx=True, ex=60*60*24*8):
            date_key = today_key()
            # Atomic transaction keeps count and sum consistent for this processed event.
            pipe = R.pipeline(transaction=True)
            pipe.incr(f"shopvibe:orders:{date_key}")
            pipe.incrbyfloat(f"shopvibe:sales:{date_key}", float(total))
            pipe.execute()

            customer_id = as_int(row.get("customer_id"))
            if customer_id is not None:
                # ZSET stores event timestamp scores, so the sliding 120-second window is exact.
                now = time.time()
                key = f"shopvibe:customer_orders:{customer_id}"
                R.zremrangebyscore(key, "-inf", now - 120)
                R.zadd(key, {str(order_id): now})
                R.expire(key, 180)
                count = R.zcard(key)
                if count > 5:
                    alert_id = f"{customer_id}:{order_id}"
                    alert = {
                        "alert_id": alert_id, "customer_id": customer_id,
                        "order_id": order_id, "orders_in_120s": count,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "rule": "mais de 5 pedidos em 120 segundos"
                    }
                    ALERTS.update_one({"alert_id": alert_id}, {"$setOnInsert": alert}, upsert=True)

def main():
    consumer = Consumer({
        "bootstrap.servers": BOOTSTRAP,
        "group.id": "shopvibe-cg",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
        "max.poll.interval.ms": 300000,
        # Se o tópico ainda não existir, volta a procurá-lo a cada 5s (padrão: 5 min).
        "topic.metadata.refresh.interval.ms": 5000,
    })
    consumer.subscribe([TOPIC])
    print(f"[worker] Consumindo {TOPIC} em {BOOTSTRAP}", flush=True)
    topic_warned = False
    try:
        while running:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                err = msg.error()
                if err.code() == KafkaError.UNKNOWN_TOPIC_OR_PART:
                    # Não é falha: o tópico ainda não foi criado. Espera e tenta de novo.
                    if not topic_warned:
                        print(f"[worker] Tópico {TOPIC} ainda não existe; aguardando...", flush=True)
                        topic_warned = True
                    continue
                if err.code() == KafkaError._PARTITION_EOF:
                    continue
                if err.fatal():
                    # Erro irrecuperável: sai para o Docker (restart: unless-stopped) reiniciar.
                    print(f"[worker] Erro fatal do Kafka: {err}", flush=True)
                    raise KafkaException(err)
                print(f"[worker] Kafka: {err}", flush=True)
                continue
            topic_warned = False
            try:
                process_message(msg)
                consumer.commit(message=msg, asynchronous=False)
            except Exception as exc:
                print(f"[worker] Erro ao processar; vai tentar de novo a mesma mensagem: {exc}", flush=True)
                # Volta o consumidor para esta mensagem. Sem o seek, o poll seguinte entregaria
                # a próxima mensagem e o commit dela marcaria esta como lida (perda de evento).
                try:
                    consumer.seek(TopicPartition(msg.topic(), msg.partition(), msg.offset()))
                except KafkaException as seek_exc:
                    print(f"[worker] Falha no seek: {seek_exc}", flush=True)
                time.sleep(1)
    finally:
        consumer.close()
        MONGO.close()

if __name__ == "__main__":
    main()
