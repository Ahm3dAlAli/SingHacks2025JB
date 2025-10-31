"""
Structured logging configuration for TAE service.
Provides JSON formatting for production and pretty printing for development.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
import json
from datetime import datetime

from app.config import settings


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)

        return json.dumps(log_data)


def setup_logging() -> logging.Logger:
    """
    Configure logging for the application.
    Returns the root logger configured with appropriate handlers.
    """
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "tae.log"

    # Get log level from settings
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Create root logger
    logger = logging.getLogger("tae")
    logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Console Handler (pretty print for development)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    if settings.is_development:
        # Use simple format for development
        console_format = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(console_format)
    else:
        # Use JSON format for production
        console_handler.setFormatter(JSONFormatter())

    logger.addHandler(console_handler)

    # File Handler (always JSON, with rotation)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"  # 10MB
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(JSONFormatter())
    logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    logger.info(
        "Logging initialized",
        extra={
            "extra_data": {"log_level": settings.LOG_LEVEL, "environment": settings.ENVIRONMENT}
        },
    )

    return logger


# Create global logger instance
logger = setup_logging()
