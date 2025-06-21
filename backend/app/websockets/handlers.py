"""
Centralized registration for all WebSocket event handlers.
"""


def register_websocket_handlers(socketio):
    """
    Register all WebSocket event handlers (performance controls, karaoke queue, jobs).
    Args:
        socketio: The Flask-SocketIO instance
    """
    from .performance_controls_ws import (
        register_handlers as register_performance_controls,
    )
    from .karaoke_queue_ws import register_handlers as register_karaoke_queue
    from .jobs_ws import initialize_jobs_websocket

    register_performance_controls(socketio)
    register_karaoke_queue(socketio)
    initialize_jobs_websocket()
