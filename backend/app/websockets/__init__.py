"""
WebSocket functionality for Open Karaoke Studio.
"""

from .socketio import init_socketio, socketio

# Import WebSocket handlers to register them
from . import jobs_ws
