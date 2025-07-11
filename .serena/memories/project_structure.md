# Open Karaoke Studio - Project Structure (2025)

## Root Directory
```
/
├── frontend/           # React TypeScript application
├── backend/            # Python Flask API and services
├── docs/               # Documentation
├── scripts/            # Development scripts
├── karaoke_library/    # Processed songs storage
├── temp_downloads/     # Temporary file processing
├── .github/            # GitHub workflows
├── setup.sh            # Automated setup script
```

## Frontend Structure (`frontend/`)
```
frontend/
├── src/
│   ├── components/         # React components (see below for substructure)
│   │   ├── library/        # Song library UI
│   │   ├── player/         # Audio player and visualizations
│   │   ├── upload/         # Upload workflow, steps, dialogs
│   │   ├── queue/          # Karaoke queue management
│   │   ├── lyrics/         # Lyrics display and dialogs
│   │   ├── songs/          # Song cards, details, metadata editing
│   │   │   ├── song-details/
│   │   │   │   ├── metadata-edit/
│   │   ├── forms/          # Form components
│   │   ├── ui/             # Shadcn UI primitives
│   │   ├── layout/         # App layout and navigation
│   ├── hooks/              # Custom React hooks
│   ├── pages/              # Route components
│   ├── services/           # API/websocket client services
│   ├── stores/             # Zustand state stores
│   ├── types/              # TypeScript type definitions
│   ├── utils/              # Utility functions
├── public/                 # Static assets
├── package.json            # Dependencies and scripts
├── vite.config.ts          # Vite configuration
```

## Backend Structure (`backend/`)
```
backend/
├── app/
│   ├── api/                # Flask API endpoints (songs, jobs, users, etc.)
│   ├── config/             # Configuration management (env, logging, etc.)
│   ├── db/
│   │   ├── models/         # SQLAlchemy models (DbSong, DbJob, User, Queue)
│   │   └── database.py     # DB session management
│   ├── jobs/               # Celery background jobs and job event handlers
│   ├── repositories/       # Data access layer (SongRepository, JobRepository)
│   ├── schemas/            # Pydantic models (requests, responses)
│   ├── services/
│   │   ├── interfaces/     # Service interfaces (for DI/testing)
│   │   ├── audio_service.py
│   │   ├── file_service.py
│   │   ├── lyrics_service.py
│   │   ├── metadata_service.py
│   │   ├── youtube_service.py
│   │   ├── youtube_music_service.py
│   │   ├── jobs_service.py
│   ├── tasks/              # Task orchestration (future/experimental)
│   ├── utils/              # Utility functions (error handling, validation, events)
│   ├── websockets/         # WebSocket handlers (jobs_ws, karaoke_queue_ws, etc.)
│   └── main.py             # App entrypoint
├── scripts/                # Maintenance and utility scripts
├── tests/                  # Test suite (integration/unit)
├── logs/                   # Application logs
├── requirements.txt        # Python dependencies
├── run_api.sh              # API server startup script
```

## Key Services & Components

### Backend Services
- **SongRepository**: Song data access
- **JobRepository**: Job data access
- **AudioService**: Vocal separation (Demucs)
- **FileService**: File system operations
- **YouTubeService**: YouTube integration/downloads
- **YouTubeMusicService**: YouTube Music integration
- **LyricsService**: Lyrics search and management
- **MetadataService**: Metadata enrichment (iTunes, etc.)
- **JobsService**: Background job management

### Frontend Components
- **SongLibrary**: Main library interface
- **UploadWorkflow**: File upload and processing
- **JobsMonitor**: Real-time job status tracking
- **Player**: Audio playback controls
- **SearchInterface**: Song and artist search
- **KaraokeQueue**: Queue management UI
- **LyricsDisplay**: Lyrics and timing

### Database Models
- **DbSong**: Song metadata and file paths
- **DbJob**: Background job tracking
- **User**: User management (future)
- **KaraokeQueueItem**: Karaoke session queue

- Pydantic models in `schemas/` are used for API validation/serialization and generally mirror the DB models unless otherwise noted.

## Important Directories
- **karaoke_library/**: Processed songs with vocals/instrumentals
- **logs/**: Application logs (app.log, celery.log, etc.)
- **docs/**: Comprehensive documentation
- **scripts/**: Development and maintenance utilities
