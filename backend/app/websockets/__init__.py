"""
WebSocket functionality for Open Karaoke Studio.
"""

# Import WebSocket handlers to register them


# Export socketio initialization function
from .socketio import init_socketio



__all__ = ["init_socketio"]
