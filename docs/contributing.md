# Contributing

How to run Open Karaoke Studio from source and work on it. To just run it, see
[Self-Hosting](/self-hosting).

## Setup

**You need:** Python 3.13, Node.js 20+ with pnpm, Postgres, Redis, FFmpeg and tmux. A CUDA GPU is
optional but makes separation much faster.

```bash
git clone https://github.com/spencerfrost/open-karaoke-studio.git
cd open-karaoke-studio

cp .env.example .env    # set JWT_SECRET_KEY, SECRET_KEY, ADMIN_USERNAME, ADMIN_PASSWORD, DATABASE_URL

cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
cd ../frontend && pnpm install && cd ..

./scripts/dev-tmux.sh   # API, frontend and Celery worker, one tmux pane each
```

On its first start the API creates an admin from `ADMIN_USERNAME` and `ADMIN_PASSWORD` (at least
8 characters). Sign in with it under **Hosting tonight? Sign in**, then add hosts on
`/admin/users`. Once an admin exists the two variables are ignored;
[`backend/scripts/manage_users.py`](https://github.com/spencerfrost/open-karaoke-studio/blob/master/backend/scripts/manage_users.py)
creates accounts and resets passwords by hand.

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| API | http://localhost:5123 |
| API docs (Swagger) | http://localhost:5123/docs |

The API and frontend reload when files change. The Celery worker doesn't: restart its pane after
changing anything it runs.

## Tests and checks

```bash
# Backend (from backend/, with the venv active)
pytest
black app/ && isort app/

# Frontend (from frontend/)
pnpm run type-check
pnpm run lint:check
pnpm run format
pnpm test:run

# Docs (from docs/): fails on dead links
pnpm run build
```

## Where things are

| Path | What's there |
|------|--------------|
| `backend/app/api/` | REST routers |
| `backend/app/ws/` | The two WebSocket endpoints: `/ws/jobs` and `/ws/session/{session_id}` |
| `backend/app/services/`, `repositories/` | Business logic and database access, including the separation engines |
| `backend/app/jobs/` | Celery tasks: audio, lyrics, enrichment |
| `backend/alembic/versions/` | Database migrations |
| `frontend/src/features/` | One folder per area: library, songs, lyrics, session, queue, player, stage, performance, admin, demo, tour |
| `frontend/src/stores/`, `services/` | Zustand stores and the REST and WebSocket clients |
| `tv-app/` | The Android TV app for the NVIDIA Shield |
| `cli/` | `oks-cli`, a Go tool for running the dev services |
| `showcase/` | The showcase video, made with Remotion |
| `docs/` | This site |

[Architecture](/architecture) explains how the pieces fit, and links to one doc per area.

## The rule that matters most

Everything about a session (player state, performance controls, the queue) is stored by
`session_id`. There is no global state shared between sessions. The
[WebSocket protocol](/websocket-protocol) has the details.

## Making changes

When a change alters behaviour that a doc describes, update that doc in the same commit: the
area's doc in `docs/domains/`, its page in `docs/api/` for an endpoint, the
[WebSocket protocol](/websocket-protocol) for a message, and [Features](/features) for anything a
user can see.
