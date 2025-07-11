# Open Karaoke Studio - Tech Stack

## Frontend Stack
- **Framework**: React 19 + TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS v4.1
- **UI Components**: Shadcn/UI with Radix UI primitives
- **State Management**: Zustand
- **Data Fetching**: TanStack React Query
- **Forms**: React Hook Form with Zod validation
- **Routing**: React Router DOM v7
- **WebSocket**: Socket.IO client
- **Package Manager**: pnpm 10.9

## Backend Stack
- **Framework**: Python + Flask
- **AI Processing**: Demucs (forked version), PyTorch, Torchaudio
- **Database**: SQLite with SQLAlchemy ORM
- **Background Jobs**: Celery with Redis
- **WebSocket**: Flask-SocketIO with eventlet
- **Audio Processing**: yt-dlp, soundfile
- **Data Validation**: Pydantic v2.11+
- **Migration**: Alembic
- **Testing**: pytest, pytest-flask, pytest-cov

## Infrastructure & Tools
- **Database**: SQLite (development), supports PostgreSQL (production)
- **Message Broker**: Redis (for Celery)
- **Containerization**: Docker with docker-compose
- **Code Quality**: 
  - Frontend: ESLint, Prettier, TypeScript strict mode
  - Backend: PyLint, Black, isort
- **Package Management**: 
  - Frontend: pnpm workspaces
  - Backend: pip with requirements.txt