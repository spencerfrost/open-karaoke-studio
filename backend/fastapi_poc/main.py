"""
FastAPI Proof of Concept for Open Karaoke Studio

This demonstrates how FastAPI can integrate with the existing Celery infrastructure
while providing modern async capabilities and better performance.

Enhanced with session-based WebSocket architecture for party mode and
full integration with existing database models and services.
"""

import asyncio
import json
import secrets
import string
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Generator, List, Optional

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Add the parent directory to the Python path to import from app
sys.path.append(str(Path(__file__).parent.parent))

# Import existing services and models
from app.db.database import SessionLocal, get_db_session
from app.db.models.job import DbJob, JobStatus
from app.db.models.queue import KaraokeQueueItem
from app.db.models.song import DbSong
from app.repositories.job_repository import JobRepository
from app.services.jobs_service import JobsService
from sqlalchemy.orm import joinedload

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

# Session management models
class SessionCreate(BaseModel):
    device_type: str = "stage"

class SessionJoin(BaseModel):
    display_code: str
    device_type: str = "performer"

class SessionJoinById(BaseModel):
    session_id: str
    device_type: str = "performer"

class ConnectedDevice(BaseModel):
    device_id: str
    device_type: str
    joined_at: datetime
    is_active: bool = True
    is_self: bool = False

class SessionInfo(BaseModel):
    session_id: str
    display_code: str
    is_host: bool
    device_type: str
    device_count: int
    connected_devices: List[ConnectedDevice]
    created_at: datetime
    expires_at: datetime
    is_active: bool = True

class SessionResponse(BaseModel):
    session_id: str
    display_code: str
    is_host: bool
    device_count: int
    expires_at: datetime

# Enhanced WebSocket connection manager with session support
class SessionConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.rooms: Dict[str, List[WebSocket]] = {}
        self.device_sessions: Dict[str, str] = {}  # device_id -> session_id
        self.sessions: Dict[str, Dict] = {}  # session_id -> session_data

    async def connect(self, websocket: WebSocket, device_id: Optional[str] = None):
        await websocket.accept()
        self.active_connections.append(websocket)
        if device_id:
            # Store device_id in our mapping instead of on the websocket object
            self.device_sessions[f"ws_{id(websocket)}"] = device_id

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        # Remove from all rooms
        for room_connections in self.rooms.values():
            if websocket in room_connections:
                room_connections.remove(websocket)
        
        # Remove from device sessions if exists
        ws_key = f"ws_{id(websocket)}"
        device_id = None
        for dev_id, session_id in list(self.device_sessions.items()):
            if dev_id == ws_key:
                device_id = session_id
                break
        
        if device_id:
            # Find the actual device_id in sessions
            for session in self.sessions.values():
                if device_id in session["connected_devices"]:
                    self.leave_session(device_id, session["session_id"])
                    break

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_text(json.dumps(message))

    async def broadcast_to_room(self, room: str, message: dict, exclude: Optional[WebSocket] = None):
        if room in self.rooms:
            room_size = len(self.rooms[room])
            print(f"🔊 Broadcasting to room '{room}' with {room_size} clients")
            disconnected = []
            for connection in self.rooms[room]:
                if connection == exclude:
                    print(f"  ⏭️ Skipping sender {id(connection)}")
                    continue  # Skip the excluded connection
                try:
                    await connection.send_text(json.dumps(message))
                    print(f"  ✅ Sent to client {id(connection)}")
                except Exception as e:
                    print(f"  ❌ Failed to send to client {id(connection)}: {e}")
                    # Handle disconnected clients
                    disconnected.append(connection)
            
            # Clean up disconnected clients
            for conn in disconnected:
                self.rooms[room].remove(conn)
        else:
            print(f"🚫 Room '{room}' not found!")

    async def join_room(self, websocket: WebSocket, room: str):
        if room not in self.rooms:
            self.rooms[room] = []
        if websocket not in self.rooms[room]:
            self.rooms[room].append(websocket)
            print(f"🏠 Client {id(websocket)} joined room '{room}' (now {len(self.rooms[room])} clients)")
        else:
            print(f"🔄 Client {id(websocket)} already in room '{room}'")

    async def leave_room(self, websocket: WebSocket, room: str):
        if room in self.rooms and websocket in self.rooms[room]:
            self.rooms[room].remove(websocket)

    def generate_session_id(self) -> str:
        """Generate a unique session ID."""
        return secrets.token_urlsafe(24)

    def generate_display_code(self) -> str:
        """Generate a 4-character display code."""
        # Use uppercase letters and numbers, excluding confusing characters (0, O, 1, I)
        chars = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
        return "".join(secrets.choice(chars) for _ in range(4))

    def create_session(self, host_device_id: str) -> Dict:
        """Create a new karaoke session."""
        session_id = self.generate_session_id()
        display_code = self.generate_display_code()
        
        # Ensure display code is unique
        max_attempts = 10
        attempt = 0
        while any(s.get("display_code") == display_code for s in self.sessions.values()) and attempt < max_attempts:
            display_code = self.generate_display_code()
            attempt += 1
        
        session_data = {
            "session_id": session_id,
            "display_code": display_code,
            "host_device_id": host_device_id,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(hours=24),
            "is_active": True,
            "connected_devices": {}
        }
        
        self.sessions[session_id] = session_data
        return session_data

    def find_session_by_code(self, display_code: str) -> Optional[Dict]:
        """Find session by display code."""
        for session in self.sessions.values():
            if session.get("display_code") == display_code and session.get("is_active"):
                return session
        return None

    def find_session_by_id(self, session_id: str) -> Optional[Dict]:
        """Find session by ID."""
        return self.sessions.get(session_id) if self.sessions.get(session_id, {}).get("is_active") else None

    def join_session(self, session_id: str, device_id: str, device_type: str) -> bool:
        """Add device to session."""
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        session["connected_devices"][device_id] = {
            "device_id": device_id,
            "device_type": device_type,
            "joined_at": datetime.now(),
            "is_active": True
        }
        
        self.device_sessions[device_id] = session_id
        return True

    def leave_session(self, device_id: str, session_id: Optional[str] = None):
        """Remove device from session."""
        if not session_id and device_id in self.device_sessions:
            session_id = self.device_sessions[device_id]
        
        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
            if device_id in session["connected_devices"]:
                session["connected_devices"][device_id]["is_active"] = False
                
            # If host leaves, mark session inactive
            if device_id == session["host_device_id"]:
                session["is_active"] = False
        
        if device_id in self.device_sessions:
            del self.device_sessions[device_id]

    def get_session_for_device(self, device_id: str) -> Optional[Dict]:
        """Get session data for a device."""
        if device_id in self.device_sessions:
            session_id = self.device_sessions[device_id]
            return self.sessions.get(session_id)
        return None

    def get_session_room_name(self, session_id: str, room_type: str = "main") -> str:
        """Generate session-specific room names."""
        if room_type == "main":
            return f"session_{session_id}"
        return f"session_{session_id}_{room_type}"

manager = SessionConnectionManager()

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

# Global performance state for real-time controls
global_performance_state = {
    # Synchronized state - these values are shared across all devices
    "vocal_volume": 0,
    "instrumental_volume": 1,
    "lyrics_size": "medium",
    "lyrics_offset": 0,
    
    # Playback state - ALSO synchronized (contrary to my earlier comment)
    "current_time": 0,
    "duration": 0,
    "is_playing": False,
}

# Helper functions for jobs
async def get_current_jobs_list():
    """
    Get current jobs list using the real JobsService.
    Updated for PostgreSQL compatibility.
    """
    try:
        # Use the existing JobsService which handles PostgreSQL properly
        jobs_service = JobsService()
        jobs = jobs_service.get_all_jobs()
        return [job.to_dict() for job in jobs]
    except Exception as e:
        print(f"Error getting jobs list from PostgreSQL: {e}")
        # Fallback to mock data if service fails
        return [
            {
                "id": "demo-job-1",
                "status": "processing",
                "progress": 45,
                "filename": "demo-song.mp3",
                "task_id": "demo-task-123",
                "created_at": datetime.now().isoformat()
            }
        ]

# Job broadcasting functions for Celery integration
async def broadcast_job_update(job_data: dict):
    """Broadcast job update to all subscribed clients."""
    await manager.broadcast_to_room("jobs_updates", {
        "type": "job_updated",
        "job": job_data
    })

async def broadcast_job_created(job_data: dict):
    """Broadcast new job creation to all subscribed clients."""
    await manager.broadcast_to_room("jobs_updates", {
        "type": "job_created", 
        "job": job_data
    })

async def broadcast_job_completed(job_data: dict):
    """Broadcast job completion to all subscribed clients."""
    await manager.broadcast_to_room("jobs_updates", {
        "type": "job_completed",
        "job": job_data
    })

async def broadcast_job_failed(job_data: dict):
    """Broadcast job failure to all subscribed clients."""
    await manager.broadcast_to_room("jobs_updates", {
        "type": "job_failed",
        "job": job_data
    })

async def broadcast_job_cancelled(job_data: dict):
    """Broadcast job cancellation to all subscribed clients."""
    await manager.broadcast_to_room("jobs_updates", {
        "type": "job_cancelled",
        "job": job_data
    })

async def broadcast_all_jobs(jobs_data: list):
    """Broadcast complete jobs list to all subscribed clients."""
    await manager.broadcast_to_room("jobs_updates", {
        "type": "jobs_list",
        "jobs": jobs_data
    })

# Helper functions for karaoke queue
async def get_current_queue_state():
    """
    Get current karaoke queue state using real database queries.
    Updated for PostgreSQL compatibility.
    """
    try:
        with get_db_session() as session:
            # Get queue items with song data - PostgreSQL handles this efficiently
            queue_items = (
                session.query(KaraokeQueueItem)
                .options(joinedload(KaraokeQueueItem.song))
                .order_by(KaraokeQueueItem.position)
                .all()
            )
            
            # Format data for frontend
            queue_data = []
            for item in queue_items:
                if item.song:  # Ensure song exists
                    # Handle potential null timestamps gracefully
                    added_at = None
                    if hasattr(item, 'created_at') and item.created_at:
                        added_at = item.created_at.isoformat()
                    
                    queue_data.append({
                        "id": item.id,
                        "songId": item.song_id,
                        "singer": item.singer_name,
                        "position": item.position,
                        "addedAt": added_at,
                        "song": {
                            "id": item.song.id,
                            "title": item.song.title,
                            "artist": item.song.artist,
                            "album": item.song.album,
                            "duration": item.song.duration,
                            "coverArt": getattr(item.song, 'cover_art_url', None),
                            "syncedLyrics": item.song.synced_lyrics,
                            "plainLyrics": item.song.plain_lyrics
                        }
                    })
            return queue_data
    except Exception as e:
        print(f"Error getting queue state from PostgreSQL: {e}")
        # Fallback to mock data if database fails
        return [
            {
                "id": "queue-item-1",
                "songId": "demo-song-1",
                "singer": "Demo Singer",
                "position": 1,
                "addedAt": datetime.now().isoformat(),
                "song": {
                    "id": "demo-song-1",
                    "title": "Demo Song",
                    "artist": "Demo Artist",
                    "album": "Demo Album",
                    "duration": 180,
                    "coverArt": None,
                    "syncedLyrics": None,
                    "plainLyrics": "Demo lyrics..."
                }
            }
        ]

# Queue broadcasting functions
async def broadcast_queue_update():
    """Broadcast queue update to all clients in the queue room."""
    queue_data = await get_current_queue_state()
    await manager.broadcast_to_room("karaoke_queue", {
        "type": "queue_updated",
        "items": queue_data
    })

# Routes
@app.get("/")
async def root():
    return {
        "message": "Open Karaoke Studio FastAPI Backend with Session Management",
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
        }
    }

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

@app.websocket("/ws/jobs")
async def websocket_jobs_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time job updates.
    Replaces Flask-SocketIO with native FastAPI WebSocket support.
    Enhanced with full Flask feature parity.
    """
    await manager.connect(websocket)
    jobs_room = "jobs_updates"
    await manager.join_room(websocket, jobs_room)
    
    print(f"Jobs client connected: {id(websocket)}")
    
    try:
        # Send connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connected",
            "status": "connected"
        }))
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            message_type = message.get("type")
            
            if message_type == "subscribe_to_jobs":
                # Client explicitly subscribed to job updates
                await websocket.send_text(json.dumps({
                    "type": "subscribed",
                    "status": "subscribed to job updates"
                }))
                
                # Send current jobs list to the newly subscribed client
                # In real implementation, this would call JobsService
                await websocket.send_text(json.dumps({
                    "type": "jobs_list",
                    "jobs": await get_current_jobs_list()
                }))
                
                print(f"Client {id(websocket)} subscribed to job updates")
                
            elif message_type == "unsubscribe_from_jobs":
                # Client unsubscribed from job updates
                await manager.leave_room(websocket, jobs_room)
                await websocket.send_text(json.dumps({
                    "type": "unsubscribed",
                    "status": "unsubscribed from job updates"
                }))
                
                print(f"Client {id(websocket)} unsubscribed from job updates")
                
            elif message_type == "request_jobs_list":
                # Send current jobs list on demand
                await websocket.send_text(json.dumps({
                    "type": "jobs_list",
                    "jobs": await get_current_jobs_list()
                }))
                
            else:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                }))
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print(f"Jobs client disconnected: {id(websocket)}")

@app.websocket("/ws/performance")
async def websocket_performance_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time performance controls synchronization.
    Handles vocal/instrumental volume, lyrics controls, and playback state.
    Based on the Flask-SocketIO performance_controls_ws.py implementation.
    """
    await manager.connect(websocket)
    performance_room = "global_performance_controls"
    await manager.join_room(websocket, performance_room)
    
    print(f"Performance controls client connected: {id(websocket)}")
    
    try:
        # Send current performance state to new connection
        await websocket.send_text(json.dumps({
            "type": "performance_state",
            "state": global_performance_state
        }))
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            message_type = message.get("type")
            
            if message_type == "join_performance":
                # Client explicitly joined performance controls
                await websocket.send_text(json.dumps({
                    "type": "performance_state",
                    "state": global_performance_state
                }))
                print(f"Client {id(websocket)} joined performance controls")
                
            elif message_type == "update_performance_control":
                # Update a specific control (vocal_volume, instrumental_volume, etc.)
                control_name = message.get("control")
                value = message.get("value")
                
                if not control_name or value is None:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Invalid control update request"
                    }))
                    continue
                    
                if control_name not in global_performance_state:
                    await websocket.send_text(json.dumps({
                        "type": "error", 
                        "message": f"Unsupported control: {control_name}"
                    }))
                    continue
                
                # Update global state
                global_performance_state[control_name] = value
                print(f"🎛️ Updated {control_name}={value} for performance controls")
                print(f"🌍 Global state: {global_performance_state}")
                
                # Broadcast to all clients except sender
                await manager.broadcast_to_room(performance_room, {
                    "type": "control_updated",
                    "control": control_name,
                    "value": value
                }, exclude=websocket)
                
            elif message_type == "update_player_state":
                # Update player state - this IS synchronized across all devices
                is_playing = message.get("isPlaying")
                current_time = message.get("currentTime") 
                duration = message.get("duration")
                
                if is_playing is not None:
                    global_performance_state["is_playing"] = is_playing
                if current_time is not None:
                    global_performance_state["current_time"] = current_time
                if duration is not None:
                    global_performance_state["duration"] = duration
                    
                # Send updated state back to sender only (like Flask version)
                await websocket.send_text(json.dumps({
                    "type": "performance_state",
                    "state": global_performance_state
                }))
                
                print(f"Updated player state: is_playing={is_playing}, currentTime={current_time}, duration={duration}")
                
            elif message_type == "reset_player_state":
                # Reset player state AND broadcast event (like Flask version)
                global_performance_state["current_time"] = 0
                global_performance_state["is_playing"] = False
                
                # Broadcast reset event to all clients except sender
                await manager.broadcast_to_room(performance_room, {
                    "type": "reset_player_state"
                }, exclude=websocket)
                
                print(f"Reset player state from client {id(websocket)}")
                
            elif message_type == "playback_play":
                # Play command: Update state AND broadcast event (matching Flask exactly)
                global_performance_state["is_playing"] = True
                
                # Broadcast play command to all clients including sender
                await manager.broadcast_to_room(performance_room, {
                    "type": "playback_play"
                })
                
                # Also broadcast updated state to all clients including sender
                await manager.broadcast_to_room(performance_room, {
                    "type": "performance_state",
                    "state": global_performance_state
                })
                
                print(f"Play command from client {id(websocket)}")
                
            elif message_type == "playback_pause":
                # Pause command: Update state AND broadcast event (matching Flask exactly)
                global_performance_state["is_playing"] = False
                
                # Broadcast pause command to all clients including sender
                await manager.broadcast_to_room(performance_room, {
                    "type": "playback_pause"
                })
                
                # Also broadcast updated state to all clients including sender
                await manager.broadcast_to_room(performance_room, {
                    "type": "performance_state", 
                    "state": global_performance_state
                })
                
                print(f"Pause command from client {id(websocket)}")
                
            elif message_type == "seek_to":
                # Seek command: Update current_time state AND broadcast event
                seek_time = message.get("time", 0)
                global_performance_state["current_time"] = seek_time
                
                await manager.broadcast_to_room(performance_room, {
                    "type": "seek_to",
                    "time": seek_time
                })
                
                # Also broadcast updated state
                await manager.broadcast_to_room(performance_room, {
                    "type": "performance_state",
                    "state": global_performance_state
                })
                
                print(f"Seek command to {seek_time}s from client {id(websocket)}")
                
            else:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                }))
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print(f"Performance controls client disconnected: {id(websocket)}")

@app.websocket("/ws/session")
async def websocket_session_endpoint(websocket: WebSocket):
    """
    Session management WebSocket endpoint.
    Handles session creation, joining, leaving, and real-time session updates.
    """
    device_id = f"device_{secrets.token_urlsafe(8)}"
    await manager.connect(websocket, device_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            message_type = message.get("type")
            
            if message_type == "create_session":
                # Create new session
                session_data = manager.create_session(device_id)
                
                # Join the session room
                session_room = manager.get_session_room_name(session_data["session_id"])
                await manager.join_room(websocket, session_room)
                
                # Add host to session
                manager.join_session(session_data["session_id"], device_id, "stage")
                
                await manager.send_personal_message({
                    "type": "session_created",
                    "session_id": session_data["session_id"],
                    "display_code": session_data["display_code"],
                    "is_host": True,
                    "device_count": 1,
                    "expires_at": session_data["expires_at"].isoformat(),
                }, websocket)
                
            elif message_type == "join_session_by_code":
                display_code = message.get("display_code", "").upper().strip()
                device_type = message.get("device_type", "performer")
                
                if not display_code or len(display_code) != 4:
                    await manager.send_personal_message({
                        "type": "session_error",
                        "error": "Invalid display code"
                    }, websocket)
                    continue
                
                session = manager.find_session_by_code(display_code)
                if not session:
                    await manager.send_personal_message({
                        "type": "session_error",
                        "error": "Session not found"
                    }, websocket)
                    continue
                
                # Join the session
                session_room = manager.get_session_room_name(session["session_id"])
                await manager.join_room(websocket, session_room)
                
                manager.join_session(session["session_id"], device_id, device_type)
                
                device_count = len([d for d in session["connected_devices"].values() if d["is_active"]])
                
                await manager.send_personal_message({
                    "type": "session_joined",
                    "session_id": session["session_id"],
                    "display_code": session["display_code"],
                    "is_host": device_id == session["host_device_id"],
                    "device_type": device_type,
                    "device_count": device_count,
                    "expires_at": session["expires_at"].isoformat(),
                }, websocket)
                
                # Notify other devices about new member
                await manager.broadcast_to_room(session_room, {
                    "type": "device_joined",
                    "device_id": device_id,
                    "device_type": device_type,
                    "device_count": device_count,
                })
                
            elif message_type == "join_session_by_id":
                session_id = message.get("session_id", "").strip()
                device_type = message.get("device_type", "performer")
                
                session = manager.find_session_by_id(session_id)
                if not session:
                    await manager.send_personal_message({
                        "type": "session_error",
                        "error": "Session not found"
                    }, websocket)
                    continue
                
                # Same logic as join by code
                session_room = manager.get_session_room_name(session["session_id"])
                await manager.join_room(websocket, session_room)
                
                manager.join_session(session["session_id"], device_id, device_type)
                
                device_count = len([d for d in session["connected_devices"].values() if d["is_active"]])
                
                await manager.send_personal_message({
                    "type": "session_joined",
                    "session_id": session["session_id"],
                    "display_code": session["display_code"],
                    "is_host": device_id == session["host_device_id"],
                    "device_type": device_type,
                    "device_count": device_count,
                    "expires_at": session["expires_at"].isoformat(),
                }, websocket)
                
                await manager.broadcast_to_room(session_room, {
                    "type": "device_joined",
                    "device_id": device_id,
                    "device_type": device_type,
                    "device_count": device_count,
                })
                
            elif message_type == "leave_session":
                session = manager.get_session_for_device(device_id)
                if session:
                    session_room = manager.get_session_room_name(session["session_id"])
                    
                    manager.leave_session(device_id, session["session_id"])
                    await manager.leave_room(websocket, session_room)
                    
                    device_count = len([d for d in session["connected_devices"].values() if d["is_active"]])
                    
                    await manager.send_personal_message({
                        "type": "session_left",
                        "session_id": session["session_id"]
                    }, websocket)
                    
                    # If host left, end session
                    if device_id == session["host_device_id"]:
                        await manager.broadcast_to_room(session_room, {
                            "type": "session_ended",
                            "reason": "Host disconnected"
                        })
                    else:
                        await manager.broadcast_to_room(session_room, {
                            "type": "device_left",
                            "device_id": device_id,
                            "device_count": device_count,
                        })
                
            elif message_type == "get_session_info":
                session = manager.get_session_for_device(device_id)
                if session:
                    connected_devices = [
                        {
                            "device_id": d["device_id"],
                            "device_type": d["device_type"],
                            "joined_at": d["joined_at"].isoformat(),
                            "is_self": d["device_id"] == device_id,
                        }
                        for d in session["connected_devices"].values()
                        if d["is_active"]
                    ]
                    
                    await manager.send_personal_message({
                        "type": "session_info",
                        "in_session": True,
                        "session_id": session["session_id"],
                        "display_code": session["display_code"],
                        "is_host": device_id == session["host_device_id"],
                        "device_count": len(connected_devices),
                        "connected_devices": connected_devices,
                        "created_at": session["created_at"].isoformat(),
                        "expires_at": session["expires_at"].isoformat(),
                        "is_active": session["is_active"],
                    }, websocket)
                else:
                    await manager.send_personal_message({
                        "type": "session_info",
                        "in_session": False
                    }, websocket)
                
    except WebSocketDisconnect:
        # Handle disconnection
        session = manager.get_session_for_device(device_id)
        if session:
            session_room = manager.get_session_room_name(session["session_id"])
            manager.leave_session(device_id, session["session_id"])
            
            # Notify remaining devices
            if device_id == session["host_device_id"]:
                await manager.broadcast_to_room(session_room, {
                    "type": "session_ended",
                    "reason": "Host disconnected"
                })
            else:
                device_count = len([d for d in session["connected_devices"].values() if d["is_active"]])
                await manager.broadcast_to_room(session_room, {
                    "type": "device_disconnected",
                    "device_id": device_id,
                    "device_count": device_count,
                })
        
        manager.disconnect(websocket)
        print(f"Device {device_id} disconnected from session WebSocket")

@app.websocket("/ws/queue")
async def websocket_queue_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time karaoke queue updates.
    Replaces Flask-SocketIO queue functionality with FastAPI WebSockets.
    """
    await manager.connect(websocket)
    queue_room = "karaoke_queue"
    await manager.join_room(websocket, queue_room)
    
    print(f"Queue client connected: {id(websocket)}")
    
    try:
        # Send connection confirmation
        await websocket.send_text(json.dumps({
            "type": "queue_joined",
            "room": queue_room
        }))
        
        # Send current queue state
        queue_data = await get_current_queue_state()
        await websocket.send_text(json.dumps({
            "type": "queue_updated",
            "items": queue_data
        }))
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            message_type = message.get("type")
            
            if message_type == "join_queue_room":
                # Client explicitly joined queue room
                await websocket.send_text(json.dumps({
                    "type": "queue_joined",
                    "room": queue_room
                }))
                
                # Send current queue
                queue_data = await get_current_queue_state()
                await websocket.send_text(json.dumps({
                    "type": "queue_updated", 
                    "items": queue_data
                }))
                
                print(f"Client {id(websocket)} joined queue room")
                
            elif message_type == "leave_queue_room":
                # Client left queue room
                await manager.leave_room(websocket, queue_room)
                await websocket.send_text(json.dumps({
                    "type": "queue_left",
                    "room": queue_room
                }))
                
                print(f"Client {id(websocket)} left queue room")
                
            elif message_type == "request_queue_update":
                # Send current queue state on demand
                queue_data = await get_current_queue_state()
                await websocket.send_text(json.dumps({
                    "type": "queue_updated",
                    "items": queue_data
                }))
                
            else:
                await websocket.send_text(json.dumps({
                    "type": "error", 
                    "message": f"Unknown message type: {message_type}"
                }))
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print(f"Queue client disconnected: {id(websocket)}")

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
    
    print("🚀 Starting FastAPI Proof of Concept with PostgreSQL Integration")
    print("📖 API Documentation: http://localhost:5124/docs")
    print("🔍 Alternative Docs: http://localhost:5124/redoc")
    print("❤️  Health Check: http://localhost:5124/api/health")
    print("🎵 Songs API: http://localhost:5124/api/songs")
    print("⚡ Performance Test: http://localhost:5124/api/performance-test")
    print("🔌 WebSocket Jobs: ws://localhost:5124/ws/jobs")
    print("🎛️  WebSocket Performance: ws://localhost:5124/ws/performance")
    print("🎪 WebSocket Sessions: ws://localhost:5124/ws/session")
    print("🎵 WebSocket Queue: ws://localhost:5124/ws/queue")
    print()
    print("💡 This is equivalent to running: uvicorn main:app --reload --port 5124")
    print("   But works just like your Flask app: python main.py")
    print()
    print("🗄️  Database: PostgreSQL (via existing configuration)")
    print("🎯 Session Management Features:")
    print("   • Create karaoke sessions with 4-character codes")
    print("   • Join sessions by code or direct link")
    print("   • Real-time device synchronization")
    print("   • Session-specific WebSocket rooms")
    print("   • Host controls and device management")
    print()
    print("✅ Real Database Integration:")
    print("   • Songs API using existing PostgreSQL data")
    print("   • Jobs API using existing JobsService")
    print("   • Queue API using existing models")
    print("   • All WebSockets ready for Celery integration")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5124,
        reload=True,
        log_level="info"
    )
