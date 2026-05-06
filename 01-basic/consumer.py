import os
import pika
from dotenv import load_dotenv
load_dotenv()

RABBITMQ_HOST     = os.getenv("RABBITMQ_HOST")
RABBITMQ_USER     = os.getenv("RABBITMQ_USER")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD")
RABBITMQ_QUEUE    = os.getenv("RABBITMQ_QUEUE")
HEARTBEAT         = os.getenv("HEARTBEAT", 300)

def minha_callback(ch, method, properties, body):
    print(body)

connection_parameters = pika.ConnectionParameters(
    host=RABBITMQ_HOST,
    credentials=pika.PlainCredentials(
    username=RABBITMQ_USER,
        password=RABBITMQ_PASSWORD
    ),
    heartbeat=HEARTBEAT
)

channel = pika.BlockingConnection(connection_parameters).channel()
channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
channel.basic_consume(
    queue=RABBITMQ_QUEUE,
    auto_ack=True,
    on_message_callback=minha_callback
)
channel.start_consuming()


