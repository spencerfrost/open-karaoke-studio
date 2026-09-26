# Open Karaoke Studio - Backend

This directory contains the FastAPI-powered backend for Open Karaoke Studio, responsible for audio processing, song management, and real-time synchronization.

## Project Description

The backend of Open Karaoke Studio is a **FastAPI** RESTful API that orchestrates the core logic of the application. It's designed for high performance and real-time responsiveness.

### Key Responsibilities:
- **Audio Processing:** Orchestrating AI vocal separation using Demucs/Roformer via Celery.
- **Song Management:** Managing the library of songs, including metadata and file storage.
- **Real-time Sync:** Synchronizing performance state across multiple devices using WebSockets.
- **YouTube Integration:** Downloading and processing content from YouTube via yt-dlp.

## Technologies

- **Python 3.13+**
- **FastAPI** (REST API & WebSockets)
- **Celery & Redis** (Asynchronous task processing)
- **SQLAlchemy & Alembic** (Database ORM and migrations)
- **Demucs / PyTorch** (AI audio separation)
- **yt-dlp** (Media downloading)

## Directory Structure

```
backend/
├── alembic/                # Database migration scripts
├── app/                    # Main application package
│   ├── api/                # REST API routers (FastAPI APIRouter)
│   │   ├── songs.py        # Song CRUD and library management
│   │   ├── sessions.py     # Karaoke session management
│   │   └── ...             # Other domain-specific routers
│   ├── config/             # Configuration management (Pydantic-based)
│   ├── db/                 # Database layer (Models, Repositories, Sessions)
│   ├── jobs/               # Celery task definitions
│   │   ├── audio_tasks.py  # Separation and processing tasks
│   │   └── celery_app.py   # Celery application configuration
│   ├── services/           # Business logic layer
│   │   ├── audio.py        # Audio processing orchestration
│   │   ├── separation_engines/ # Specific AI engine implementations
│   │   └── youtube_service.py  # YouTube integration
│   ├── utils/              # Shared utility functions
│   ├── ws/                 # WebSocket layer (ConnectionManager, handlers)
│   └── main.py             # FastAPI entry point
├── tests/                  # Pytest suite
├── run_api.sh              # Start the FastAPI server
├── run_celery.sh           # Start the Celery worker
└── requirements.txt        # Python dependencies
```

## Getting Started

### Prerequisites
- Python 3.13+
- Redis (for Celery and WebSocket state)
- FFmpeg

### Installation
1. Navigate to the `backend/` directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Backend
1. **API Server:**
   ```bash
   ./run_api.sh
   ```
   The server runs on `http://localhost:5123` by default. API docs are available at `/docs`.

2. **Celery Worker:**
   ```bash
   ./run_celery.sh
   ```

## API Documentation
Once the server is running, you can explore the interactive API documentation:
- **Swagger UI:** `http://localhost:5123/docs`
- **ReDoc:** `http://localhost:5123/redoc`

## Development Conventions
- **Logging:** Use `logger = logging.getLogger(__name__)`. Avoid `print()`.
- **Typing:** Use Python type hints for all function parameters and return values.
- **Errors:** Use standardized exceptions from `app.exceptions`.
- **Migrations:** Use Alembic for any database schema changes.

## Testing
Run the test suite using `pytest`:
```bash
pytest
```
Tests are organized into `unit`, `integration`, and `jobs` categories.
