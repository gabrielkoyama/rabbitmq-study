import pika

RABBITMQ_HOST="localhost"
RABBITMQ_USER="guest"
RABBITMQ_PASSWORD="guest"
RABBITMQ_QUEUE="teste_queue"

def minha_callback(ch, method, properties, body):
    print(body)

connection_parameters = pika.ConnectionParameters(
    host=RABBITMQ_HOST,
    credentials=pika.PlainCredentials(
    username=RABBITMQ_USER,
        password=RABBITMQ_PASSWORD
    ),
    heartbeat=5
    # blocked_connection_timeout=3
)

channel = pika.BlockingConnection(connection_parameters).channel()
channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
channel.basic_consume(
    queue=RABBITMQ_QUEUE,
    auto_ack=True,
    on_message_callback=minha_callback
)
channel.start_consuming()


