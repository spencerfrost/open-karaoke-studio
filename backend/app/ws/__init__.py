"""
WebSocket endpoints for Open Karaoke Studio FastAPI backend.

This module contains all WebSocket-related functionality including:
- Connection management and session handling
- Real-time job updates
- Unified session-based WebSocket for performance controls and queue management

ARCHITECTURE:
Only TWO WebSocket endpoints are exposed:
1. /ws/jobs - Global job status updates
2. /ws/session/{session_id} - All session-specific karaoke functionality

All session state is properly isolated using session_id as the key.
"""

from .connection_manager import SessionConnectionManager
from .jobs import websocket_jobs_endpoint
from .session_specific import websocket_unified_session_endpoint

__all__ = [
    "SessionConnectionManager",
    "websocket_jobs_endpoint",
    "websocket_unified_session_endpoint",
]
