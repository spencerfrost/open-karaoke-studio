# Open Karaoke Studio - Copilot Instructions

This is a personal karaoke application for friends and family, not a production SaaS. Use best practices but optimize for simplicity over enterprise-scale concerns - we typically have 5-10 concurrent users maximum.

This is a monorepo karaoke application with React 19 frontend and FastAPI backend, using WebSockets for real-time multi-device synchronization.

We use FastAPI for both REST APIs and WebSocket endpoints. When working with WebSockets, always use the FastAPI implementation in `backend/app/ws/`.

WebSocket state must be session-isolated using session_id as the key. Never use global state dictionaries for performance controls or player state - always scope state to individual karaoke sessions.

We use TanStack Query for server state management and Zustand for client-side state. API calls should use the `useApiQuery` and `useApiMutation` hooks from `frontend/src/hooks/api/useApi.ts`.

Backend commands must be prefixed with `source /mnt/ssd-data/spencer/code/open-karaoke-studio/backend/venv/bin/activate &&` to ensure the virtual environment is active.

The dev environment runs via `./scripts/dev-tmux.sh` and is typically already running - do not start dev servers unless explicitly asked. Celery workers do not hot-reload and require manual restart after backend changes.

We use ShadCN/UI components with Tailwind CSS for styling. Forms use React Hook Form with Zod validation schemas.

Audio processing uses Demucs for vocal/instrumental separation via Celery background jobs. Audio playback uses Web Audio API with synchronized controls across devices via WebSocket.