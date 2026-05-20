import os
import time
import pika
import threading
from pika.exceptions import AMQPConnectionError, StreamLostError

from dotenv import load_dotenv
load_dotenv()

RABBITMQ_HOST     = os.getenv("RABBITMQ_HOST")
RABBITMQ_USER     = os.getenv("RABBITMQ_USER")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD")
RABBITMQ_QUEUE    = os.getenv("RABBITMQ_QUEUE")
RETRY_QUEUE       = os.getenv("RETRY_QUEUE")
DLQ_QUEUE         = os.getenv("DLQ_QUEUE")
HEARTBEAT         = os.getenv("HEARTBEAT", 300)
MAX_RETRIES       = int(os.getenv("MAX_RETRIES", 3))
TIME_RETRY        = os.getenv("TIME_RETRY", 5)

class Consumer:

    def __init__(self):
        self.create_queues()

    def create_queues(self):
        channel = self._connection()
        print("Creating DLQ Queue")
        channel.queue_declare(queue=DLQ_QUEUE, durable=True)

        print("Creating DLQ Retry")
        channel.queue_declare(
            queue=RETRY_QUEUE,
            durable=True,
            arguments={
                "x-message-ttl": 5000,
                "x-dead-letter-exchange": "",
                "x-dead-letter-routing-key": RABBITMQ_QUEUE
            }
        )

        print("Creating DLQ Main")
        channel.queue_declare(
            queue=RABBITMQ_QUEUE,
            durable=True,
            arguments={
                "x-dead-letter-exchange": "",
                "x-dead-letter-routing-key": DLQ_QUEUE
            }
        )
        
    def _callback(self, ch, method, properties, body):
        headers = properties.headers or {}
        retries = headers.get("x-retry", 0)

        try:
            print(f"Processing try {retries}")
            if b"fail" in body:
                raise Exception("Simulated Error")
            ch.basic_ack(method.delivery_tag)
            print("Finish")

        except Exception as e:
            print(f"Error: {e}")
            if retries < MAX_RETRIES:
                headers["x-retry"] = retries + 1
                ch.basic_publish(
                    exchange="",
                    routing_key=RETRY_QUEUE,
                    body=body,
                    properties=pika.BasicProperties(headers=headers)
                )
                print("Sending to retry queue")
            else:
                ch.basic_publish(
                    exchange="",
                    routing_key=DLQ_QUEUE,
                    body=body
                )
                print("Sending to DLQ")
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
        print("Starting consumer with retry-dlq")
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
                print(f"Conection failed: {e}")
                print("Trying to reconect 5s...")
                time.sleep(TIME_RETRY)   


Consumer().run()

# t = threading.Thread(target=Consumer().run)
# t.start()