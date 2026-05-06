import os
import time
import pika
import threading
from datetime import datetime, timezone
from pika.exceptions import AMQPConnectionError, StreamLostError

from elasticapm import Client
from elasticsearch import Elasticsearch
from elasticapm.traces import capture_span
from elasticapm.instrumentation.control import instrument
instrument()

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
ELASTIC_URL       = os.getenv("ELASTIC_URL", "http://localhost:9200")
RBQ_ELASTIC_INDEX = os.getenv("RBQ_ELASTIC_INDEX", "rabbitmq-logs")
TIME_RETRY        = os.getenv("TIME_RETRY", 5)


class Consumer:

    def __init__(self):
        self.apm_client = Client({
            "SERVICE_NAME": "rabbitmq-worker",
            "SERVER_URL": "http://localhost:8200",
            "ENVIRONMENT": "local"
        })
        self.create_queues()
        self.es = Elasticsearch(ELASTIC_URL)

    def send_log(self, status, msg, retry, processing_time):
        doc = {
            "service": "worker",
            "status": status,
            "retry": retry,
            "msg": msg,
            "processing_time_ms": processing_time,
            "@timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.es.index(index=RBQ_ELASTIC_INDEX, document=doc)

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
        start = time.time()
        try:

            print(f"Processing try {retries}")
            with capture_span("process_message", span_type="worker"):
                time.sleep(2)
                if b"fail" in body:
                    raise Exception("Erro simulado")

            self.send_log(
                status="SUCCESS",
                msg = "Finish",
                retry=0,
                processing_time=int((time.time() - start) * 1000)
            )
            self.apm_client.end_transaction("rabbitmq.consume", "success")
            ch.basic_ack(method.delivery_tag)

        except Exception as e:
            print(f"Error: {e}")
            self.apm_client.capture_exception()
            self.apm_client.end_transaction("rabbitmq.consume", "error")
            self.send_log(
                status="ERROR",
                msg = f"Error: {e}",
                retry=retries,
                processing_time=int((time.time() - start) * 1000)
            )
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
        print("Starting consumer with APM")
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