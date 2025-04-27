# Open Karaoke Studio Backend

This directory contains the backend API and processing services for the Open Karaoke Studio application.

## Directory Structure

The backend is organized into the following structure:

```
backend/
├── app/                     # Main application package
│   ├── __init__.py          # Application factory
│   ├── config.py            # Configuration settings
│   ├── main.py              # Entry point for the application
│   │
│   ├── api/                 # API endpoints
│   │   ├── __init__.py      # Registers all blueprints
│   │   ├── karaoke_queue.py # Karaoke queue endpoints
│   │   ├── lyrics.py        # Lyrics API endpoints
│   │   ├── musicbrainz.py   # MusicBrainz API endpoints 
│   │   ├── queue.py         # Queue management endpoints
│   │   ├── songs.py         # Song management endpoints
│   │   ├── users.py         # User management endpoints
│   │   └── youtube.py       # YouTube integration endpoints
│   │
│   ├── db/                  # Database models and access
│   │   ├── __init__.py      # Database package exports
│   │   ├── database.py      # Database connection and utilities
│   │   ├── migrate.py       # Database migration utilities
│   │   └── models.py        # SQLAlchemy and Pydantic models
│   │
│   ├── services/            # Business logic and utilities
│   │   ├── __init__.py      # Service package exports
│   │   ├── audio.py         # Audio processing logic
│   │   ├── file_management.py # File operations
│   │   ├── lyrics_service.py  # Lyrics processing
│   │   ├── musicbrainz_service.py # MusicBrainz integration
│   │   └── youtube_service.py # YouTube integration
│   │
│   ├── tasks/               # Asynchronous task processing
│   │   ├── __init__.py      # Task package exports
│   │   ├── celery_app.py    # Celery configuration
│   │   └── tasks.py         # Task definitions
│   │
│   └── websockets/          # Real-time communication
│       ├── __init__.py      # WebSocket package exports
│       └── websocket.py     # WebSocket implementation
│
├── celery.conf             # Celery worker configuration
├── run_api.sh              # Script to run the API server
├── run_celery.sh           # Script to run the Celery worker
└── requirements.txt        # Python dependencies
```

## Setup & Usage

### Installation

1. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the backend API:
   ```bash
   ./run_api.sh
   ```

3. Start the Celery worker (in a separate terminal):
   ```bash
   ./run_celery.sh
   ```

## Architecture Overview

- **API Layer**: Flask-based REST API endpoints
- **Service Layer**: Core business logic, file management, and external service integration
- **Database Layer**: SQLAlchemy models and database access functions
- **Task Processing**: Async processing using Celery for CPU-intensive operations
- **WebSockets**: Real-time communication for karaoke performance controls

## Authentication

The API uses a simple cookie-based authentication system. Authentication endpoints are provided in the `users.py` module.

## Development

To modify the application:

1. **Adding new endpoints**: Create new files in the `api/` directory and register them in `api/__init__.py`
2. **Adding new models**: Update the `db/models.py` file and run database migrations
3. **Adding new services**: Place them in the `services/` directory and update `services/__init__.py`
4. **Adding async tasks**: Add to `tasks/tasks.py`
