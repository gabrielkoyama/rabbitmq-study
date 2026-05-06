# TODO 
 

- Observability and tracebility

## Backlog 

### Observability 
- Observability with Elastic 
- Start Elastic container + Kibana 
- integrate logs on consumer 
- Create structure logs 

Create basic queries: 
- Error per min 
- Average time of processing 
- Amount of retries Basic Metrics: 
- Count messages processed 
- Count of failed 
- Count of messages on queue 
- Average time of processing 

### Simulate Infrastructure clusters 
Create docker-compose with:
- rabbitmq
- 2+ workers
 - Run multiple workers
 - Test parallel consumption
 - Kill one worker and observe behavior

### KAFKA Topics vs Queues
- Study: Topics vs Queues
- Create simple Kafka producer/consumer
- Compare with RabbitMQ
- Document in README