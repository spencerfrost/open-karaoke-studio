"""
SocketIO instance and initialization for Open Karaoke Studio.
"""

from flask_socketio import SocketIO

# Create the SocketIO instance (do not bind to app yet)
socketio = SocketIO()


def init_socketio(app):
    """Initialize SocketIO with the Flask app."""
    socketio.init_app(app, cors_allowed_origins="*")
    return socketio
