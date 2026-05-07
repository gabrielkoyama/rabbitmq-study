import pika

connection = pika.BlockingConnection(pika.ConnectionParameters(host="localhost"))
channel = connection.channel()

for i in range(10):
    channel.basic_publish(
        exchange="",
        routing_key="main_queue",
        body=f"msg {i}"
    )

print("Mensagens enviadas")