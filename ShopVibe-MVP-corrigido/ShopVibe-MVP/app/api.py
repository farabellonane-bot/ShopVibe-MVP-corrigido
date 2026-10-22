import os
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from pymongo import MongoClient, DESCENDING
import redis
from app.common import today_key

app = FastAPI(
    title="ShopVibe API",
    description="API de consulta do MVP de ingestão em tempo real.",
    version="1.0.0"
)
mongo = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
db = mongo[os.getenv("MONGO_DB", "shopvibe")]
r = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)

@app.get("/health")
def health():
    mongo.admin.command("ping")
    r.ping()
    return {"status": "ok", "mongo": "ok", "redis": "ok"}

@app.get("/vendas/hoje")
def vendas_hoje():
    key = today_key()
    return {
        "data": key,
        "quantidade_pedidos": int(r.get(f"shopvibe:orders:{key}") or 0),
        "valor_total": round(float(r.get(f"shopvibe:sales:{key}") or 0), 2),
        "observacao": "Contadores do worker para eventos de criação processados; snapshots CDC não são somados."
    }

@app.get("/pedidos/{order_id}")
def pedido(order_id: int):
    doc = db["orders_current"].find_one({"order_id": order_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Pedido não encontrado no stream processado")
    return doc

@app.get("/alertas/fraude")
def alertas_fraude(limite: int = 100):
    limite = max(1, min(limite, 500))
    docs = list(db["fraud_alerts"].find({}, {"_id": 0}).sort("created_at", DESCENDING).limit(limite))
    return {"total_retornado": len(docs), "alertas": docs}

@app.get("/eventos/brutos")
def eventos_brutos(limite: int = 20):
    """Endpoint auxiliar para demonstrar persistência de eventos CDC brutos."""
    limite = max(1, min(limite, 100))
    docs = list(db["raw_events"].find({}, {"_id": 0}).sort("received_at", DESCENDING).limit(limite))
    return {"total_retornado": len(docs), "eventos": docs}
