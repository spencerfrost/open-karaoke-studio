# CLAUDE.md

**Serena**: Activate with `activate_project("open-karaoke-studio")` at conversation start for semantic code tools.

## Project Overview

Open Karaoke Studio is a self-hosted AI-powered karaoke application for small gatherings (5-10 users) featuring:
- YouTube download + AI vocal separation (Demucs)
- Real-time WebSocket synchronization
- Session-based queue management
- Background processing (Celery)

**Stack**: FastAPI + React 19 + TypeScript | SQLite/PostgreSQL + Redis | Vite + Tailwind CSS v4

## Architecture

**Monorepo** with independent frontend/backend services.

### WebSocket Architecture (CRITICAL)
**Only TWO WebSocket endpoints:**
1. `/ws/jobs` - Global job status updates
2. `/ws/session/{session_id}` - All karaoke functionality

**All session state MUST be session-isolated using `session_id` as the key. NEVER use global state dictionaries for performance controls, player state, or queue management.**

### Structure
```
backend/app/
├── api/          # REST endpoints
├── ws/           # WebSocket handlers
├── services/     # Business logic
├── repositories/ # Data access
├── db/models/    # SQLAlchemy models
├── schemas/      # Pydantic validation
└── jobs/         # Celery background jobs

frontend/src/
├── components/   # UI (library, player, queue, lyrics)
├── hooks/        # Custom hooks (useApi.ts for API)
├── stores/       # Zustand state
└── services/     # API/WebSocket clients
```

## Development

**Services** (usually already running via tmux):
- Backend: `http://0.0.0.0:5123`
- Frontend: `http://localhost:5173`

**Do not start dev servers unless explicitly asked.**

### Key Commands

```bash
# Setup
./setup.sh                    # Initial setup (once)
./scripts/dev-tmux.sh         # Start all services

# Frontend (cd frontend/)
pnpm run type-check           # TypeScript only (run this first — clean signal)
pnpm run lint:check           # ESLint only
pnpm run format               # Auto-format all files (prettier --write)
pnpm run check                # All three — fails fast on format, noisy with pre-existing issues
pnpm build                    # Production build

# Backend (cd backend/ && source venv/bin/activate)
pytest                        # Run tests
./run_api.sh                  # Start FastAPI
./run_celery.sh               # Start Celery worker
black app/ && isort app/      # Format code

# Database (PostgreSQL - requires DATABASE_URL env var)
python3 -m alembic current    # Show current migration
python3 -m alembic upgrade head  # Apply pending migrations
python3 -m alembic downgrade -1  # Rollback one migration
psql $DATABASE_URL -c "\d songs"  # Inspect table schema
psql $DATABASE_URL -c "SELECT version_num FROM alembic_version"  # Current migration version
```

**CRITICAL: Backend commands require venv activation:**
```bash
# Always activate venv in backend/ directory before running Python commands
cd backend && source venv/bin/activate

# Then run commands (pytest, alembic, etc.)
# The venv must be activated in the same shell session where commands run
```

### Tmux Dev Environment

Services run in tmux session `open-karaoke`, window 0 (`services`) with 3 panes:
- **Pane 0.0**: Backend API (FastAPI/Uvicorn) - **auto-reloads on file changes**
- **Pane 0.1**: Frontend (Vite) - **auto-reloads on file changes**
- **Pane 0.2**: Celery worker - **does NOT auto-reload**

```bash
# Check logs
tmux capture-pane -t open-karaoke:0.0 -p | tail -20  # API server
tmux capture-pane -t open-karaoke:0.1 -p | tail -20  # Frontend
tmux capture-pane -t open-karaoke:0.2 -p | tail -20  # Celery worker
```

**IMPORTANT: DO NOT restart services via tmux commands.** The API and frontend hot-reload automatically in development. If Celery changes are made, ask the user to restart Celery before continuing.

## Development Conventions

### Backend
- **Logging**: Use `logger = logging.getLogger(__name__)` pattern (critical for Celery jobs where `print()` is invisible)
- **Style**: Black + isort formatting, type hints required
- **Errors**: Use `app.exceptions` types, `@handle_api_error` decorator, `exc_info=True` in logs

### Frontend
- **Logging**: Use `createLogger(namespace)` from `@/lib/logger`, NOT console.log
  - Development: All levels visible (debug, info, warn, error)
  - Production: Only warn/error visible (controlled by `VITE_LOG_LEVEL`)
  - Namespace pattern: `createLogger("component:Name")`, `createLogger("service:api")`, `createLogger("store:session")`
- **Style**: Prettier + ESLint, TypeScript strict mode
- **State**: TanStack Query (`useApiQuery`, `useApiMutation`) for server state, Zustand for client state
- **Components**: Shadcn/UI primitives, React Hook Form + Zod for forms

## Processing Flow

```
YouTube URL → yt-dlp → Celery → Demucs → vocals.mp3 + instrumental.mp3
                                       → karaoke_library/{song_id}/
```

## Critical Constraints

1. **Session Isolation**: All WebSocket state keyed by `session_id` (NEVER global)
2. **Celery Hot-Reload**: Does NOT auto-reload - ask user to restart after Celery job changes
3. **Virtual Environment**: Required for all backend commands (Python 3.13)
4. **Scale**: Optimized for 5-10 concurrent users, not enterprise
5. **Service Restarts**: NEVER restart API/frontend via tmux - they hot-reload automatically

## Common Gotchas

- **Celery changes not applied**: Ask user to restart Celery worker before continuing
- **Backend import errors**: Activate venv (`source venv/bin/activate`)
- **WebSocket issues**: Verify `session_id` is passed correctly
- **Global state bugs**: All session state must be session-isolated
- **Celery debugging**: Check `logs/celery.log` (console output not visible)
- **API/Frontend hot-reload**: Both services auto-reload on file changes - never restart via tmux

## Documentation

This file (CLAUDE.md) provides AI assistant context and development workflows. For comprehensive documentation:

- **[FEATURES.md](FEATURES.md)** - Complete feature inventory with user stories (24 features across 8 domains)
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Technical deep-dive: WebSocket design, processing pipeline, database schema, state management
- **[TECH-DEBT.md](TECH-DEBT.md)** - Known issues and tech debt (21 items prioritized by severity)
- **[ROADMAP.md](ROADMAP.md)** - Future improvements and feature ideas organized by theme
- **[docs/](docs/)** - Detailed guides for complex topics (future)
