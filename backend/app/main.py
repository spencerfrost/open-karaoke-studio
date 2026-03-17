"""
FastAPI Backend for Open Karaoke Studio

This is the main FastAPI application that provides:
- REST API endpoints for songs, jobs, sessions, and queue management
- WebSocket endpoints for real-time communication
- Integration with existing Celery infrastructure for audio processing

CLEAN ARCHITECTURE: Only two WebSocket endpoints - jobs (global) and session (session-specific).
All karaoke functionality (performance controls, queue, player state) handled through sessions.
"""

import asyncio
import logging
import os
import time

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

# Import routers
from app.api import (
    health_router,
    host_settings_router,
    jobs_router,
    lyrics_router,
    metadata_router,
    queue_router,
    sessions_router,
    songs_router,
    users_router,
    youtube_music_router,
    youtube_router,
)

# Import configuration and logging setup
from app.config import get_config
from app.config.logging import setup_logging

# Import the cleanup utility
from app.utils.cleanup_jobs import cleanup_stuck_jobs

# Import WebSocket modules
from app.ws import (
    SessionConnectionManager,
    websocket_jobs_endpoint,
    websocket_unified_session_endpoint,
)
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Get configuration and setup logging
config = get_config()
logging_config = setup_logging(config)
logger = logging.getLogger(__name__)

# Clean up stuck jobs on startup
logger.info("Open Karaoke Studio backend starting")
cleanup_stuck_jobs()

# Create FastAPI app with metadata
app = FastAPI(
    title="Open Karaoke Studio API",
    description="FastAPI-powered backend for karaoke processing with real-time WebSocket support",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the WebSocket connection manager
manager = SessionConnectionManager()
app.state.session_manager = manager

# Include all API routers
app.include_router(health_router)
app.include_router(songs_router)
app.include_router(jobs_router)
app.include_router(sessions_router)
app.include_router(queue_router)
app.include_router(youtube_router)
app.include_router(youtube_music_router)
app.include_router(metadata_router)
app.include_router(lyrics_router)
app.include_router(users_router)
app.include_router(host_settings_router)


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Open Karaoke Studio FastAPI Backend",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/api/health",
        "api_endpoints": {
            "songs": "/api/songs",
            "jobs": "/api/jobs",
            "sessions": "/api/sessions",
            "queue": "/api/karaoke-queue",
            "youtube": "/api/youtube",
            "youtube_music": "/api/youtube-music",
            "metadata": "/api/metadata",
            "lyrics": "/api/lyrics",
            "users": "/api/users",
        },
        "websockets": {
            "jobs": "ws://localhost:5123/ws/jobs",
            "session": "ws://localhost:5123/ws/session/{session_id}",
        },
    }


# WebSocket Routes - Clean session architecture with only two endpoints
@app.websocket("/ws/jobs")
async def jobs_ws(websocket: WebSocket):
    """WebSocket endpoint for real-time job updates."""
    await websocket_jobs_endpoint(websocket, manager)


@app.websocket("/ws/session/{session_id}")
async def unified_session_ws(websocket: WebSocket, session_id: str):
    """
    Unified session WebSocket endpoint.
    Handles all session-related communication: performance controls, player state, and queue management.
    """
    await websocket_unified_session_endpoint(websocket, session_id, manager)


# Performance testing endpoint
@app.get("/api/performance-test")
async def performance_test():
    """
    Endpoint for performance testing.
    """
    start_time = time.time()
    await asyncio.sleep(0.01)  # 10ms of "work"
    end_time = time.time()
    
    return {
        "framework": "fastapi",
        "response_time_ms": round((end_time - start_time) * 1000, 2),
        "async_capable": True,
        "concurrent_ready": True
    }


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not found",
            "message": f"The endpoint {request.url.path} was not found",
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error", 
            "message": "An unexpected error occurred",
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("PORT", 5123))
    
    logger.info("Starting Open Karaoke Studio API Server on http://0.0.0.0:%s", port)
    print(f"🚀 Starting Open Karaoke Studio FastAPI Backend")
    print(f"📖 API Documentation: http://localhost:{port}/docs")
    print(f"🔍 Alternative Docs: http://localhost:{port}/redoc")
    print(f"❤️  Health Check: http://localhost:{port}/api/health")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
