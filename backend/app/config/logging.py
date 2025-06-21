"""
Centralized logging configuration for Open Karaoke Studio backend.
Provides file-based persistent logging with rotation and proper formatting.
"""

import logging
import os
from pathlib import Path
from typing import Any

from .base import BaseConfig


class LoggingConfig:
    """Centralized logging configuration"""

    def __init__(self, config: BaseConfig):
        self.config = config
        self.log_dir = Path(config.BASE_DIR) / "backend" / "logs"
        self.log_dir.mkdir(exist_ok=True)

    def setup_logging(self, environment: str = "development") -> dict[str, Any]:
        """Setup logging configuration based on environment"""

        # Base log configuration
        log_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "detailed": {
                    "format": (
                        "%(asctime)s - %(name)s - %(levelname)s - "
                        "%(filename)s:%(lineno)d - %(funcName)s - %(message)s"
                    ),
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
                "simple": {
                    "format": "%(asctime)s - %(levelname)s - %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
                "celery": {
                    "format": (
                        "%(asctime)s - %(name)s - %(levelname)s - "
                        "%(funcName)s - %(message)s"
                    ),
                    "datefmt": "%Y-%m-%d %H:%M:%S",
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
                },
                "file_error": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "ERROR",
                    "formatter": "detailed",
                    "filename": str(self.log_dir / "errors.log"),
                    "maxBytes": 10485760,
                    "backupCount": 5,
                    "encoding": "utf8",
                },
                "file_celery": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "INFO",
                    "formatter": "celery",
                    "filename": str(self.log_dir / "celery.log"),
                    "maxBytes": 10485760,
                    "backupCount": 5,
                    "encoding": "utf8",
                },
                "file_jobs": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "INFO",
                    "formatter": "detailed",
                    "filename": str(self.log_dir / "jobs.log"),
                    "maxBytes": 10485760,
                    "backupCount": 5,
                    "encoding": "utf8",
                },
                "file_youtube": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "INFO",
                    "formatter": "detailed",
                    "filename": str(self.log_dir / "youtube.log"),
                    "maxBytes": 5242880,  # 5MB
                    "backupCount": 3,
                    "encoding": "utf8",
                },
                "file_audio": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "INFO",
                    "formatter": "detailed",
                    "filename": str(self.log_dir / "audio_processing.log"),
                    "maxBytes": 10485760,
                    "backupCount": 5,
                    "encoding": "utf8",
                },
            },
            "loggers": {
                # Root logger
                "": {
                    "level": "INFO",
                    "handlers": ["console", "file_info", "file_error"],
                    "propagate": False,
                },
                # App-specific loggers
                "app": {
                    "level": "INFO",
                    "handlers": ["console", "file_info", "file_error"],
                    "propagate": False,
                },
                "app.jobs": {
                    "level": "INFO",
                    "handlers": ["console", "file_jobs", "file_error"],
                    "propagate": False,
                },
                "app.services.youtube_service": {
                    "level": "INFO",
                    "handlers": ["console", "file_youtube", "file_error"],
                    "propagate": False,
                },
                "app.services.audio": {
                    "level": "INFO",
                    "handlers": ["console", "file_audio", "file_error"],
                    "propagate": False,
                },
                # Celery loggers
                "celery": {
                    "level": "INFO",
                    "handlers": ["console", "file_celery", "file_error"],
                    "propagate": False,
                },
                "celery.task": {
                    "level": "INFO",
                    "handlers": ["console", "file_celery", "file_error"],
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
            },
        }

        # Environment-specific adjustments
        if environment == "development":
            log_config["loggers"][""]["level"] = "DEBUG"
            log_config["handlers"]["console"]["level"] = "DEBUG"
            log_config["loggers"]["app"]["level"] = "DEBUG"

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


def setup_logging(config: BaseConfig = None):
    """Initialize logging configuration"""
    if config is None:
        from . import get_config

        config = get_config()

    logging_config = LoggingConfig(config)
    log_dict_config = logging_config.setup_logging(
        environment=os.getenv("FLASK_ENV", "development")
    )

    # Apply the logging configuration
    import logging.config as logging_config_module

    logging_config_module.dictConfig(log_dict_config)

    # Log that logging has been initialized
    log = logging.getLogger(__name__)
    log.info(
        "Logging initialized - Environment: %s", os.getenv("FLASK_ENV", "development")
    )
    log.info("Log directory: %s", logging_config.log_dir)

    return logging_config


def get_structured_logger(name: str, extra_fields: dict[str, Any] = None):
    """Get a logger with structured logging support"""
    logger = logging.getLogger(name)

    if extra_fields:
        # Create a LoggerAdapter to add extra fields
        return logging.LoggerAdapter(logger, extra_fields)

    return logger
