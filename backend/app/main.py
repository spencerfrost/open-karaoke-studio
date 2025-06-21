"""
Main entry point for the Open Karaoke Studio backend application.
"""

import logging
import os

from . import create_app
from .config import get_config
from .config.logging import setup_logging

# Get the current configuration and create the Flask app
config = get_config()

# Setup comprehensive logging before app creation
logging_config = setup_logging(config)

app = create_app(config)

# Get a logger for this module
logger = logging.getLogger(__name__)

# Only log essential startup information
logger.info("Open Karaoke Studio backend starting")

# Set Flask app logger to use our configured logging
app.logger.handlers = []  # Remove default handlers
app.logger.propagate = True  # Let our loggers handle it

if __name__ == "__main__":
    # Optional: Setup any additional runtime configuration here
    from .websockets.karaoke_queue_ws import register_handlers as register_karaoke_queue
    from .websockets.performance_controls_ws import (
        register_handlers as register_performance_controls,
    )
    from .websockets.socketio import init_socketio, socketio

    # Initialize SocketIO with the Flask app
    init_socketio(app)
    # Register websocket event handlers
    register_performance_controls(socketio)
    register_karaoke_queue(socketio)

    port = int(os.environ.get("PORT", 5123))
    debug = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    use_reloader = os.environ.get("FLASK_USE_RELOADER", "true").lower() == "true"

    print(f"Starting Open Karaoke Studio API Server on http://0.0.0.0:{port}")
    print(f"Debug mode: {debug}")

    socketio.run(app, host="0.0.0.0", port=port, debug=debug, use_reloader=use_reloader)
