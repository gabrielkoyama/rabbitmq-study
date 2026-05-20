import os
import pika
import json
from dotenv import load_dotenv
load_dotenv()

RABBITMQ_HOST     = os.getenv("RABBITMQ_HOST")
RABBITMQ_USER     = os.getenv("RABBITMQ_USER")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD")
RABBITMQ_QUEUE    = os.getenv("RABBITMQ_QUEUE")

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
    body=json.dumps({"fail": "test"})
)

