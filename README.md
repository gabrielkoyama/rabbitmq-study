# Basic Publisher and Consumer RabbitMQ

## Init container RabbitMQ

```
    docker compose up 
```
Access RabbitMQ url: http://localhost:15672/

## Basic execution

- python basic_consumer.py -- start listening messages and printing them

- python basic_publisher.py -- publish message text