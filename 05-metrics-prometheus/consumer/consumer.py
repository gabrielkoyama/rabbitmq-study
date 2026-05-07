import pika

import time
import os
from prometheus_client import Counter, Histogram, start_http_server

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
QUEUE = "main_queue"

# métricas
# messages_processed = Counter(
#     "messages_processed_total",
#     "Total de mensagens processadas"
# )

messages_processed = Counter(
    "messages_processed_total",
    "Total de mensagens processadas",
    ["status"]
)

errors = Counter(
    "message_errors_total",
    "Total de erros"
)

processing_time = Histogram(
    "message_processing_seconds",
    "Tempo de processamento"
)

def callback(ch, method, properties, body):
    start = time.time()
    try:
        with processing_time.time():
            print(f"Processing: {body}")
            time.sleep(2)

            if b"fail" in body:
                raise Exception("Erro simulado")

        # messages_processed.inc()
        messages_processed.labels(status="success").inc()
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print(f"Erro: {e}")
        messages_processed.labels(status="success").inc()
        ch.basic_ack(delivery_tag=method.delivery_tag)


def connect():
    while True:
        try:
            print(f"Tentando conectar em: {RABBITMQ_HOST}")

            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=RABBITMQ_HOST,
                    heartbeat=300
                )
            )

            print("Conectado ao RabbitMQ!")
            return connection

        except Exception as e:
            print(f"Erro ao conectar: {e}")
            print("RabbitMQ não pronto, tentando novamente em 5s...")
            time.sleep(5)

def main():
    start_http_server(8000)

    connection = connect()
    channel = connection.channel()

    channel.queue_declare(queue=QUEUE)
    channel.basic_qos(prefetch_count=1)

    channel.basic_consume(
        queue=QUEUE,
        on_message_callback=callback,
        auto_ack=False
    )

    print("Consumer started...")
    channel.start_consuming()


if __name__ == "__main__":
    main()