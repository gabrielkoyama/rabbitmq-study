# RabbitMQ Study - Step 5: Prometheus Metrics

Fifth step of this study focuses on collecting and exposing application metrics from the RabbitMQ consumer using **Prometheus**, with visualization through **Grafana**.

While Step 4 introduced APM tracing (latency, transactions, spans), this step adds a metrics-based observability layer: counters, gauges, and histograms that Prometheus scrapes on a fixed interval.

## Purpose

Understand how to instrument a message consumer and monitor messaging behavior with the Prometheus ecosystem:

- Expose metrics from the application (HTTP endpoint on port `8000`)
- Configure Prometheus to scrape those metrics
- Visualize time-series data in Grafana
- Complement APM tracing with quantitative, aggregatable metrics

## Architecture

```text
+-------------+      +----------------+      +------------------+      +-------------+
|  Publisher  | ---> |   RabbitMQ     | ---> |     Consumer     | ---> |  /metrics   |
| publisher.py|      |   main_queue   |      |  (prometheus-    |      |  :8000      |
+-------------+      +----------------+      |   client)        |      +------+------+
                                               +------------------+             |
                                                                                  | scrape (5s)
                                                                                  v
                                         +----------------+      +----------------+
                                         |   Prometheus   | ---> |    Grafana     |
                                         |     :9090      |      |     :3000      |
                                         +----------------+      +----------------+
```

The consumer runs inside Docker, exposes a `/metrics` endpoint via `prometheus_client`, and Prometheus scrapes it according to `prometheus.yml`. Grafana queries Prometheus as a data source for dashboards.

## Stack (this step)

| Service    | Port  | Role                                      |
|-----------|-------|-------------------------------------------|
| RabbitMQ  | 5672, 15672 | Broker + Management UI              |
| Consumer  | 8000  | Worker + Prometheus metrics exporter    |
| Prometheus| 9090  | Metrics collection and storage          |
| Grafana   | 3000  | Dashboards and visualization            |

## Metrics

The consumer defines the following Prometheus metrics:

| Metric | Type | Description |
|--------|------|-------------|
| `messages_processed_total` | Counter (`status` label) | Total messages processed (`success` / `error`) |
| `message_processing_seconds` | Histogram | Time spent processing each message |
| `rabbitmq_queue_messages` | Gauge | Message count in `main_queue` (read at startup) |
| `message_errors_total` | Counter | Defined for error tracking (not wired in callback yet) |

Instrumentation in the consumer:

```python
from prometheus_client import Counter, Histogram, start_http_server, Gauge

messages_processed = Counter(
    "messages_processed_total",
    "Total messages processed",
    ["status"]
)

processing_time = Histogram(
    "message_processing_seconds",
    "Tempo de processamento"
)

start_http_server(8000)
```

Processing duration is measured with the histogram context manager:

```python
with processing_time.time():
    print(f"Processing: {body}")
    time.sleep(2)
    if b"fail" in body:
        raise Exception("Erro simulado")
```

Prometheus scrape configuration (`prometheus.yml`):

```yaml
global:
  scrape_interval: 5s

scrape_configs:
  - job_name: "consumer"
    static_configs:
      - targets: ["consumer:8000"]
```

Inside Docker Compose, the target hostname `consumer` resolves to the consumer service. Prometheus scrapes every 5 seconds.

## Installation and Setup

Prerequisites:

- Docker
- Docker Compose
- Python 3.x (only if running `publisher.py` on the host)

1. Clone the repository (if you have not already):

   ```bash
   git clone https://github.com/gabrielkoyama/rabbitmq-study.git
   ```

2. Go to this step's directory:

   ```bash
   cd 05-metrics-prometheus
   ```

3. Start all services:

   ```bash
   docker compose up --build
   ```

   This starts RabbitMQ, the consumer (with metrics on port `8000`), Prometheus, and Grafana.

4. Verify services:

   - RabbitMQ Management UI: http://localhost:15672 (user/password: `guest`)
   - Prometheus UI: http://localhost:9090
   - Grafana: http://localhost:3000 (default login: `admin` / `admin`)
   - Consumer metrics: http://localhost:8000/metrics

## Test and Execution

### 1. Confirm the consumer is scraping

In Prometheus (http://localhost:9090), open **Status → Targets** and check that the `consumer` job is **UP**.

Example queries:

```promql
messages_processed_total
rate(message_processing_seconds_sum[1m])
histogram_quantile(0.95, rate(message_processing_seconds_bucket[5m]))
```

### 2. Publish messages

With the stack running, send messages from the host (RabbitMQ is exposed on `localhost:5672`):

```bash
cd 05-metrics-prometheus
python publisher.py
```

The publisher sends 5 messages to `main_queue`. The consumer simulates 2 seconds of processing per message.

To simulate a processing failure (same pattern as Step 2), publish a body containing `fail` (adjust `publisher.py` or use another client).

### 3. Configure Grafana

1. Open http://localhost:3000 and log in.
2. Add a data source: **Prometheus**, URL `http://prometheus:9090` (from inside the Grafana container).
3. Create a panel with a query such as `rate(messages_processed_total[1m])` or `message_processing_seconds_bucket`.

After traffic is generated, counters and histograms should appear in Prometheus and Grafana.

## Docker Compose overview

```yaml
services:
  rabbitmq:    # broker (management image)
  consumer:    # builds ./consumer, exposes :8000
  prometheus:  # mounts ./prometheus.yml
  grafana:     # depends on prometheus
```

The consumer receives `RABBITMQ_HOST=rabbitmq` via environment variable and retries the connection until RabbitMQ is ready.

## Relationship to previous steps

| Step | Focus |
|------|--------|
| 04-apm-tracing | Distributed tracing, transactions, spans (Elastic APM + Kibana) |
| **05-metrics-prometheus** | Time-series metrics (Prometheus + Grafana) |

APM answers *what happened in a request trace*; Prometheus answers *how much and how fast over time* (throughput, latency distribution, error counts). Both layers are useful together in production observability.

<!-- ## Next step

Possible extensions for a follow-up:

- Wire `message_errors_total` and fix error-path labeling on `messages_processed_total`
- Refresh `rabbitmq_queue_messages` periodically (or use RabbitMQ's Prometheus plugin)
- Add Grafana dashboard JSON and alert rules
- Correlate metrics with trace IDs from Step 4 -->

## References

- [RabbitMQ Official Documentation](https://www.rabbitmq.com/docs)
- [Pika Documentation](https://pika.readthedocs.io/en/stable/)
- [Prometheus Documentation](https://prometheus.io/docs/introduction/overview/)
- [prometheus_client (Python)](https://github.com/prometheus/client_python)
- [Grafana Documentation](https://grafana.com/docs/)
