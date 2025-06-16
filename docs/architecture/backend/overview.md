# Backend Architecture Overview

**Last Updated**: June 15, 2025  
**Architecture Version**: 2025.1  

## System Overview

The Open Karaoke Studio backend implements a **modern service-oriented architecture** designed for scalability, maintainability, and real-time performance. The system processes audio content through AI-powered vocal separation while providing rich metadata and real-time collaboration features.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend (React/Vite)                        │
└─────────────┬───────────────────────────────────────────────────┘
              │ HTTP/WebSocket
┌─────────────▼───────────────────────────────────────────────────┐
│                    API Gateway (Flask)                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│
│  │   Songs     │ │    Jobs     │ │   Queue     │ │   Users     ││
│  │     API     │ │     API     │ │     API     │ │     API     ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘│
└─────────────┬───────────────────────────────────────────────────┘
              │
┌─────────────▼───────────────────────────────────────────────────┐
│                   Service Layer                                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│
│  │   YouTube   │ │   iTunes    │ │    Audio    │ │    Song     ││
│  │   Service   │ │   Service   │ │   Service   │ │   Service   ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘│
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│
│  │    Jobs     │ │    File     │ │   Lyrics    │ │  Metadata   ││
│  │   Service   │ │   Service   │ │   Service   │ │   Service   ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘│
└─────────────┬───────────────────────────────────────────────────┘
              │
┌─────────────▼───────────────────────────────────────────────────┐
│                   Data Layer                                    │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│
│  │    Songs    │ │    Jobs     │ │    Users    │ │    Queue    ││
│  │   (SQLite)  │ │  (SQLite)   │ │  (SQLite)   │ │  (SQLite)   ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘│
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                 Background Processing                           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│
│  │   Celery    │ │    Redis    │ │   Demucs    │ │   yt-dlp    ││
│  │   Workers   │ │    Queue    │ │  (Audio AI) │ │ (YouTube)   ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘│
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                 External Services                               │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│
│  │   YouTube   │ │   iTunes    │ │ MusicBrainz │ │  File       ││
│  │     API     │ │ Store API   │ │     API     │ │  System     ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

## Architectural Principles

### 1. **Clean Architecture**
- **Dependency Inversion**: High-level modules don't depend on low-level modules
- **Interface Segregation**: Services depend only on interfaces they use
- **Single Responsibility**: Each component has one reason to change
- **Open/Closed**: Open for extension, closed for modification

### 2. **Service-Oriented Design**
- **14 specialized services** handling distinct business domains
- **Protocol interfaces** enabling dependency injection and testing
- **Service composition** for complex workflows
- **Error boundaries** preventing cascade failures

### 3. **Event-Driven Architecture**
- **WebSocket communication** for real-time updates
- **Background job events** for progress tracking
- **Queue state synchronization** across clients
- **Service decoupling** through async messaging

## Core Components

### API Layer (35 endpoints)
**Purpose**: HTTP interface and request/response handling
**Technology**: Flask with Blueprint architecture
**Responsibilities**:
- Request validation and routing
- Response formatting and serialization
- Error handling and logging
- WebSocket connection management

**Key Blueprints**:
- **Songs API** (11 endpoints) - Core content management
- **Jobs API** (6 endpoints) - Background processing control
- **YouTube API** (2 endpoints) - Video integration
- **Queue API** (4 endpoints) - Real-time karaoke management
- **Users API** (3 endpoints) - Authentication and profiles

### Service Layer (2,447 lines)
**Purpose**: Business logic and external system integration
**Technology**: Interface-driven Python classes
**Responsibilities**:
- Domain logic implementation
- External API integration
- Data transformation and validation
- Cross-cutting concerns (logging, error handling)

**Core Services**:
- **YouTube Service** (691 lines) - Video download and metadata
- **iTunes Service** (499 lines) - Official metadata enrichment
- **Audio Service** (270 lines) - AI-powered vocal separation
- **Song Service** (217 lines) - Content lifecycle management
- **Jobs Service** (216 lines) - Background processing coordination

### Data Layer (4 tables)
**Purpose**: Persistent storage and data modeling
**Technology**: SQLAlchemy ORM with SQLite
**Responsibilities**:
- Data persistence and retrieval
- Relationship management
- Transaction handling
- Schema evolution via migrations

**Core Models**:
- **Songs** (40+ columns) - Rich metadata from multiple sources
- **Jobs** (15+ columns) - Background processing state
- **Users** (7 columns) - Authentication and preferences
- **Queue** (4 columns) - Real-time karaoke queue

### Background Processing
**Purpose**: Non-blocking long-running operations
**Technology**: Celery with Redis broker
**Responsibilities**:
- Audio processing (vocal separation)
- Video downloading and conversion
- Metadata enrichment from external APIs
- Progress reporting and error handling

## Data Flow Patterns

### 1. **Typical Song Creation Flow**
```
User Request → API Validation → YouTube Service → Background Job
     ↓                ↓               ↓              ↓
WebSocket ← Job Updates ← Audio Processing ← Video Download
     ↓                ↓               ↓              ↓
  Client UI ← Song Available ← Database Storage ← File System
```

### 2. **Real-time Queue Management**
```
Queue API → WebSocket Broadcast → All Connected Clients
    ↓              ↓                       ↓
Database → State Sync → Real-time UI Updates
```

### 3. **Metadata Enrichment Pipeline**
```
YouTube Metadata → iTunes API → MusicBrainz → Combined Metadata
       ↓              ↓            ↓              ↓
   Video Info → Official Data → Open Data → Rich Song Profile
```

## Technology Stack

### Core Framework
| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Web Framework** | Flask | Latest | HTTP API and routing |
| **Database ORM** | SQLAlchemy | Latest | Data modeling and queries |
| **Migrations** | Alembic | 1.8.0+ | Schema versioning |
| **Background Jobs** | Celery | 5.0+ | Async task processing |
| **Message Broker** | Redis | Latest | Job queue and caching |
| **WebSockets** | Flask-SocketIO | Latest | Real-time communication |

### Audio Processing
| Component | Technology | Purpose |
|-----------|------------|---------|
| **AI Vocal Separation** | Demucs (Custom Fork) | Audio track isolation |
| **ML Framework** | PyTorch | Neural network processing |
| **Audio Conversion** | FFmpeg | Format conversion and optimization |
| **YouTube Download** | yt-dlp | Video/audio extraction |

### External Integrations
| Service | API | Purpose |
|---------|-----|---------|
| **YouTube** | yt-dlp + YouTube Data API | Video search and download |
| **iTunes Store** | iTunes Search API | Official metadata and artwork |
| **MusicBrainz** | REST API | Open music database |

## Scalability Considerations

### Current Architecture
- **Single-node deployment** with SQLite database
- **Process-based concurrency** via Celery workers
- **Local file storage** for audio content
- **In-memory WebSocket management**

### Scaling Strategies
1. **Database**: Migrate to PostgreSQL for multi-user scenarios
2. **File Storage**: Move to S3/MinIO for distributed storage
3. **Load Balancing**: Multiple API instances behind reverse proxy
4. **Background Processing**: Horizontal Celery worker scaling
5. **Caching**: Redis for metadata and session caching

## Performance Characteristics

### Processing Times
- **Audio Separation**: 30-120 seconds (GPU) / 2-10 minutes (CPU)
- **YouTube Download**: 10-60 seconds depending on video length
- **Metadata Enrichment**: 2-10 seconds per source
- **API Response Times**: <200ms for most endpoints

### Resource Usage
- **Memory**: 512MB base + 2-8GB during audio processing
- **CPU**: Low baseline, high during audio separation
- **Storage**: ~50-200MB per song (3 audio files + metadata)
- **Network**: Burst usage during downloads, low baseline

## Security Model

### Authentication
- **Optional password-based** user system
- **Session-based** authentication (no JWT currently)
- **Public API access** for most endpoints
- **Admin privileges** flag for future use

### File Security
- **Path traversal protection** in download endpoints
- **Library boundary validation** prevents unauthorized access
- **File type restrictions** for uploads and downloads
- **Input sanitization** for metadata fields

### Network Security
- **CORS configuration** for frontend integration
- **Request size limits** for file uploads
- **Rate limiting** considerations for external APIs
- **Error message sanitization** to prevent information leakage

## Monitoring and Observability

### Logging Strategy
- **Structured JSON logging** for production
- **Multiple log levels** (DEBUG, INFO, WARNING, ERROR)
- **Service-specific loggers** for component isolation
- **File and console outputs** for different environments

### Health Monitoring
- **Database connectivity** checks
- **Background job queue** monitoring
- **External service** availability tracking
- **File system** health and capacity

### Performance Metrics
- **Request latency** by endpoint
- **Background job completion** times
- **Error rates** by service
- **Resource utilization** trends

## Development Patterns

### Code Organization
```
app/
├── api/           # HTTP endpoints and routing
├── services/      # Business logic and integrations
├── db/           # Data models and database operations
├── jobs/         # Background task definitions
├── websockets/   # Real-time communication
├── config/       # Environment and settings
└── exceptions/   # Custom error types
```

### Testing Strategy
- **Unit tests** for service layer business logic
- **Integration tests** for API endpoints and workflows
- **Mock external services** for reliable testing
- **Test data factories** for consistent test scenarios

### Configuration Management
- **Environment-based** configuration (dev/test/prod)
- **External configuration** via environment variables
- **Sensible defaults** for development setup
- **Configuration validation** at startup

## Future Architecture Evolution

### Planned Enhancements
1. **Microservices Migration** - Split services into independent deployments
2. **Event Sourcing** - Audit trail and replay capabilities
3. **CQRS Implementation** - Separate read/write models
4. **API Gateway** - Centralized routing and authentication
5. **Distributed Caching** - Redis cluster for metadata

### Technology Upgrades
- **FastAPI Migration** - Modern async Python framework
- **PostgreSQL** - Production-grade database
- **Kubernetes** - Container orchestration
- **Prometheus/Grafana** - Advanced monitoring
- **OpenAPI 3.0** - Comprehensive API documentation

---

**Next Reading**: 
- [Data Models](data-models.md) - Detailed database schema
- [Request Flow](request-flow.md) - How requests move through the system
- [External Integrations](external-integrations.md) - Third-party service details
