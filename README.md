# RabbitMQ Study

Projeto prático evoluindo de uso básico até observabilidade e tracing.

## Etapas

- 01-basic → publish/consume
- 02-retry-dlq → tratamento de falhas
- 03-observability → logs + elastic
- 04-apm-tracing → tracing distribuído

## Stack

- RabbitMQ
- Python (pika)
- Elasticsearch + Kibana
- OpenTelemetry (ou Elastic APM)

## Como rodar

cd 01-basic
docker-compose up