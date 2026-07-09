# Open Karaoke Studio - Project Overview for Gemini

This document provides a comprehensive overview of the Open Karaoke Studio project, detailing its purpose, technical stack, architecture, and key operational procedures.

## Project Overview

Open Karaoke Studio is an open-source, AI-powered karaoke application designed for self-hosting and small gatherings (5-10 users). It automates the creation of karaoke tracks using AI vocal separation and synchronizes playback across multiple devices in real-time.

**Key Features:**
*   **AI Vocal Separation:** Uses Demucs/Roformer (via PyTorch) to extract vocals and instrumentals from any audio file or YouTube URL.
*   **Real-time Synchronization:** WebSockets ensure that the host display (Stage), performer controls, and lyrics are perfectly in sync across all devices.
*   **Session Management:** Isolated karaoke sessions with unique join codes and queue management.
*   **Asynchronous Processing:** Robust background task handling with Celery and Redis.

## Technical Stack

*   **Backend:** FastAPI (Python 3.13), Celery, Redis, SQLAlchemy (PostgreSQL/SQLite).
*   **Frontend:** React 19, TypeScript, Vite, Tailwind CSS v4, Shadcn/UI, TanStack Query, Zustand.
*   **Processing:** yt-dlp, Demucs, FFmpeg.

## Architecture

### Monorepo Structure
*   `backend/`: FastAPI application, database models, and Celery jobs.
*   `frontend/`: React application and styling.
*   `cli/`: Go-based CLI for service management (optional).
*   `docs/`: Comprehensive technical documentation.

### WebSocket Architecture (CRITICAL)
There are exactly **two** WebSocket endpoints:
1.  `/ws/jobs`: Global real-time updates for background tasks (downloading, separation).
2.  `/ws/session/{session_id}`: Unified session state (queue, player state, performance controls).

**Constraint:** All session state MUST be isolated using `session_id`. Never use global dictionaries for transient session data.

### Processing Flow
1.  **Request:** User submits a YouTube URL or file.
2.  **Job:** REST API creates a `Song` record and triggers a Celery job.
3.  **Processing:** `yt-dlp` downloads audio → `Demucs` separates tracks → `FFmpeg` post-processes.
4.  **Feedback:** Real-time progress is broadcast over `/ws/jobs`.
5.  **Storage:** Files are stored in `karaoke_library/{song_id}/`.

## Development Workflow

### Initial Setup
Run `./setup.sh` to install system dependencies, `pnpm`, and set up the backend virtual environment.

### Running the Application
The recommended way to run all services is via tmux:
```bash
./scripts/dev-tmux.sh
```
This starts:
*   **Pane 0.0:** Backend API (FastAPI) - Hot-reloads.
*   **Pane 0.1:** Frontend (Vite) - Hot-reloads.
*   **Pane 0.2:** Celery Worker - **Does NOT hot-reload.**

### Key Commands
*   **Backend (cd backend/ && source venv/bin/activate):**
    *   `pytest` - Run tests.
    *   `black app/ && isort app/` - Format code.
    *   `python3 -m alembic upgrade head` - Apply migrations.
*   **Frontend (cd frontend/):**
    *   `pnpm run type-check` - Primary signal for correctness.
    *   `pnpm run check` - Format + Lint + Type-check.
    *   `pnpm run fix` - Auto-fix linting and formatting.

## Engineering Standards

### Backend (Python)
*   **Logging:** Use `logger = logging.getLogger(__name__)`. Never use `print()` or `current_app.logger`.
*   **Error Handling:** Use `app.exceptions` types and the `@handle_api_error` decorator.
*   **Typing:** All function signatures must have complete type hints.

### Frontend (TypeScript/React)
*   **Logging:** Use `createLogger(namespace)` from `@/lib/logger`. Do not use `console.log`.
*   **State:** TanStack Query for server state; Zustand for client/UI state.
*   **Components:** Prefer Shadcn/UI primitives and Tailwind v4 utility classes.

## Critical Constraints & Gotchas
*   **Celery Restart:** After modifying any code in `backend/app/jobs/` or separation engines, the Celery worker **must** be manually restarted.
*   **Virtual Environment:** Backend commands must run with the `venv` activated.
*   **Session Isolation:** Always key transient performance/queue state by `session_id`.
