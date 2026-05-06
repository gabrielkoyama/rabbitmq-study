import logging
import sys
import json

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "@timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "log.level": record.levelname.lower(),
            "message": record.getMessage(),
            "service.name": "rabbitmq-worker",
            "logger": record.name,
        }

        if record.exc_info:
            log_record["error"] = {
                "message": record.getMessage()
            }

        return json.dumps(log_record)

logger = logging.getLogger("rabbitmq-worker")
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())

logger.addHandler(handler)