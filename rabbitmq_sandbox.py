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


class Consumer:

    def _callback(self, ch, method, properties, body):
        headers = properties.headers or {}
        retries = headers.get("x-retry", 0)

        try:
            print(f"Processando tentativa {retries}")
            time.sleep(10)

            if b"fail" in body:
                raise Exception("Erro simulado")

            ch.basic_ack(method.delivery_tag)
            print("OK")

        except Exception as e:
            print(f"Erro: {e}")

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
                        auto_ack=True,
                        on_message_callback=self._callback
                    )
                _channel.start_consuming()
            except (AMQPConnectionError, StreamLostError, EOFError) as e:
                print(f"Conexão caiu: {e}")
                print("Tentando reconectar em 5s...")
                time.sleep(5)   


t = threading.Thread(target=Consumer().run)
t.start()
