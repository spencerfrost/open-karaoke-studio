"""
FastAPI Proof of Concept for Open Karaoke Studio

This demonstrates how FastAPI can integrate with the existing Celery infrastructure
while providing modern async capabilities and better performance.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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

# Pydantic models for type safety
class HealthResponse(BaseModel):
    status: str
    framework: str
    timestamp: datetime
    response_time_ms: float

class SongCreate(BaseModel):
    artist: str
    title: str
    video_id: Optional[str] = None

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

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.rooms: dict = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast_to_room(self, room: str, message: dict):
        if room in self.rooms:
            for connection in self.rooms[room]:
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    # Handle disconnected clients
                    pass

    async def join_room(self, websocket: WebSocket, room: str):
        if room not in self.rooms:
            self.rooms[room] = []
        self.rooms[room].append(websocket)

manager = ConnectionManager()

# Routes
@app.get("/")
async def root():
    return {
        "message": "Open Karaoke Studio FastAPI Backend",
        "docs": "/docs",
        "health": "/api/health"
    }

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
async def get_songs():
    """
    Get all songs. In the real implementation, this would use your existing
    SongRepository and database session.
    """
    # This is a mock response. In real implementation:
    # from app.repositories.song_repository import SongRepository
    # from app.db.database import get_db_session
    # 
    # with get_db_session() as session:
    #     repo = SongRepository(session)
    #     songs = repo.get_all()
    #     return [SongResponse.from_orm(song) for song in songs]
    
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

@app.websocket("/ws/jobs")
async def websocket_jobs_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time job updates.
    Replaces Flask-SocketIO with native FastAPI WebSocket support.
    """
    await manager.connect(websocket)
    await manager.join_room(websocket, "jobs_updates")
    
    try:
        # Send initial jobs list
        await websocket.send_text(json.dumps({
            "type": "jobs_list",
            "jobs": [
                {
                    "id": "demo-job-1",
                    "status": "processing",
                    "progress": 45,
                    "filename": "demo-song.mp3"
                }
            ]
        }))
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "subscribe_to_jobs":
                # Client subscribed, they already have the jobs list
                await websocket.send_text(json.dumps({
                    "type": "subscribed",
                    "message": "Subscribed to job updates"
                }))
                
            elif message["type"] == "request_jobs_list":
                # Send current jobs (in real implementation, get from database)
                await websocket.send_text(json.dumps({
                    "type": "jobs_list", 
                    "jobs": []
                }))
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("Client disconnected from jobs WebSocket")

@app.websocket("/ws/performance")
async def websocket_performance_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for performance controls synchronization.
    Demonstrates real-time state synchronization without Flask-SocketIO.
    """
    await manager.connect(websocket)
    await manager.join_room(websocket, "performance_controls")
    
    # Global performance state (in real app, this might be in Redis)
    global_state = {
        "vocal_volume": 0,
        "instrumental_volume": 1,
        "lyrics_size": "medium",
        "is_playing": False
    }
    
    try:
        # Send current state to new connection
        await websocket.send_text(json.dumps({
            "type": "state_update",
            "state": global_state
        }))
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "update_controls":
                # Update global state
                global_state.update(message["data"])
                
                # Broadcast to all connected clients
                await manager.broadcast_to_room("performance_controls", {
                    "type": "state_update",
                    "state": global_state
                })
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("Client disconnected from performance WebSocket")

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
    
    print("🚀 Starting FastAPI Proof of Concept")
    print("📖 API Documentation: http://localhost:8000/docs")
    print("🔍 Alternative Docs: http://localhost:8000/redoc")
    print("❤️  Health Check: http://localhost:8000/api/health")
    print("🎵 Songs API: http://localhost:8000/api/songs")
    print("⚡ Performance Test: http://localhost:8000/api/performance-test")
    print("🔌 WebSocket Jobs: ws://localhost:8000/ws/jobs")
    print("🎛️  WebSocket Performance: ws://localhost:8000/ws/performance")
    print()
    print("💡 This is equivalent to running: uvicorn main:app --reload --port 8000")
    print("   But works just like your Flask app: python main.py")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
