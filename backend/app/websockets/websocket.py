"""
WebSocket module for real-time performance controls in Open Karaoke Studio.
This module provides functionality for synchronized control across multiple devices
during a karaoke performance, including vocal/instrumental volume and lyrics size.
"""

from flask_socketio import SocketIO, emit, join_room, leave_room
from flask import request
import logging

logger = logging.getLogger(__name__)
socketio = SocketIO()

# Global room name for performance controls
GLOBAL_CONTROLS_ROOM = 'global_performance_controls'

# Global state for performance controls
global_performance_state = {
    'vocal_volume': 50,
    'instrumental_volume': 100,
    'lyrics_size': 'medium'
}

def init_socketio(app):
    """Initialize SocketIO with the Flask app"""
    socketio.init_app(app, cors_allowed_origins="*")
    register_handlers()
    logger.info("WebSocket server initialized")
    return socketio

def register_handlers():
    """Register WebSocket event handlers"""
    
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        logger.info(f"Client connected: {request.sid}")
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        logger.info(f"Client disconnected: {request.sid}")
    
    @socketio.on('join_performance')
    def handle_join_performance(data=None):
        """Join the global performance controls room"""
        join_room(GLOBAL_CONTROLS_ROOM)
        logger.info(f"Client {request.sid} joined global performance controls")
        
        # Send current state to the new client
        emit('performance_state', global_performance_state, room=request.sid)
    
    @socketio.on('leave_performance')
    def handle_leave_performance(data=None):
        """Leave the global performance controls room"""
        leave_room(GLOBAL_CONTROLS_ROOM)
        logger.info(f"Client {request.sid} left global performance controls")
    
    @socketio.on('update_performance_control')
    def handle_update_control(data):
        """Update a performance control parameter"""
        control_name = data.get('control')
        value = data.get('value')
        
        if not all([control_name, value is not None]):
            logger.error(f"Invalid control update request: {data}")
            return
        
        # Update the control value in global state
        global_performance_state[control_name] = value
        
        # Broadcast to all clients in the room except sender
        emit('control_updated', {
            'control': control_name,
            'value': value
        }, room=GLOBAL_CONTROLS_ROOM, include_self=False)
        
        logger.info(f"Updated {control_name}={value} for global performance controls")

    # Log that handlers are registered
    logger.info("WebSocket event handlers registered")