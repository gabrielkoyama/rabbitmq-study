# My dev log


## Threads and Concurrent futures python

```
import threading

def task(): print("Starting task")

t = threading.Thread(target=task)
t.start()

```

Library threading is used for one or a few threads. Threads that you want to manage manually.

If I want to create 3 threads:
```
def task(i): 
    print(f"Starting task {i}")
    time.sleep(2)  # mock processing
    print(f"Task {i} done")

n_threads = 3
for i in range(n_threads):
    t = threading.Thread(target=task)
    t.start()
```

Use of t.join(): Its used for wait until threads are finish to continue running the code. If you are running multiple threads in for, you may add them to a list and then use t.join for all of them to wait.

```
n_threads = 3
threads=[]
for i in range(n_threads):
    t = threading.Thread(target=task, args=(i,))
    threads.append(t)
    t.start()

for t in threads:
    t.join()

print("All threads are done, i can continue now")

Out: 
    $ Starting task 0
    $ Starting task 1
    $ Starting task 2
    $ Task 2 done
    $ Task 0 done
    $ Task 1 done
    $ All threads are done, i can continue now
```

### Difference between library threading and concurrent.future

The differnce is that thread is more for a few manually threads and ThreadPoolExecutor creates a Pool of reusable threads and simplify the management.

```
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=3) as executor:
    futuros = [executor.submit(task, i) for i in range(5)]
    results = [f.result() for f in futuros]

print("Results:", results)
```

The parameter ```daemon``` indicates if the thread is dameon or not, default is ```False ``` and this makes the thread finish even if the process are done. If ```daemon=True```, when the main process are done the thread are killed.

Example:
```
def task(): 
    print("starting thread")
    time.sleep(5)
    print("Thread finished")

t = threading.Thread(target=tarefa, daemon=False)
t.start()
print("Main process finish")

Out:
    $ starting thread
    $ Main process finish
    $ Thread finished
```

If Daemon=True, thread never responds.
```
Out:
    $ starting thread
    $ Main process finish
```

## RabbitMQ Retry and args

So, I have a basic RabbitMQ connection and I want to implement connection retry and see some examples of the arguments ```heartbeat``` and ```blocked_connection_timeout```.


>Important reminders RabbiMQ: It needs to have a ack (acknowledge) to confirm that the message was delivery succesfully. For test, its ok to set ```auto_ack=True```, but for heavy process its not. Use ```auto_ack=False``` and treat this on callback, giving **ACK** if the process sucefully finish ou on Exception use **NACK** to handle error messages. **NACK** default retrive back to queue and try again, if you don't treat that it will be in a **LOOP**. 

```
class Consumer:

    def _callback(self, ch, method, properties, body):
        print(f"Stating callback, waiting {TIMEWAIT}s")
        time.sleep(TIMEWAIT)
        print(body)
        print("Finish")

    def run(self):
        connection_parameters = pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            credentials=pika.PlainCredentials(
            username=RABBITMQ_USER,
                password=RABBITMQ_PASSWORD
            ),
            heartbeat=300,
            blocked_connection_timeout=5
        )

        channel = pika.BlockingConnection(connection_parameters).channel()
        channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
        channel.basic_consume(
            queue=RABBITMQ_QUEUE,
            auto_ack=True,
            on_message_callback=self._callback
        )
        print("Starting consumer.")
        channel.start_consuming()
```

Putting on a thread:
```
t = threading.Thread(target=Consumer().run)
t.start()
```


If I use ```heatbeat=5``` and ```TIMEWAIT=10``` on my callback, RabbitMQ will not finish connection because there is a tolerance of 2x. So, if I set ```TIMEWAIT=30```, RabbitMQ will kill the connection.
```
raise self._closed_result.value.error
pika.exceptions.StreamLostError: Transport indicated EOF
```

The argument ```blocked_connection_timeout``` is not related to timeout callback, so if I put ```heartbeat=300```, ```TIMEWAIT=30``` and ```blocked_connection_timeout=5``` it should be fine. Because ```blocked_connection_timeout``` only will terminated the session if RabbitMQ is in flow control (high memony, full disk).


To keep connection after raise EOF, implement a simple retry connection.

```
TIMEWAIT = 30

def _consume(self):
    connection_parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        credentials=pika.PlainCredentials(
        username=RABBITMQ_USER,
            password=RABBITMQ_PASSWORD
        ),
        heartbeat=1
    )

    channel = pika.BlockingConnection(connection_parameters).channel()
    channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
    channel.basic_consume(
        queue=RABBITMQ_QUEUE,
        auto_ack=True,
        on_message_callback=self._callback
    )
    print("Starting consumer.")
    channel.start_consuming()
    
def run(self):
    while True:
        try:
            self._consume()
        except (AMQPConnectionError, StreamLostError, EOFError) as e:
            print(f"Connection down: {e}")
            print("Trying to reconnect in 5s...")
            time.sleep(5)   
```

### Best pratices: Retry and DLQ

```
Main Queue → Consumer
     ↓ fail
Retry Queue (with delay)
     ↓ fail X times
DLQ
```

Important: if you publish to a non exist queue, RabbitMQ won't give any error, so you have to guarantee that the queues exists.

If you are trying to create a queue that already exist with another settings it will appear this error:
```
pika.exceptions.ChannelClosedByBroker: (406, "PRECONDITION_FAILED - inequivalent arg 'x-dead-letter-exchange' for queue 'main_queue' in vhost '/': received the value '' of type 'longstr' but current is none")
```

So I modify a little bit Consumer to separete connection to actual start consuming the QUEUE.

```
def _connection(self):
    connection_parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        credentials=pika.PlainCredentials(
        username=RABBITMQ_USER,
            password=RABBITMQ_PASSWORD
        ),
        heartbeat=1
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
                    on_message_callback=self.__callback
                )
            _channel.start_consuming()
        except (AMQPConnectionError, StreamLostError, EOFError) as e:
            print(f"Conexão caiu: {e}")
            print("Tentando reconectar em 5s...")
            time.sleep(5)   
```

Creating the QUEUES

```
channel = Consumer()._connection()
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
```

Now we can add that on callback, I will exaplain in parts.
```
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
```