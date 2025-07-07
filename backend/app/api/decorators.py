# backend/app/api/decorators.py
"""
API decorators for common functionality
"""

import functools
import logging

from flask import request


def log_api_call(logger: logging.Logger):
    """Decorator to log API calls"""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger.info(
                "API call to %s: %s %s", func.__name__, request.method, request.path
            )
            try:
                result = func(*args, **kwargs)
                logger.info("API call to %s completed successfully", func.__name__)
                return result
            except Exception as e:
                logger.error("API call to %s failed: %s", func.__name__, e)
                raise

        return wrapper

    return decorator
