"""
FastAPI Proof of Concept for Open Karaoke Studio

This demonstrates how FastAPI can integrate with the existing Celery infrastructure
while providing modern async capabilities and better performance.

Enhanced with session-based WebSocket architecture for party mode and
full integration with existing database models and services.

REFACTORED: WebSocket endpoints moved to separate modules for better maintainability.
"""

import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Generator, List

from fastapi import Depends, FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Add the parent directory to the Python path to import from app
sys.path.append(str(Path(__file__).parent.parent))

# Import existing services and models
from app.db.database import SessionLocal
from app.db.models.song import DbSong
from app.services.jobs_service import JobsService

# Import our refactored WebSocket modules
from websockets import (
    SessionConnectionManager,
    websocket_jobs_endpoint,
    websocket_performance_endpoint,
    websocket_queue_endpoint,
    websocket_session_endpoint,
    websocket_session_performance_endpoint,
    websocket_session_queue_endpoint,
    websocket_unified_session_endpoint,
)

# Create FastAPI app with metadata
app = FastAPI(
    title="Open Karaoke Studio API",
    description="FastAPI-powered backend for karaoke processing",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative dev port
        "http://192.168.50.112:5173",  # Network access
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the WebSocket connection manager
manager = SessionConnectionManager()

# Pydantic models for type safety
class HealthResponse(BaseModel):
    status: str
    framework: str
    timestamp: datetime
    response_time_ms: float

class SongCreate(BaseModel):
    artist: str
    title: str
    video_id: str | None = None

class SongResponse(BaseModel):
    id: str
    artist: str
    title: str
    has_audio_files: bool = False
    processing_status: str = "pending"
    created_at: datetime

class JobCreate(BaseModel):
    song_id: str
    job_type: str = "audio_processing"

class JobResponse(BaseModel):
    id: str
    task_id: str
    status: str
    progress: int = 0

# Database dependency for FastAPI
def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session - works with PostgreSQL or SQLite"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        print(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

# Routes
@app.get("/")
async def root():
    return {
        "message": "Open Karaoke Studio FastAPI Backend with Session Management (REFACTORED)",
        "docs": "/docs",
        "health": "/api/health",
        "test_pages": {
            "session_test": "/session-test",
            "dual_backend_test": "/dual-backend-test", 
            "performance_test": "/performance-test",
            "queue_test": "/queue-test",
            "websocket_test": "/websocket-test"
        },
        "websockets": {
            "jobs": "ws://localhost:5124/ws/jobs",
            "performance": "ws://localhost:5124/ws/performance", 
            "session": "ws://localhost:5124/ws/session",
            "queue": "ws://localhost:5124/ws/queue"
        },
        "session_websockets": {
            "unified": "ws://localhost:5124/ws/session/{session_id}",
            "performance": "ws://localhost:5124/ws/session/{session_id}/performance",
            "queue": "ws://localhost:5124/ws/session/{session_id}/queue"
        }
    }

# Test page routes
@app.get("/performance-test", response_class=FileResponse)
async def performance_test_page():
    """Serve the performance controls test page"""
    return FileResponse("performance_test.html", media_type="text/html")

@app.get("/dual-backend-test", response_class=FileResponse)
async def dual_backend_test():
    """Serve the dual backend test page"""
    return FileResponse("dual_backend_test.html", media_type="text/html")

@app.get("/session-test")
async def session_test():
    """Serve the session testing HTML page."""
    return FileResponse("session_test.html")

@app.get("/queue-test", response_class=FileResponse)
async def queue_test_page():
    """Serve the queue test page"""
    return FileResponse("queue_test.html", media_type="text/html")

@app.get("/websocket-test", response_class=FileResponse)
async def websocket_test_page():
    """Serve the complete WebSocket migration test page"""
    return FileResponse("complete_websocket_test.html", media_type="text/html")

# API Routes
@app.get("/api/health", response_model=HealthResponse)
async def health():
    """
    Health check endpoint with performance timing.
    Compare this with Flask's health endpoint to see performance improvements.
    """
    start_time = time.time()
    
    # Simulate some async work
    await asyncio.sleep(0.001)
    
    end_time = time.time()
    response_time = (end_time - start_time) * 1000  # Convert to milliseconds
    
    return HealthResponse(
        status="ok",
        framework="fastapi",
        timestamp=datetime.now(),
        response_time_ms=round(response_time, 2)
    )

@app.get("/api/songs", response_model=List[SongResponse])
async def get_songs(db: Session = Depends(get_db)):
    """
    Get all songs using the existing database models.
    Updated for PostgreSQL compatibility.
    """
    try:
        songs = db.query(DbSong).order_by(DbSong.date_added.desc()).all()
        
        # Convert to API format using the existing to_dict method
        song_responses = []
        for song in songs:
            song_dict = song.to_dict()
            
            # Handle PostgreSQL timestamp formatting
            created_at = datetime.now()
            if song_dict.get("dateAdded"):
                try:
                    # PostgreSQL timestamps may include timezone info
                    date_str = song_dict["dateAdded"]
                    if 'T' in date_str:
                        created_at = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    else:
                        created_at = datetime.fromisoformat(date_str)
                except (ValueError, TypeError):
                    created_at = datetime.now()
            
            song_responses.append(SongResponse(
                id=song_dict["id"],
                artist=song_dict["artist"],
                title=song_dict["title"],
                has_audio_files=bool(song_dict.get("vocalPath") and song_dict.get("instrumentalPath")),
                processing_status=song_dict.get("status", "completed"),
                created_at=created_at
            ))
        
        return song_responses
    except Exception as e:
        print(f"Error getting songs from PostgreSQL: {e}")
        # Fallback to mock data if database fails
        return [
            SongResponse(
                id="demo-1",
                artist="Demo Artist", 
                title="Demo Song",
                has_audio_files=True,
                processing_status="completed",
                created_at=datetime.now()
            )
        ]

@app.post("/api/songs", response_model=SongResponse)
async def create_song(song_data: SongCreate):
    """
    Create a new song. Demonstrates Pydantic validation and async processing.
    """
    # Mock implementation - in real app, this would:
    # 1. Create song in database
    # 2. If video_id provided, start YouTube download job
    # 3. Return the created song
    
    return SongResponse(
        id="new-song-123",
        artist=song_data.artist,
        title=song_data.title,
        created_at=datetime.now()
    )

@app.post("/api/jobs/process-audio", response_model=JobResponse)
async def start_audio_processing(job_data: JobCreate):
    """
    Start audio processing job using existing Celery infrastructure.
    This demonstrates how FastAPI integrates with your current Celery setup.
    """
    try:
        # Import your existing Celery task
        # from app.jobs.jobs import process_audio_job
        # 
        # # Dispatch to existing Celery worker
        # task = process_audio_job.delay(job_data.song_id)
        # 
        # return JobResponse(
        #     id=job_data.song_id,
        #     task_id=task.id,
        #     status="queued"
        # )
        
        # Mock response for demo
        return JobResponse(
            id=job_data.song_id,
            task_id="demo-task-123",
            status="queued"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start job: {str(e)}")

@app.post("/api/broadcast/queue-update")
async def trigger_queue_broadcast():
    """
    HTTP endpoint to trigger queue update broadcasts.
    Called by Flask API when queue changes occur.
    """
    try:
        # Import the broadcast function and call it with our manager
        from websockets.queue import broadcast_queue_update
        await broadcast_queue_update(manager)
        return {"status": "broadcast_sent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to broadcast: {str(e)}")

# WebSocket Routes - Now using the refactored modules
@app.websocket("/ws/jobs")
async def jobs_ws(websocket: WebSocket):
    """WebSocket endpoint for real-time job updates."""
    await websocket_jobs_endpoint(websocket, manager)

@app.websocket("/ws/performance")
async def performance_ws(websocket: WebSocket):
    """WebSocket endpoint for real-time performance controls synchronization."""
    await websocket_performance_endpoint(websocket, manager)

@app.websocket("/ws/session")
async def session_ws(websocket: WebSocket):
    """Session management WebSocket endpoint."""
    await websocket_session_endpoint(websocket, manager)

@app.websocket("/ws/queue")
async def queue_ws(websocket: WebSocket):
    """WebSocket endpoint for real-time karaoke queue updates."""
    await websocket_queue_endpoint(websocket, manager)

# Session-specific WebSocket endpoints
@app.websocket("/ws/session/{session_id}")
async def unified_session_ws(websocket: WebSocket, session_id: str):
    """
    Unified session WebSocket endpoint.
    Handles all session-related communication: performance controls, player state, and queue management.
    """
    await websocket_unified_session_endpoint(websocket, session_id, manager)

@app.websocket("/ws/session/{session_id}/performance")
async def session_performance_ws(websocket: WebSocket, session_id: str):
    """Session-specific performance controls WebSocket endpoint."""
    await websocket_session_performance_endpoint(websocket, session_id, manager)

@app.websocket("/ws/session/{session_id}/queue")
async def session_queue_ws(websocket: WebSocket, session_id: str):
    """Session-specific queue WebSocket endpoint."""
    await websocket_session_queue_endpoint(websocket, session_id, manager)

# Performance testing endpoint
@app.get("/api/performance-test")
async def performance_test():
    """
    Endpoint for comparing FastAPI vs Flask performance.
    Run concurrent requests against this and Flask's equivalent.
    """
    start_time = time.time()
    
    # Simulate some work
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
    return {
        "error": "Not found",
        "message": f"The endpoint {request.url.path} was not found",
        "framework": "fastapi"
    }

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return {
        "error": "Internal server error", 
        "message": "An unexpected error occurred",
        "framework": "fastapi"
    }

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting FastAPI Proof of Concept with PostgreSQL Integration (REFACTORED)")
    print("📖 API Documentation: http://localhost:5124/docs")
    print("🔍 Alternative Docs: http://localhost:5124/redoc")
    print("❤️  Health Check: http://localhost:5124/api/health")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5124,
        reload=True,
        log_level="info"
    )