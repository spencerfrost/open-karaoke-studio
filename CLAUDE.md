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
pnpm run check                # Format, lint, type-check
pnpm run fix                  # Auto-fix issues
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
- **Pane 0.0**: Backend API (FastAPI/Uvicorn)
- **Pane 0.1**: Frontend (Vite)
- **Pane 0.2**: Celery worker

```bash
# API server (pane 0.0)
tmux capture-pane -t open-karaoke:0.0 -p | tail -20                              # Check logs
tmux send-keys -t open-karaoke:0.0 C-c && sleep 2 && tmux send-keys -t open-karaoke:0.0 "./run_api.sh" Enter  # Restart

# Celery worker (pane 0.2)
tmux capture-pane -t open-karaoke:0.2 -p | tail -20                              # Check logs
tmux send-keys -t open-karaoke:0.2 C-c && sleep 2 && tmux send-keys -t open-karaoke:0.2 "./run_celery.sh" Enter  # Restart
```

## Development Conventions

### Backend
- **Logging**: Use `logger = logging.getLogger(__name__)` pattern (critical for Celery jobs where `print()` is invisible)
- **Style**: Black + isort formatting, type hints required
- **Errors**: Use `app.exceptions` types, `@handle_api_error` decorator, `exc_info=True` in logs

### Frontend
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
2. **Celery Hot-Reload**: Does NOT auto-reload - manually restart after backend changes
3. **Virtual Environment**: Required for all backend commands
4. **Scale**: Optimized for 5-10 concurrent users, not enterprise

## Common Gotchas

- **Celery changes not applied**: Restart Celery worker manually
- **Backend import errors**: Activate venv (`source venv/bin/activate`)
- **WebSocket issues**: Verify `session_id` is passed correctly
- **Global state bugs**: All session state must be session-isolated
- **Celery debugging**: Check `logs/celery.log` (console output not visible)
