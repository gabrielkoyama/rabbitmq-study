import time
import pika
import threading
from pika.exceptions import AMQPConnectionError, StreamLostError

RABBITMQ_HOST="localhost"
RABBITMQ_USER="guest"
RABBITMQ_PASSWORD="guest"
RABBITMQ_QUEUE="teste_queue"

RABBITMQ_QUEUE = "main_queue"
RETRY_QUEUE = "retry_queue"
DLQ_QUEUE = "dlq_queue"

TIMEWAIT = 30
MAX_RETRIES=3

# from elasticapm import Client
# from elasticapm.instrumentation.control import instrument

# apm_client = Client({
#     "SERVICE_NAME": "rabbitmq-worker",
#     "SERVER_URL": "http://localhost:8200",
# })

# instrument()

from datetime import datetime, timezone
from elasticsearch import Elasticsearch
es = Elasticsearch("http://localhost:9200")
def send_log(status, retry, processing_time):
    doc = {
        "service": "worker",
        "status": status,
        "retry": retry,
        "processing_time_ms": processing_time,
        # "timestamp": time.time()
        "@timestamp": datetime.now(timezone.utc).isoformat()

    }
    es.index(index="rabbitmq-logs", document=doc)



class Consumer:

    def _callback(self, ch, method, properties, body):
        start = time.time()

        headers = properties.headers or {}
        retries = headers.get("x-retry", 0)

        try:
            print(f"Processando tentativa {retries}")
            time.sleep(2)

            # apm_client.end_transaction("process_message", "success")

            send_log(
                status="success",
                retry=0,
                processing_time=int((time.time() - start) * 1000)
            )

            if b"fail" in body:
                raise Exception("Erro simulado")

            ch.basic_ack(method.delivery_tag)
            print("OK")

        except Exception as e:
            send_log(
                status="error",
                retry=retries,
                processing_time=int((time.time() - start) * 1000)
            )
            print(f"Erro: {e}")
            # apm_client.end_transaction("process_message", "error")


            if retries < MAX_RETRIES:
                headers["x-retry"] = retries + 1

                ch.basic_publish(
                    exchange="",
                    routing_key=RETRY_QUEUE,
                    body=body,
                    properties=pika.BasicProperties(headers=headers)
                )
                print("Enviado para retry")

            else:
                ch.basic_publish(
                    exchange="",
                    routing_key=DLQ_QUEUE,
                    body=body
                )

                print("Enviado para DLQ")

            ch.basic_ack(method.delivery_tag)


    def _connection(self):
        connection_parameters = pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            credentials=pika.PlainCredentials(
            username=RABBITMQ_USER,
                password=RABBITMQ_PASSWORD
            ),
            heartbeat=300
        )
        channel = pika.BlockingConnection(connection_parameters).channel()
        print("Starting consumer.")
        return channel

    def run(self):
        while True:
            try:
                _channel = self._connection()
                _channel.basic_consume(
                        queue=RABBITMQ_QUEUE,
                        auto_ack=False,
                        on_message_callback=self._callback
                    )
                _channel.start_consuming()
            except (AMQPConnectionError, StreamLostError, EOFError) as e:
                print(f"Conexão caiu: {e}")
                print("Tentando reconectar em 5s...")
                time.sleep(5)   


t = threading.Thread(target=Consumer().run)
t.start()
