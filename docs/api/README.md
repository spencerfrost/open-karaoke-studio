# API Documentation

Open Karaoke Studio provides a comprehensive REST API for programmatic access to all functionality.

## 📋 API Overview

The API is organized into logical endpoints for different system components:

### Current API Endpoints
- **[Songs API](songs.md)** - Song management and processing
- **[Jobs API](jobs.md)** - Background job monitoring and control
- **[Queue API](queue.md)** - Real-time karaoke queue management
- **[Metadata API](metadata.md)** - Search and discovery functionality
- **[Authentication API](authentication.md)** - User management (if enabled)

### API Examples
- **[Usage Examples](examples/README.md)** - Practical code samples
- **[Sample Responses](examples/sample-responses/)** - Real API response data

## 🚀 Quick Start

### Base URL
```
http://localhost:5000/api
```

### Authentication
Currently, the API operates without authentication for local development. Production deployments may implement authentication.

### Content Type
All API endpoints accept and return `application/json` unless otherwise specified.

## 📖 Detailed Documentation

The existing backend documentation contains comprehensive API details:

**→ [Complete API Reference](../architecture/backend/api/README.md)**

This includes:
- All 35 REST endpoints across 8 blueprints
- Request/response schemas
- Error handling patterns
- Integration examples

## 🔧 API Categories

### Core Operations
- **Song Management** - Upload, process, and organize tracks
- **Background Processing** - Monitor and control async jobs
- **File Operations** - Download and manage generated files

### Real-time Features  
- **Queue Management** - Live karaoke session control
- **WebSocket Updates** - Real-time progress and status
- **Event Broadcasting** - Cross-client synchronization

### Metadata & Search
- **Multi-source Search** - YouTube, iTunes, and local search
- **Metadata Enrichment** - Automatic song information
- **Discovery Features** - Browse and filter capabilities

## 💡 Integration Examples

### Basic Song Processing
```bash
# Upload and process a song
curl -X POST http://localhost:5000/api/songs \
  -F "file=@song.mp3"

# Check processing status  
curl http://localhost:5000/api/jobs/status

# Download results
curl http://localhost:5000/api/songs/{id}/download/instrumental
```

### YouTube Integration
```bash
# Import from YouTube
curl -X POST http://localhost:5000/api/youtube/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://youtube.com/watch?v=VIDEO_ID"}'
```

## 📚 Related Documentation

- **[Architecture Overview](../architecture/backend/README.md)** - Backend system design
- **[Feature Documentation](../features/README.md)** - Implementation details
- **[Development Guide](../development/guides/api-development.md)** - API development patterns

---

**Note**: This API documentation section provides an overview and quick start. The comprehensive API reference is maintained in the [backend architecture documentation](../architecture/backend/api/README.md) where it's kept in sync with the codebase.
