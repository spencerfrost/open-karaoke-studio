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
- `docs.md` (`backend/app/**`, `frontend/src/**`, `docs/**`) — which domain doc each code area updates, and how docs are written.

## Documentation

The docs are a VitePress site in `docs/` (`cd docs && pnpm run build`).

- **[docs/architecture.md](docs/architecture.md)** — Overview and map of the domain docs
- **[docs/domains/](docs/domains/)** — One doc per slice (ingestion, song library, lyrics, sessions, player/stage, platform): how it works, diagrams, known debt
- **[docs/features.md](docs/features.md)** — What a user can do
- **[docs/api/](docs/api/)**, **[docs/websocket-protocol.md](docs/websocket-protocol.md)** — Endpoint and message reference
- **[docs/tech-debt.md](docs/tech-debt.md)** · **[docs/roadmap.md](docs/roadmap.md)**
- **[docs/plans/](docs/plans/)** — Working plans (not published on the site)
