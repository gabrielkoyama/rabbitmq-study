import time
import pika
import threading
from pika.exceptions import AMQPConnectionError, StreamLostError
from rabbitmq_sandbox import Consumer

RABBITMQ_HOST="localhost"
RABBITMQ_USER="guest"
RABBITMQ_PASSWORD="guest"
RABBITMQ_QUEUE="teste_queue"

RABBITMQ_QUEUE = "main_queue"
RETRY_QUEUE = "retry_queue"
DLQ_QUEUE = "dlq_queue"

def create_queues():
    connection_parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        credentials=pika.PlainCredentials(
        username=RABBITMQ_USER,
            password=RABBITMQ_PASSWORD
        )
    )
    channel = pika.BlockingConnection(connection_parameters).channel()

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
# create_queues()


import time
from elasticsearch import Elasticsearch
es = Elasticsearch("http://localhost:9200")


def send_log(status, retry, processing_time):
    doc = {
        "service": "worker",
        "status": status,
        "retry": retry,
        "processing_time_ms": processing_time,
        "timestamp": time.time()
    }
    es.index(index="rabbitmq-logs", document=doc)
# send_log("WARNING", "1", time.time())



t = threading.Thread(target=Consumer().run)
t.start()
