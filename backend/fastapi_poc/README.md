# FastAPI Proof of Concept Setup

This directory contains a basic FastAPI setup that demonstrates how to integrate with your existing Celery infrastructure while providing modern async capabilities.

## Quick Start

1. **Install FastAPI dependencies:**
   ```bash
   cd backend/fastapi_poc
   source ../venv/bin/activate  # Activate venv from backend directory
   pip install fastapi uvicorn[standard] python-multipart
   ```

2. **Run the FastAPI app:**
   ```bash
   uvicorn main:app --reload --port 8000
   ```

3. **Test the API:**
   ```bash
   # Health check
   curl http://localhost:8000/api/health
   
   # View auto-generated docs
   open http://localhost:8000/docs
   ```

## What's Included

- ✅ Basic FastAPI app structure
- ✅ Integration with existing Celery tasks
- ✅ WebSocket support for real-time updates
- ✅ Pydantic models for type safety
- ✅ Auto-generated API documentation
- ✅ CORS configuration for frontend integration

## Key Features Demonstrated

### 1. Performance Comparison
The `/api/health` endpoint shows response time improvements over Flask.

### 2. Type Safety
All endpoints use Pydantic models for automatic validation:
```python
class SongCreate(BaseModel):
    artist: str
    title: str
    video_id: Optional[str] = None
```

### 3. Celery Integration
Jobs are dispatched to your existing Celery workers:
```python
@router.post("/process-audio")
async def start_audio_processing(job_id: str):
    task = process_audio_job.delay(job_id)
    return {"task_id": task.id}
```

### 4. WebSocket Support
Real-time updates without Flask-SocketIO:
```python
@app.websocket("/ws/jobs")
async def websocket_jobs_endpoint(websocket: WebSocket):
    # Native WebSocket handling
```

## Integration with Existing Code

This POC reuses your existing:
- Database models (SQLAlchemy)
- Repository patterns
- Service layer
- Celery tasks
- Business logic

No changes needed to your core functionality!

## Next Steps

1. **Run both servers** (Flask on 5123, FastAPI on 8000)
2. **Compare performance** using the health endpoints
3. **Test WebSocket connections** 
4. **Migrate one endpoint at a time** when ready for full migration

See the full migration guide in `FLASK_TO_FASTAPI_MIGRATION.md` for detailed steps.
