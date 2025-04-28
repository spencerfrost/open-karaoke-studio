"""
Open Karaoke Studio Backend

A Flask application for managing and processing karaoke tracks.
"""
import os
from flask import Flask
from flask_cors import CORS

# Import the config directly using get_config function
from .config import get_config
from .api import register_blueprints
from .tasks import init_celery
from .db import Base, engine
from .websockets import init_socketio

# Get the configuration based on environment
Config = get_config()

def create_app(config_class=Config):
    """
    Application factory function to create and configure the Flask app.
    
    Args:
        config_class: Configuration class to use for app configuration
        
    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    CORS(app, origins=["http://localhost:5173"], supports_credentials=True)
    
    # Initialize Celery
    init_celery(app)
    
    # Initialize WebSocket
    socketio = init_socketio(app)
    
    # Ensure database tables are created
    Base.metadata.create_all(bind=engine)
    
    # Register all blueprints
    register_blueprints(app)
    
    return app
