"""
Logging utility module.
Provides structured logging for Lambda functions.
"""
import logging
import json
import sys
from typing import Any, Dict, Optional
from functools import lru_cache

from .config import get_config


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add extra fields if present
        if hasattr(record, "extra_data"):
            log_data["data"] = record.extra_data
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, default=str)


@lru_cache(maxsize=10)
def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance."""
    config = get_config()
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, config.log_level, logging.INFO))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Add JSON handler for production
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    
    return logger


def log_request(logger: logging.Logger, event: Dict[str, Any]) -> None:
    """Log incoming request details."""
    logger.info(
        "Incoming request",
        extra={
            "extra_data": {
                "path": event.get("rawPath", event.get("path", "unknown")),
                "method": event.get("requestContext", {}).get("http", {}).get("method", "unknown"),
                "query": event.get("queryStringParameters", {}),
            }
        }
    )


def log_response(logger: logging.Logger, status_code: int, duration_ms: Optional[float] = None) -> None:
    """Log outgoing response details."""
    data: Dict[str, Any] = {"status_code": status_code}
    if duration_ms is not None:
        data["duration_ms"] = round(duration_ms, 2)
    
    logger.info("Outgoing response", extra={"extra_data": data})
