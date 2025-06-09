"""
Configuration management for Open Karaoke Studio backend.

This module provides environment-based configuration loading.
"""

import os
from .base import BaseConfig
from .development import DevelopmentConfig
from .production import ProductionConfig
from .testing import TestingConfig

config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
}

def get_config():
    """
    Get the appropriate configuration class based on the FLASK_ENV environment variable.
    
    Returns:
        Configuration class instance for the current environment
    """
    env = os.getenv('FLASK_ENV', 'development')
    config_class = config_map.get(env, DevelopmentConfig)
    return config_class()

# For backwards compatibility, export commonly used config
Config = get_config()
