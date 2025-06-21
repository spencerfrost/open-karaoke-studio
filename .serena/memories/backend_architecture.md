# Backend Architecture Patterns

## Service Layer Architecture
The backend follows a layered architecture:

### API Layer (`backend/app/api/`)
- **Blueprint Structure**: Each domain has its own blueprint (songs, jobs, lyrics, etc.)
- **Error Handling**: All endpoints use `@handle_api_error` decorator
- **Validation**: Request validation with Pydantic schemas
- **Response Format**: Consistent JSON responses with proper HTTP status codes

### Service Layer (`backend/app/services/`)
- **Business Logic**: Core application logic separated from API concerns
- **Interfaces**: Abstract interfaces for testability and modularity
- **Dependency Injection**: Services injected via constructor or method parameters

### Repository Layer (`backend/app/repositories/`)
- **Data Access**: Database operations abstracted from business logic
- **ORM Handling**: SQLAlchemy session management
- **Query Optimization**: Efficient database queries

### Database Layer (`backend/app/db/`)
- **Models**: SQLAlchemy ORM models in `models/` directory
- **Operations**: Direct database functions in `song_operations.py`
- **Migrations**: Alembic for schema versioning

## Key Patterns

### Error Handling Strategy
- Custom exception hierarchy in `exceptions.py`
- Structured error responses with error codes
- Comprehensive logging with context information

### Job Processing
- Celery for asynchronous task processing
- WebSocket updates for real-time progress
- Event-driven architecture with EventBus

### File Management
- `FileService` for file system operations
- Organized directory structure per song
- Multiple file format support (audio, images)