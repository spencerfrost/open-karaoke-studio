# FastAPI Migration Quick Reference

## Before You Start

### Prerequisites Checklist
- [ ] Python 3.10+ installed
- [ ] Current Flask app working correctly
- [ ] Celery workers functioning
- [ ] Redis running
- [ ] Frontend tests passing

### Install FastAPI Dependencies
```bash
cd backend
pip install fastapi uvicorn[standard] python-multipart
# Update requirements.txt
echo "fastapi>=0.104.0" >> requirements-fastapi.txt
echo "uvicorn[standard]>=0.24.0" >> requirements-fastapi.txt
```

## Phase-by-Phase Commands

### Phase 1: Setup
```bash
# Create FastAPI app directory
mkdir backend/fastapi_app
cd backend/fastapi_app

# Create basic structure
touch main.py
mkdir -p {routers,models,websockets,middleware}
touch routers/__init__.py models/__init__.py websockets/__init__.py

# Test basic FastAPI
uvicorn main:app --reload --port 8000
```

### Phase 2: Core Endpoints
```bash
# Run both servers during migration
# Terminal 1 (Flask - keep current)
cd backend && python app/main.py

# Terminal 2 (FastAPI - new)
cd backend/fastapi_app && uvicorn main:app --reload --port 8000
```

### Phase 3: WebSocket Migration
```bash
# Test WebSocket connections
# Use tools like websocat or browser dev tools
websocat ws://localhost:8000/ws/jobs
```

### Phase 4: Frontend Updates
```bash
cd frontend

# Update API client to use FastAPI
npm run dev

# Test both backends during transition
REACT_APP_API_URL=http://localhost:8000 npm run dev  # FastAPI
REACT_APP_API_URL=http://localhost:5123 npm run dev  # Flask (fallback)
```

## Key Code Patterns

### Flask → FastAPI Route Migration
```python
# OLD (Flask)
from flask import Blueprint, request, jsonify

bp = Blueprint('songs', __name__, url_prefix='/api')

@bp.route('/songs', methods=['GET'])
def get_songs():
    return jsonify({"songs": []})

@bp.route('/songs', methods=['POST'])
def create_song():
    data = request.get_json()
    return jsonify({"id": "123"})

# NEW (FastAPI)
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["songs"])

class SongCreate(BaseModel):
    artist: str
    title: str

@router.get("/songs")
async def get_songs():
    return {"songs": []}

@router.post("/songs")
async def create_song(song_data: SongCreate):
    return {"id": "123"}
```

### Flask-SocketIO → FastAPI WebSocket
```python
# OLD (Flask-SocketIO)
from flask_socketio import emit, join_room

@socketio.on('join_queue_room')
def on_join_queue(data):
    room = "karaoke_queue"
    join_room(room)
    emit('queue_joined', {"room": room})

# NEW (FastAPI WebSocket)
from fastapi import WebSocket
import json

@app.websocket("/ws/queue")
async def websocket_queue(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text(json.dumps({
        "type": "queue_joined", 
        "room": "karaoke_queue"
    }))
```

### Database Integration (Unchanged)
```python
# This stays the same in both Flask and FastAPI
from app.repositories.song_repository import SongRepository
from app.db.database import get_db_session

with get_db_session() as session:
    repo = SongRepository(session)
    songs = repo.get_all()
```

### Celery Integration (Unchanged)
```python
# This stays the same in both Flask and FastAPI
from app.jobs.jobs import process_audio_job

# Dispatch task
task = process_audio_job.delay(job_id)
return {"task_id": task.id}
```

## Testing Commands

### Unit Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run FastAPI tests
cd backend/fastapi_app
pytest test_main.py -v

# Test specific endpoint
pytest test_main.py::test_health_endpoint -v
```

### Performance Testing
```bash
# Install testing tools
pip install locust httpx

# Run load test
locust -f locustfile.py --host=http://localhost:8000
```

### WebSocket Testing
```bash
# Install websocat for WebSocket testing
# macOS: brew install websocat
# Linux: cargo install websocat

# Test WebSocket connection
websocat ws://localhost:8000/ws/jobs

# Send test message
echo '{"type": "subscribe_to_jobs"}' | websocat ws://localhost:8000/ws/jobs
```

## Debugging Commands

### Check FastAPI Docs
```bash
# Auto-generated API documentation
open http://localhost:8000/docs      # Swagger UI
open http://localhost:8000/redoc     # ReDoc
```

### Monitor Logs
```bash
# FastAPI with detailed logging
uvicorn main:app --reload --port 8000 --log-level debug

# Check Celery workers (unchanged)
cd backend && celery -A app.jobs.celery_app.celery worker --loglevel=info
```

### Health Checks
```bash
# Test Flask health (current)
curl http://localhost:5123/api/health

# Test FastAPI health (new)
curl http://localhost:8000/api/health

# Compare response times
time curl http://localhost:5123/api/health
time curl http://localhost:8000/api/health
```

## Rollback Commands

### Emergency Rollback
```bash
# Switch frontend back to Flask
cd frontend
REACT_APP_API_URL=http://localhost:5123 npm run dev

# Stop FastAPI server
# Ctrl+C or kill the uvicorn process

# Verify Flask is working
curl http://localhost:5123/api/health
```

### Gradual Rollback
```bash
# Move specific endpoints back to Flask
# Update frontend to use Flask URLs for specific features
# Example: Use Flask for songs, FastAPI for jobs
```

## Development Workflow

### Daily Development
```bash
# Start all services
cd backend && ./run_api.sh          # Flask (current)
cd backend && ./run_celery.sh       # Celery workers
cd backend/fastapi_app && uvicorn main:app --reload --port 8000  # FastAPI (new)
cd frontend && npm run dev           # Frontend

# Check all services
curl http://localhost:5123/api/health  # Flask
curl http://localhost:8000/api/health  # FastAPI
curl http://localhost:5173/           # Frontend
```

### Pre-Migration Checklist
- [ ] Flask app runs without errors
- [ ] Celery workers processing jobs
- [ ] WebSocket connections working
- [ ] Frontend can create/view songs
- [ ] Audio processing working
- [ ] Database migrations up to date

### Post-Migration Validation
- [ ] FastAPI app runs without errors
- [ ] All API endpoints return expected data
- [ ] WebSocket real-time updates working
- [ ] Celery integration unchanged
- [ ] Frontend works with new backend
- [ ] Performance improved
- [ ] Auto-generated docs accessible

## Common Issues & Solutions

### CORS Issues
```python
# Add to FastAPI app
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### WebSocket Connection Issues
```python
# Ensure proper WebSocket handling
@app.websocket("/ws/test")
async def websocket_endpoint(websocket: WebSocket):
    try:
        await websocket.accept()
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        print("Client disconnected")
```

### Pydantic Validation Errors
```python
# Use Optional for optional fields
from typing import Optional
from pydantic import BaseModel

class SongUpdate(BaseModel):
    artist: Optional[str] = None
    title: Optional[str] = None
```

## File Structure Comparison

### Before (Flask)
```
backend/
├── app/
│   ├── main.py              # Flask app
│   ├── api/                 # Flask blueprints
│   ├── websockets/          # Flask-SocketIO
│   ├── jobs/                # Celery tasks
│   └── services/            # Business logic
└── requirements.txt
```

### After (FastAPI)
```
backend/
├── app/                     # Keep for Celery/services
│   ├── jobs/               # Celery tasks (unchanged)
│   └── services/           # Business logic (unchanged)
├── fastapi_app/            # New FastAPI app
│   ├── main.py             # FastAPI app
│   ├── routers/            # API routes
│   ├── models/             # Pydantic models
│   ├── websockets/         # Native WebSockets
│   └── middleware/         # Custom middleware
└── requirements-fastapi.txt
```

---
**💡 Tip**: Keep this guide open during migration for quick reference!
