# CLAUDE.md

## Project Overview

Open Karaoke Studio is a self-hosted AI-powered karaoke app for small gatherings (5–10 users):
- YouTube download + AI vocal separation (Demucs)
- Real-time WebSocket synchronization
- Session-based queue management
- Background processing (Celery)

Don't take shortcuts for the sake of simplicity. Don't aim for enterprise-level solutions, but don't cut corners due to the app's small size either.

**Stack**: FastAPI + React 19 + TypeScript | SQLite/PostgreSQL + Redis | Vite + Tailwind CSS v4

**Monorepo** with independent frontend/backend services.

## Critical Invariant

**All session state (player state, performance controls, queue) MUST be keyed by `session_id`. NEVER use global state dictionaries.** Full WebSocket detail in `.claude/rules/websocket.md`.

## Scale

Optimized for 5–10 concurrent users, not enterprise.

## Development Environment (applies everywhere)

- Backend: `http://0.0.0.0:5123` · Frontend: `http://localhost:5173`
- Services usually already run via tmux. **Do NOT start dev servers unless explicitly asked.**
- **NEVER restart API/frontend via tmux** — they hot-reload automatically on file changes. (Celery does NOT hot-reload — see `.claude/rules/backend.md`.)
- tmux session `open-karaoke`, window 0 (`services`): pane 0.0 = API, 0.1 = Frontend, 0.2 = Celery.

```bash
# Capture logs (console output for Celery is only visible here / in logs/celery.log)
tmux capture-pane -t open-karaoke:0.0 -p | tail -20   # API server
tmux capture-pane -t open-karaoke:0.1 -p | tail -20   # Frontend
tmux capture-pane -t open-karaoke:0.2 -p | tail -20   # Celery worker

# Setup
./setup.sh                    # Initial setup (once)
./scripts/dev-tmux.sh         # Start all services
```

## Path-Scoped Rules

Topic conventions live in `.claude/rules/` and load automatically when Claude reads matching files:
- `backend.md` (`backend/**`) — venv, pytest, style, logging, errors, DB/Alembic, Celery.
- `frontend.md` (`frontend/**`) — pnpm commands, logging, state, components.
- `websocket.md` (`backend/app/ws/**`, `frontend/src/{services,stores}/**`) — endpoints + session isolation.

## Documentation

- **[FEATURES.md](FEATURES.md)** — Feature inventory with user stories (24 features across 8 domains)
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — WebSocket design, processing pipeline, DB schema, state management
- **[TECH-DEBT.md](TECH-DEBT.md)** — Known issues and tech debt (21 items by severity)
- **[ROADMAP.md](ROADMAP.md)** — Future improvements and feature ideas
- **[docs/](docs/)** — Detailed guides for complex topics (future)
