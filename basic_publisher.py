import pika
import json

RABBITMQ_HOST="localhost"
RABBITMQ_USER="guest"
RABBITMQ_PASSWORD="guest"
RABBITMQ_QUEUE="teste_queue"


connection_parameters = pika.ConnectionParameters(
    host=RABBITMQ_HOST,
    credentials=pika.PlainCredentials(
        username=RABBITMQ_USER,
        password=RABBITMQ_PASSWORD
    )
)

channel = pika.BlockingConnection(connection_parameters).channel()
channel.basic_publish(
    exchange="",
    routing_key=RABBITMQ_QUEUE,
    body=json.dumps({"teste": "ok"})
)

