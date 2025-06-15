# Architecture Overview

This section contains comprehensive documentation about Open Karaoke Studio's system architecture, covering both frontend and backend components and their integration.

## 📋 Architecture Documentation

### High-Level Design
- **[Project Overview](project-overview.md)** - System design, technology stack, and component breakdown
- **[System Integration](integration/README.md)** - How frontend and backend communicate

### Component Architecture
- **[Backend Architecture](backend/README.md)** - Python/Flask API, services, and data layer
- **[Frontend Architecture](frontend/README.md)** - React/TypeScript application structure
- **[External Integrations](integration/external-services.md)** - Third-party service integration

## 🏗️ System Overview

Open Karaoke Studio is built as a modern, service-oriented web application:

### Frontend (React/TypeScript)
- **Framework**: React 19 with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS + Shadcn/UI components
- **State Management**: TanStack Query for API data
- **Architecture**: Feature-based component organization

### Backend (Python/Flask)
- **Framework**: Flask with service-oriented architecture
- **Processing**: Demucs for AI-powered vocal separation
- **Database**: SQLite with SQLAlchemy ORM
- **Background Jobs**: Celery with Redis
- **APIs**: RESTful endpoints with WebSocket real-time updates

### Key Integrations
- **YouTube**: Video download and metadata via yt-dlp
- **iTunes**: Official metadata enrichment
- **Audio Processing**: Demucs with GPU/CPU support
- **File Storage**: Organized library structure

## 🎯 Architectural Principles

### Clean Architecture
- **Service Layer**: Business logic separated from controllers
- **Dependency Inversion**: High-level modules independent of low-level details
- **Interface Segregation**: Services depend only on needed interfaces

### Scalability Design
- **Async Processing**: Background jobs for CPU-intensive tasks
- **Real-time Updates**: WebSocket communication for live features
- **Modular Services**: Each service handles one business domain

### User Experience Focus
- **Progressive Enhancement**: Core features work, advanced features enhance
- **Responsive Design**: Mobile-first approach with desktop optimization
- **Error Resilience**: Graceful degradation and clear error messaging

## 📊 System Statistics

| Component | Details |
|-----------|---------|
| **Backend Files** | 156 Python files, 15,000+ lines of code |
| **API Endpoints** | 35 REST endpoints across 8 blueprints |
| **Services** | 14 specialized business logic services |
| **Database Tables** | 4 core models with rich metadata |
| **Frontend Components** | Feature-based organization |
| **Test Coverage** | 6,500+ lines of comprehensive tests |

## 🔄 Data Flow

### Song Processing Workflow
1. **Upload/Import** → File validation and metadata extraction
2. **Background Processing** → Demucs vocal separation
3. **Metadata Enrichment** → iTunes/YouTube API integration  
4. **Storage** → Organized file structure with database records
5. **Real-time Updates** → WebSocket notifications to frontend

### User Interaction Flow
1. **Frontend Request** → React component triggers API call
2. **API Layer** → Flask route delegates to service layer
3. **Service Layer** → Business logic execution
4. **Data Layer** → Database operations via SQLAlchemy
5. **Response** → JSON data returned to frontend

## 🚀 Getting Started with Architecture

### For New Developers
1. **Start with** [Project Overview](project-overview.md) for high-level understanding
2. **Deep dive** into [Backend Architecture](backend/README.md) for server-side details
3. **Explore** [Frontend Architecture](frontend/README.md) for client-side patterns
4. **Understand** [Integration Patterns](integration/README.md) for full-stack context

### For Contributors
1. **Review** architectural principles and patterns
2. **Follow** established service layer patterns
3. **Maintain** separation of concerns
4. **Test** both unit and integration levels

### For Deployers
1. **Understand** component dependencies
2. **Configure** external service integrations
3. **Monitor** system health and performance
4. **Scale** based on usage patterns

---

**Next Steps**: 
- **New to the project?** → [Project Overview](project-overview.md)
- **Backend development?** → [Backend Architecture](backend/README.md)
- **Frontend development?** → [Frontend Architecture](frontend/README.md)
- **Full-stack understanding?** → [System Integration](integration/README.md)
