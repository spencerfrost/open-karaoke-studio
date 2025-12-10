"""
WebSocket endpoints for Open Karaoke Studio FastAPI backend.

This module contains all WebSocket-related functionality including:
- Connection management and session handling
- Real-time job updates
- Performance controls synchronization
- Karaoke queue management
- Session-specific WebSocket rooms
"""

from .connection_manager import SessionConnectionManager
from .jobs import websocket_jobs_endpoint
from .performance import websocket_performance_endpoint
from .queue import websocket_queue_endpoint
from .session_specific import (
    websocket_session_performance_endpoint,
    websocket_session_queue_endpoint,
    websocket_unified_session_endpoint,
)
from .sessions import websocket_session_endpoint

__all__ = [
    "SessionConnectionManager",
    "websocket_jobs_endpoint",
    "websocket_performance_endpoint",
    "websocket_queue_endpoint",
    "websocket_session_endpoint",
    "websocket_unified_session_endpoint",
    "websocket_session_performance_endpoint",
    "websocket_session_queue_endpoint",
]
