# Open Karaoke Studio - Project Structure

## Root Directory
```
/
├── frontend/           # React TypeScript application
├── backend/           # Python Flask API and services
├── docs/              # Documentation
├── scripts/           # Development scripts
├── karaoke_library/   # Processed songs storage
├── temp_downloads/    # Temporary file processing
├── .github/           # GitHub workflows
└── setup.sh          # Automated setup script
```

## Frontend Structure (`frontend/`)
```
frontend/
├── src/
│   ├── components/    # React components
│   ├── hooks/         # Custom React hooks
│   ├── pages/         # Route components
│   ├── services/      # API client services
│   ├── stores/        # Zustand state stores
│   ├── types/         # TypeScript type definitions
│   └── utils/         # Utility functions
├── public/            # Static assets
├── package.json       # Dependencies and scripts
└── vite.config.ts     # Vite configuration
```

## Backend Structure (`backend/`)
```
backend/
├── app/
│   ├── api/           # Flask API endpoints
│   ├── config/        # Configuration management
│   ├── db/            # Database models and operations
│   ├── jobs/          # Celery background jobs
│   ├── repositories/  # Data access layer
│   ├── schemas/       # Pydantic models
│   ├── services/      # Business logic services
│   ├── utils/         # Utility functions
│   └── websockets/    # WebSocket handlers
├── scripts/           # Maintenance and utility scripts
├── tests/             # Test suite
├── logs/              # Application logs
├── requirements.txt   # Python dependencies
└── run_api.sh        # API server startup script
```

## Key Services & Components

### Backend Services
- **SongService**: Song management and metadata
- **AudioService**: Vocal separation with Demucs
- **YouTubeService**: YouTube integration and downloads
- **LyricsService**: Lyrics search and management
- **FileService**: File system operations
- **JobsService**: Background job management

### Frontend Components
- **SongLibrary**: Main library interface
- **UploadWorkflow**: File upload and processing
- **JobsMonitor**: Real-time job status tracking
- **Player**: Audio playback controls
- **SearchInterface**: Song and artist search

### Database Models
- **DbSong**: Song metadata and file paths
- **DbJob**: Background job tracking
- **User**: User management (future)
- **KaraokeQueueItem**: Karaoke session queue

## Important Directories
- **karaoke_library/**: Processed songs with vocals/instrumentals
- **logs/**: Application logs (app.log, celery.log, etc.)
- **docs/**: Comprehensive documentation
- **scripts/**: Development and maintenance utilities