"""
Main entry point for the Open Karaoke Studio backend application.
"""

import os
import logging
from . import create_app
from .config import get_config

# Get the current configuration and create the Flask app
Config = get_config()
app = create_app(Config)

# Configure logging
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

if __name__ == "__main__":
    # Optional: Setup any additional runtime configuration here
    from .websockets.socketio import init_socketio, socketio
    from .websockets.performance_controls_ws import (
        register_handlers as register_performance_controls,
    )
    from .websockets.karaoke_queue_ws import register_handlers as register_karaoke_queue

    # Initialize SocketIO with the Flask app
    init_socketio(app)
    # Register websocket event handlers
    register_performance_controls(socketio)
    register_karaoke_queue(socketio)

    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    use_reloader = os.environ.get("FLASK_USE_RELOADER", "true").lower() == "true"

    print(f"Starting Open Karaoke Studio API Server on http://0.0.0.0:{port}")
    print(f"Debug mode: {debug}")

    socketio.run(app, host="0.0.0.0", port=port, debug=debug, use_reloader=use_reloader)
