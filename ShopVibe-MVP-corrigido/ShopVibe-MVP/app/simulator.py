import os
import random
import time
import psycopg

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://shopvibe:shopvibe_dev@localhost:5432/shopvibe"
)
INTERVALO = float(os.getenv("SIM_INTERVALO_SEGUNDOS", "2"))

# Cliente que "abusa": aparece em ~20% dos pedidos (cerca de 12 pedidos a cada 120 s),
# o que dispara o alerta de mais de 5 pedidos em 2 minutos.
CLIENTE_SUSPEITO = 999
PROB_SUSPEITO = 0.20
# Demais clientes: um grupo grande, para que cada um faça só ~1 pedido por janela de
# 120 s e NÃO dispare alerta. (Com poucos clientes, todos disparariam.)
CLIENTES_NORMAIS = range(101, 301)


def escolher_cliente() -> int:
    if random.random() < PROB_SUSPEITO:
        return CLIENTE_SUSPEITO
    return random.choice(CLIENTES_NORMAIS)


def rodar(conn):
    while True:
        customer_id = escolher_cliente()
        total = round(random.uniform(19.90, 399.90), 2)
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO orders (customer_id, total, status) VALUES (%s, %s, %s) RETURNING order_id",
                (customer_id, total, "created")
            )
            order_id = cur.fetchone()[0]
        conn.commit()
        print(f"Pedido criado: id={order_id}, cliente={customer_id}, total=R${total:.2f}", flush=True)
        time.sleep(INTERVALO)


def main():
    print("Simulador ShopVibe iniciado. CTRL+C para parar.", flush=True)
    # Se o PostgreSQL reiniciar ou a conexão cair, reconecta em vez de encerrar.
    while True:
        try:
            with psycopg.connect(DATABASE_URL) as conn:
                rodar(conn)
        except psycopg.Error as exc:
            print(f"Conexão com o PostgreSQL perdida ({exc}); nova tentativa em 5s...", flush=True)
            time.sleep(5)


if __name__ == "__main__":
    main()
