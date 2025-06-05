"""
Open Karaoke Studio Backend

A Flask application for managing and processing karaoke tracks.
"""

from flask import Flask
from flask_cors import CORS

from .config import get_config
from .api import register_blueprints
from .tasks import init_celery
from .db import Base, engine
from .websockets import init_socketio


def create_app(config_class=None):
    """
    Application factory function to create and configure the Flask app.

    Args:
        config_class: Configuration class to use for app configuration.
                     If None, will be determined from environment.

    Returns:
        Configured Flask application instance
    """
    if config_class is None:
        config_class = get_config()
        
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Configure CORS with environment-specific origins
    CORS(
        app,
        origins=config_class.CORS_ORIGINS,
        supports_credentials=True,
    )

    # Initialize Celery
    init_celery(app)

    # Initialize WebSocket
    init_socketio(app)

    # Ensure database schema is up to date
    from .db.database import ensure_db_schema
    ensure_db_schema()

    # Register all blueprints
    register_blueprints(app)

    return app
