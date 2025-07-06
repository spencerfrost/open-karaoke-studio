"""
SocketIO instance and initialization for Open Karaoke Studio.
"""

from flask_socketio import SocketIO

# Create the SocketIO instance (do not bind to app yet)
import os

# Get the Redis URL from environment or use default
REDIS_URL = os.environ.get("SOCKETIO_REDIS_URL", "redis://localhost:6379/0")
socketio = SocketIO(message_queue=REDIS_URL)


def init_socketio(app):
    """Initialize SocketIO with the Flask app."""
    socketio.init_app(app, cors_allowed_origins="*")
    return socketio
