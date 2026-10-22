import os
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo(os.getenv("TZ", "America/Sao_Paulo"))

def today_key() -> str:
    return datetime.now(TZ).date().isoformat()

def parse_debezium_value(value):
    """Retorna o registro 'after' de um evento CDC Debezium, ignorando tombstones."""
    if value is None:
        return None
    import json
    event = json.loads(value.decode("utf-8"))
    if not isinstance(event, dict):
        return None
    payload = event.get("payload", event)
    if not isinstance(payload, dict):
        return None
    op = payload.get("op")
    after = payload.get("after")
    if op == "d" or after is None:
        return None
    return {"envelope": event, "row": after, "op": op}
