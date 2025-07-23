"""
Centralized logging configuration for Open Karaoke Studio backend.
Provides file-based persistent logging with rotation and proper formatting.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo

from app.config import get_config

from .base import BaseConfig

try:
    import colorlog
    COLORLOG_AVAILABLE = True
except ImportError:
    COLORLOG_AVAILABLE = False


class TimezoneFormatter(logging.Formatter):
    """Custom formatter that converts timestamps to a specified timezone."""

    def __init__(self, fmt=None, datefmt=None, timezone="UTC"):
        super().__init__(fmt, datefmt)
        self.timezone = ZoneInfo(timezone)

    def formatTime(self, record, datefmt=None):
        """Convert the timestamp to the specified timezone."""
        dt = datetime.fromtimestamp(record.created, tz=self.timezone)
        if datefmt:
            return dt.strftime(datefmt)
        else:
            return dt.strftime("%Y-%m-%d %H:%M:%S %Z")


class LoggingConfig:
    """Centralized logging configuration"""

    def __init__(self, config: BaseConfig):
        self.config = config
        self.log_dir = Path(config.BASE_DIR) / "backend" / "logs"
        self.log_dir.mkdir(exist_ok=True)
        self.timezone = getattr(config, "TIMEZONE", "America/Toronto")

    def setup_logging(self, environment: str = "development") -> dict[str, Any]:
        """Setup logging configuration based on environment"""

        # Base log configuration
        log_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "detailed": {
                    "()": TimezoneFormatter,
                    "format": (
                        "%(asctime)s - %(name)s - %(levelname)s - "
                        "%(filename)s:%(lineno)d - %(funcName)s - %(message)s"
                    ),
                    "datefmt": "%Y-%m-%d %H:%M:%S %Z",
                    "timezone": self.timezone,
                },
                "simple": (
                    {
                        "()": colorlog.ColoredFormatter,
                        "fmt": ("%(asctime)s %(log_color)s%(levelname)-8s%(reset)s %(white)s%(message)s"
                        ),
                        "datefmt": "%H:%M:%S",
                        "log_colors": {
                            "DEBUG": "cyan",
                            "INFO": "green",
                            "WARNING": "yellow",
                            "ERROR": "red",
                            "CRITICAL": "bold_red,bg_white",
                        },
                        "secondary_log_colors": {},
                        "style": "%",
                    } if COLORLOG_AVAILABLE else {
                        "()": TimezoneFormatter,
                        "format": "%(asctime)s - %(levelname)s - %(message)s",
                        "datefmt": "%Y-%m-%d %H:%M:%S %Z",
                        "timezone": self.timezone,
                    }
                ),
                "celery": {
                    "()": TimezoneFormatter,
                    "format": (
                        "%(asctime)s - %(name)s - %(levelname)s - "
                        "%(funcName)s - %(message)s"
                    ),
                    "datefmt": "%Y-%m-%d %H:%M:%S %Z",
                    "timezone": self.timezone,
                },
                "json": {
                    "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                    "format": (
                        "%(asctime)s %(name)s %(levelname)s %(filename)s "
                        "%(lineno)d %(funcName)s %(message)s"
                    ),
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": "INFO",
                    "formatter": "simple",
                    "stream": "ext://sys.stdout",
                },
                "file_info": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "INFO",
                    "formatter": "detailed",
                    "filename": str(self.log_dir / "app.log"),
                    "maxBytes": 10485760,
                    "backupCount": 5,
                    "encoding": "utf8",
                },                "file_celery": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "INFO",
                    "formatter": "celery",
                    "filename": str(self.log_dir / "celery.log"),
                    "maxBytes": 10485760,
                    "backupCount": 5,
                    "encoding": "utf8",
                },            },
            "loggers": {
                # Root logger
                "": {
                    "level": "INFO",
                    "handlers": ["console","file_info", ],
                    "propagate": False,
                },
                # App-specific loggers
                "app": {
                    "level": "INFO",
                    "handlers": ["console","file_info", ],
                    "propagate": False,
                },
                # Celery loggers
                "celery": {
                    "level": "INFO",
                    "handlers": ["console", "file_celery",],
                    "propagate": False,
                },
                "celery.task": {
                    "level": "INFO",
                    "handlers": ["console", "file_celery",],
                    "propagate": False,
                },
                # Third-party loggers (reduce noise)
                "urllib3": {
                    "level": "WARNING",
                    "handlers": ["console"],
                    "propagate": False,
                },
                "requests": {
                    "level": "WARNING",
                    "handlers": ["console"],
                    "propagate": False,
                },
                "werkzeug": {
                    "level": "WARNING",
                    "handlers": ["console"],
                    "propagate": False,
                },
                "yt_dlp": {
                    "level": "WARNING",
                    "handlers": ["console"],
                    "propagate": False,
                },
                "multiprocessing": {
                    "level": "WARNING",
                    "handlers": ["console"],
                    "propagate": False,
                },
            },
        }

        # Environment-specific adjustments
        if environment == "development":
            # Development: INFO level for console, DEBUG for files only
            log_config["loggers"][""]["level"] = "INFO"
            log_config["handlers"]["console"]["level"] = "INFO"
            log_config["loggers"]["app"]["level"] = "INFO"

            # Make console output less verbose - only show important messages
            log_config["handlers"]["console"]["formatter"] = "simple"

        elif environment == "production":
            # Production: Only log to files, reduce console logging
            log_config["handlers"]["console"]["level"] = "WARNING"
            # Add JSON logging for production monitoring
            log_config["handlers"]["file_json"] = {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "json",
                "filename": str(self.log_dir / "app.json"),
                "maxBytes": 10485760,
                "backupCount": 10,
                "encoding": "utf8",
            }
            log_config["loggers"]["app"]["handlers"].append("file_json")

        elif environment == "testing":
            # Testing: Minimal logging
            log_config["loggers"][""]["level"] = "WARNING"
            log_config["handlers"]["console"]["level"] = "WARNING"

        return log_config

    def configure_celery_logging(self) -> dict[str, Any]:
        """Configure Celery-specific logging"""
        # Set timezone for Celery logging
        os.environ.setdefault("TZ", self.timezone)

        return {
            "task_always_eager": False,
            "worker_log_format": (
                "[%(asctime)s: %(levelname)s/%(processName)s] %(name)s: %(message)s"
            ),
            "worker_task_log_format": (
                "[%(asctime)s: %(levelname)s/%(processName)s] %(message)s"
            ),
            "worker_log_color": False,  # Disable color in files
            "worker_redirect_stdouts": True,
            "worker_redirect_stdouts_level": "INFO",
            "task_track_started": True,
            "task_send_sent_event": True,
            "worker_send_task_events": True,
            "worker_hijack_root_logger": False,  # Don't override our config
        }


# Module-level variable to track logging initialization
_logging_initialized = False


def setup_logging(config: BaseConfig):
    """Initialize logging configuration"""
    global _logging_initialized

    # Prevent duplicate logging setup
    if _logging_initialized:
        return LoggingConfig(config or get_config())

    if config is None:
        config = get_config()

    logging_config = LoggingConfig(config)
    log_dict_config = logging_config.setup_logging(
        environment=os.getenv("FLASK_ENV", "development")
    )

    # Apply the logging configuration
    import logging.config as logging_config_module

    logging_config_module.dictConfig(log_dict_config)

    # Mark logging as initialized
    _logging_initialized = True

    # Minimal logging initialization message
    log = logging.getLogger(__name__)
    log.debug("Logging configured for %s", os.getenv("FLASK_ENV", "development"))

    return logging_config


def get_structured_logger(name: str, extra_fields: Optional[dict[str, Any]] = None):
    """Get a logger with structured logging support"""
    logger = logging.getLogger(name)

    if extra_fields:
        # Create a LoggerAdapter to add extra fields
        return logging.LoggerAdapter(logger, extra_fields)

    return logger
