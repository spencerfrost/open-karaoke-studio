# Flask to FastAPI Migration Guide

**Project:** Open Karaoke Studio  
**Date Created:** August 7, 2025  
**Status:** Planning Phase  

## Executive Summary

This document outlines the migration strategy from Flask to FastAPI for the Open Karaoke Studio backend while preserving the existing Celery infrastructure for CPU-intensive audio processing tasks.

### Why Migrate?

- **Performance**: FastAPI shows ~30x better performance (17ms vs 507ms response times)
- **Native Async**: Built-in async/await support vs Flask's eventlet workaround
- **Type Safety**: Pydantic models provide automatic validation and serialization
- **Modern WebSockets**: Native WebSocket support vs Flask-SocketIO dependency
- **Auto Documentation**: OpenAPI/Swagger docs generated automatically
- **Learning**: Modern async Python patterns and best practices

### What Stays the Same

✅ **Celery Workers** - Audio processing pipeline remains unchanged  
✅ **Database Models** - SQLAlchemy works with FastAPI  
✅ **Business Logic** - Service layer remains unchanged  
✅ **Redis Infrastructure** - Same broker for Celery  
✅ **Audio Processing** - Demucs/PyTorch tasks stay in Celery  

## Current Architecture Analysis

### Flask Stack (Current)
```
Frontend (React/TypeScript) 
    ↓ HTTP/WebSocket
Flask + Flask-SocketIO + Eventlet
    ↓ Task Queue
Celery Workers (Audio Processing)
    ↓ Storage
Redis + SQLite + File System
```

### FastAPI Stack (Target)
```
Frontend (React/TypeScript)
    ↓ HTTP/WebSocket  
FastAPI + Native WebSockets
    ↓ Task Queue
Celery Workers (Audio Processing) [UNCHANGED]
    ↓ Storage
Redis + SQLite + File System [UNCHANGED]
```

## Migration Strategy

### Phase 1: Setup FastAPI Alongside Flask
**Duration:** 1-2 days  
**Goal:** Proof of concept with basic endpoints

1. **Create FastAPI app structure**
   ```bash
   mkdir backend/fastapi_app
   cd backend/fastapi_app
   pip install fastapi uvicorn[standard]
   ```

2. **Basic FastAPI setup**
   ```python
   # fastapi_app/main.py
   from fastapi import FastAPI
   from fastapi.middleware.cors import CORSMiddleware
   
   app = FastAPI(title="Open Karaoke Studio API", version="2.0.0")
   
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["http://localhost:5173"],  # Your frontend
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   
   @app.get("/health")
   async def health():
       return {"status": "ok", "framework": "fastapi"}
   ```

3. **Run both servers during development**
   - Flask: `http://localhost:5123` (current)
   - FastAPI: `http://localhost:8000` (new)

### Phase 2: Migrate Core API Endpoints
**Duration:** 3-5 days  
**Goal:** Move REST API endpoints to FastAPI

#### 2.1 Health Check Endpoint
```python
# Current Flask (backend/app/api/health.py)
@health_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

# New FastAPI equivalent
@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

#### 2.2 Songs API with Pydantic Models
```python
# fastapi_app/models/song.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class SongCreate(BaseModel):
    artist: str
    title: str
    video_id: Optional[str] = None
    
class SongResponse(BaseModel):
    id: str
    artist: str
    title: str
    has_audio_files: bool
    created_at: datetime
    
    class Config:
        from_attributes = True  # For SQLAlchemy compatibility

# fastapi_app/routers/songs.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .models.song import SongCreate, SongResponse
from .database import get_db

router = APIRouter(prefix="/api/songs", tags=["songs"])

@router.get("/", response_model=List[SongResponse])
async def get_songs(db: Session = Depends(get_db)):
    # Reuse existing repository/service logic
    from app.repositories.song_repository import SongRepository
    repo = SongRepository(db)
    songs = repo.get_all()
    return songs

@router.post("/", response_model=SongResponse)
async def create_song(song_data: SongCreate, db: Session = Depends(get_db)):
    # Reuse existing service logic
    pass
```

#### 2.3 Integration with Existing Celery
```python
# fastapi_app/routers/jobs.py
from fastapi import APIRouter
from app.jobs.jobs import process_audio_job  # Import existing Celery task

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

@router.post("/process-audio")
async def start_audio_processing(job_id: str):
    # Dispatch to existing Celery task
    task = process_audio_job.delay(job_id)
    return {"task_id": task.id, "status": "queued"}
```

### Phase 3: Migrate WebSocket Functionality
**Duration:** 2-3 days  
**Goal:** Replace Flask-SocketIO with FastAPI WebSockets

#### 3.1 WebSocket Connection Manager
```python
# fastapi_app/websockets/manager.py
from fastapi import WebSocket
from typing import List, Dict
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.rooms: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        # Remove from all rooms
        for room_connections in self.rooms.values():
            if websocket in room_connections:
                room_connections.remove(websocket)

    async def join_room(self, websocket: WebSocket, room: str):
        if room not in self.rooms:
            self.rooms[room] = []
        self.rooms[room].append(websocket)

    async def broadcast_to_room(self, room: str, message: dict):
        if room in self.rooms:
            for connection in self.rooms[room]:
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    # Handle disconnected clients
                    pass

manager = ConnectionManager()
```

#### 3.2 Job Updates WebSocket
```python
# fastapi_app/websockets/jobs.py
from fastapi import WebSocket, WebSocketDisconnect
from .manager import manager

@app.websocket("/ws/jobs")
async def websocket_jobs_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    await manager.join_room(websocket, "jobs_updates")
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "subscribe_to_jobs":
                # Send current jobs list
                from app.services.jobs_service import JobsService
                jobs_service = JobsService()
                jobs = jobs_service.get_all_jobs()
                await websocket.send_text(json.dumps({
                    "type": "jobs_list",
                    "jobs": [job.to_dict() for job in jobs]
                }))
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

#### 3.3 Performance Controls WebSocket
```python
# fastapi_app/websockets/performance.py
global_performance_state = {
    "vocal_volume": 0,
    "instrumental_volume": 1,
    "lyrics_size": "medium",
    "lyrics_offset": 0,
    "current_time": 0,
    "duration": 0,
    "is_playing": False,
}

@app.websocket("/ws/performance")
async def websocket_performance_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    await manager.join_room(websocket, "global_performance_controls")
    
    # Send current state
    await websocket.send_text(json.dumps({
        "type": "state_update",
        "state": global_performance_state
    }))
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "update_controls":
                # Update global state
                global_performance_state.update(message["data"])
                
                # Broadcast to all clients
                await manager.broadcast_to_room("global_performance_controls", {
                    "type": "state_update",
                    "state": global_performance_state
                })
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

### Phase 4: Update Celery Integration
**Duration:** 1 day  
**Goal:** Update job broadcasting to work with FastAPI WebSockets

#### 4.1 Bridge Celery Events to FastAPI WebSockets
```python
# fastapi_app/events/celery_bridge.py
from app.jobs.jobs import _broadcast_job_event  # Existing function

async def broadcast_job_update_fastapi(job_data: dict):
    """Bridge function to broadcast job updates via FastAPI WebSockets"""
    from .websockets.manager import manager
    
    await manager.broadcast_to_room("jobs_updates", {
        "type": "job_update",
        "job": job_data
    })

# Update existing Celery tasks to use both broadcasting methods during transition
```

### Phase 5: Frontend Updates
**Duration:** 1-2 days  
**Goal:** Update frontend to use new FastAPI endpoints

#### 5.1 Update API Base URL
```typescript
// frontend/src/config/api.ts
const API_BASE_URL = process.env.NODE_ENV === 'development' 
  ? 'http://localhost:8000'  // FastAPI
  : 'http://localhost:5123'; // Flask fallback
```

#### 5.2 Update WebSocket Connections
```typescript
// frontend/src/hooks/useWebSocket.ts
// Replace Socket.IO client with native WebSocket
const ws = new WebSocket('ws://localhost:8000/ws/jobs');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // Handle different message types
  switch (data.type) {
    case 'job_update':
      // Update job state
      break;
    case 'jobs_list':
      // Set initial jobs list
      break;
  }
};
```

### Phase 6: Testing & Validation
**Duration:** 2-3 days  
**Goal:** Ensure feature parity and performance

#### 6.1 Feature Checklist
- [ ] Health check endpoint
- [ ] Songs CRUD operations
- [ ] Job creation and monitoring
- [ ] Real-time job updates via WebSocket
- [ ] Performance controls synchronization
- [ ] File upload/download
- [ ] Error handling
- [ ] Authentication (if applicable)

#### 6.2 Performance Testing
```python
# Load testing script
import asyncio
import aiohttp
import time

async def test_endpoint_performance():
    async with aiohttp.ClientSession() as session:
        start_time = time.time()
        
        # Test 100 concurrent requests
        tasks = []
        for _ in range(100):
            tasks.append(session.get('http://localhost:8000/api/health'))
        
        responses = await asyncio.gather(*tasks)
        end_time = time.time()
        
        print(f"FastAPI: {(end_time - start_time) * 1000}ms for 100 requests")
```

### Phase 7: Deployment & Cleanup
**Duration:** 1 day  
**Goal:** Deploy FastAPI and decommission Flask

#### 7.1 Update Docker Configuration
```dockerfile
# Dockerfile.fastapi
FROM python:3.10-slim

WORKDIR /app
COPY requirements-fastapi.txt .
RUN pip install -r requirements-fastapi.txt

COPY fastapi_app/ .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 7.2 Update docker-compose.yml
```yaml
services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.fastapi
    ports:
      - "8000:8000"  # Changed from 5123
    
  # Celery workers remain unchanged
  celery:
    build:
      context: .
      dockerfile: Dockerfile.celery
```

## Key Differences to Understand

### Request/Response Handling
```python
# Flask
from flask import request, jsonify

@app.route('/api/songs', methods=['POST'])
def create_song():
    data = request.get_json()
    # Manual validation required
    return jsonify(result)

# FastAPI
from pydantic import BaseModel

class SongCreate(BaseModel):
    artist: str
    title: str

@app.post('/api/songs')
async def create_song(song_data: SongCreate):
    # Automatic validation via Pydantic
    return result
```

### Error Handling
```python
# Flask
from flask import abort

@app.route('/api/songs/<song_id>')
def get_song(song_id):
    if not song:
        abort(404)
    return jsonify(song)

# FastAPI
from fastapi import HTTPException

@app.get('/api/songs/{song_id}')
async def get_song(song_id: str):
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    return song
```

### Dependency Injection
```python
# FastAPI has built-in dependency injection
from fastapi import Depends
from sqlalchemy.orm import Session

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get('/api/songs')
async def get_songs(db: Session = Depends(get_db)):
    # db is automatically injected
    pass
```

## Testing Strategy

### Unit Tests
```python
# test_fastapi_endpoints.py
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_create_song():
    song_data = {"artist": "Test Artist", "title": "Test Song"}
    response = client.post("/api/songs", json=song_data)
    assert response.status_code == 201
```

### WebSocket Tests
```python
# test_websockets.py
from fastapi.testclient import TestClient
import json

def test_websocket_jobs():
    with client.websocket_connect("/ws/jobs") as websocket:
        # Test subscription
        websocket.send_text(json.dumps({"type": "subscribe_to_jobs"}))
        data = websocket.receive_text()
        message = json.loads(data)
        assert message["type"] == "jobs_list"
```

## Rollback Plan

If issues arise during migration:

1. **Immediate Rollback**: Switch frontend back to Flask endpoints
2. **Gradual Rollback**: Move endpoints back to Flask one by one
3. **Database**: No changes needed (same models/tables)
4. **Celery**: Unaffected by web framework choice

## Performance Expectations

### Before (Flask + Flask-SocketIO)
- Response time: ~500ms for API calls
- WebSocket latency: ~100-200ms
- Concurrent connections: ~1000

### After (FastAPI + Native WebSockets)
- Response time: ~15-50ms for API calls
- WebSocket latency: ~10-50ms  
- Concurrent connections: ~10,000+

## Resources for Team

### Documentation
- [FastAPI Official Docs](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [FastAPI WebSocket Guide](https://fastapi.tiangolo.com/advanced/websockets/)

### Example Projects
- [FastAPI + Celery Example](https://testdriven.io/blog/fastapi-and-celery/)
- [FastAPI WebSocket Chat](https://github.com/tiangolo/fastapi/tree/master/docs/en/docs/advanced/websockets.md)

### Migration Timeline
- **Total Estimated Time**: 10-15 days
- **Recommended Sprint**: 2-3 weeks with testing
- **Team Size**: 1-2 developers
- **Risk Level**: Medium (well-tested migration path)

## Next Steps

1. **Review this document** with the team
2. **Set up development environment** with both Flask and FastAPI
3. **Create proof of concept** with basic health endpoint
4. **Begin Phase 1** migration when ready
5. **Schedule regular check-ins** during migration

---

**Note**: This migration preserves all existing functionality while modernizing the web layer. The Celery infrastructure for heavy audio processing remains unchanged, ensuring no risk to the core functionality.
