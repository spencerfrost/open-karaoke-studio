# Open Karaoke Studio - Backend Documentation

**Version**: 2025.1
**Last Updated**: June 15, 2025
**Status**: Production Ready

## Overview

The Open Karaoke Studio backend is a sophisticated Flask-based Python application that powers a complete karaoke platform. It features AI-powered vocal separation, multi-source metadata enrichment, real-time queue management, and comprehensive background job processing.

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Redis (for background jobs)
- FFmpeg (for audio processing)
- Optional: CUDA-capable GPU (for faster audio processing)

### Installation

```bash
cd backend/
pip install -r requirements.txt
alembic upgrade head
```

### Running the Application

```bash
# Start the API server
./run_api.sh

# Start background workers (separate terminal)
./run_celery.sh
```

The API will be available at `http://localhost:5000`

## 🏗️ Architecture

### Core Components

- **API Layer** - 35 REST endpoints across 8 blueprints
- **Service Layer** - 14 business logic services with clean interfaces
- **Data Layer** - SQLAlchemy ORM with 4 core models
- **Background Jobs** - Celery-based async processing
- **Real-time Communication** - WebSocket integration for live updates

### Key Features

- **🎵 Song Management** - Upload, process, and organize karaoke tracks
- **🤖 AI Vocal Separation** - Demucs-powered instrumental/vocal isolation
- **📺 YouTube Integration** - Direct video download and processing
- **🎨 Rich Metadata** - Multi-source enrichment (YouTube, iTunes, MusicBrainz)
- **⚡ Real-time Queue** - Live karaoke session management
- **👥 User System** - Authentication and personalization
- **📊 Background Processing** - Non-blocking audio processing with progress tracking
- **🛡️ Robust Error Handling** - Standardized error responses with specific error codes and context (Updated June 2025)

## 📖 Documentation Structure

### 🏗️ Architecture Documentation

- **[Service Layer Design](service-layer-design.md)** - Business logic organization and patterns
- **[Database Design](database-design.md)** - Schema design and data access patterns

#### Service Architecture

- **[Song Service](services/song-service.md)** - Core song operations and synchronization
- **[YouTube Service](services/youtube-service.md)** - YouTube integration and video processing
- **[File Service](services/file-service.md)** - File system operations and organization
- **[Metadata Service](services/metadata-service.md)** - Multi-source metadata processing
- **[Audio Service](services/audio-service.md)** - Demucs integration and vocal separation
- **[Lyrics Service](services/lyrics-service.md)** - Lyrics fetching and validation
- **[iTunes Service](services/itunes-service.md)** - iTunes API integration and cover art
- **[Background Jobs](services/background-jobs.md)** - Unified job processing and progress tracking

#### Integration Workflows

- **[YouTube Workflow](integrations/youtube-workflow.md)** - Complete YouTube-to-karaoke processing flow

### API Documentation

- **[API Overview](api/README.md)** - Complete REST API reference
- **[Error Handling Guide](../../api/error-handling.md)** - Comprehensive error response patterns and debugging (New June 2025)
- **[Songs API](api/songs.md)** - Song management endpoints
- **[Jobs API](api/jobs.md)** - Background job control
- **[Queue API](api/queue.md)** - Real-time karaoke queue
- **[Users API](api/users.md)** - Authentication and user management
- **[Metadata API](api/metadata.md)** - Search and discovery

### Feature Documentation

- **[Song Processing](features/song-processing.md)** - Complete audio processing workflow
- **[Background Jobs](features/background-jobs.md)** - Async processing system
- **[Queue Management](features/queue-management.md)** - Real-time karaoke features
- **[Search & Discovery](features/search.md)** - Multi-source search functionality

### Development Documentation

- **[Development Setup](development/setup.md)** - Local development environment
- **[Testing Guide](development/testing.md)** - Test strategies and execution
- **[Contributing](development/contributing.md)** - Code standards and workflows
- **[Debugging](development/debugging.md)** - Common issues and solutions

### Deployment Documentation

- **[Configuration](deployment/configuration.md)** - Environment variables and settings
- **[Docker Deployment](deployment/docker.md)** - Container deployment guide
- **[Monitoring](deployment/monitoring.md)** - Logging and observability

## 🔍 Key Statistics

| Metric                    | Value                        |
| ------------------------- | ---------------------------- |
| **Total Python Files**    | 156 files                    |
| **Lines of Code**         | 15,000+ (application code)   |
| **API Endpoints**         | 35 endpoints                 |
| **Service Modules**       | 14 services                  |
| **Database Tables**       | 4 core models                |
| **Test Coverage**         | 6,500+ lines of tests        |
| **External Integrations** | YouTube, iTunes, MusicBrainz |

## 🛠️ Technology Stack

### Core Framework

- **Flask** - Web framework with blueprint architecture
- **SQLAlchemy + Alembic** - Database ORM and migrations
- **Celery + Redis** - Background job processing
- **Flask-SocketIO** - Real-time WebSocket communication

### Audio Processing

- **Demucs** - AI-powered vocal separation
- **PyTorch** - Machine learning framework
- **yt-dlp** - YouTube video/audio extraction
- **FFmpeg** - Audio format conversion

### Data Sources

- **YouTube API** - Video metadata and download
- **iTunes Store API** - Official track metadata
- **MusicBrainz** - Open music database

## 🚨 Common Operations

### Adding a Song

1. **POST** `/api/youtube/download` - Queue YouTube video for processing
2. Background job downloads video and extracts audio
3. Demucs separates vocals and instrumental tracks
4. iTunes API enriches metadata
5. Song appears in library via **GET** `/api/songs`

### Managing Queue

1. **POST** `/karaoke-queue/` - Add song to performance queue
2. WebSocket broadcasts queue changes to all clients
3. **PUT** `/karaoke-queue/reorder` - Reorder queue items
4. **DELETE** `/karaoke-queue/{id}` - Remove items

### Monitoring Jobs

1. **GET** `/api/jobs/` - View all background jobs
2. WebSocket provides real-time progress updates
3. **POST** `/api/jobs/{id}/cancel` - Cancel running jobs

## 🔧 Maintenance

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head
```

### Log Management

```bash
# View API logs
tail -f logs/app.log

# View Celery worker logs
tail -f logs/celery.log
```

### Health Checks

- **API Health**: `GET /api/songs` (should return 200)
- **Job Queue**: `GET /api/jobs/status` (check active jobs)
- **Database**: Check `karaoke.db` file exists and is writable

## 🐛 Troubleshooting

### Common Issues

1. **No GPU detected** - Audio processing will use CPU (slower but functional)
2. **YouTube downloads failing** - Check yt-dlp version and network connectivity
3. **Jobs stuck in pending** - Ensure Celery worker is running
4. **Database locked** - Check for long-running transactions or WAL file issues

### Debug Mode

```bash
export FLASK_ENV=development
export LOG_LEVEL=DEBUG
./run_api.sh
```

## 📋 Development Workflow

1. **Feature Development** - Work in feature branches
2. **Testing** - Run `pytest` before commits
3. **Database Changes** - Create Alembic migrations
4. **Documentation** - Update relevant docs
5. **Deployment** - Use Docker containers for production

## 🤝 Contributing

See [Contributing Guide](development/contributing.md) for:

- Code standards and style guide
- Testing requirements
- Pull request process
- Architecture decision records

## 📞 Support

For issues and questions:

- **Code Issues**: Check [debugging guide](development/debugging.md)
- **API Questions**: See [API documentation](api/README.md)
- **Architecture Questions**: Review [architecture overview](architecture/overview.md)

---

**Next Steps**: Choose a documentation section above based on your needs, or continue with the [Architecture Overview](architecture/overview.md) for a deeper understanding of the system design.
