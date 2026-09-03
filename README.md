<div align="center">

<img src="docs/images/logo.png" alt="Open Karaoke Studio" width="140" />

# Open Karaoke Studio

**Turn any YouTube song into a karaoke track with AI vocal separation — then run the whole party from everyone's phones.**

A self-hosted, full-stack karaoke platform. Songs are downloaded, split into isolated stems by a GPU-accelerated ML pipeline, and analyzed for chords, vocal range, and loudness. At showtime, one screen hosts the session while performers join by QR code to queue songs and control the mix — all synchronized in real time over WebSockets.

[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-strict-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PyTorch](https://img.shields.io/badge/PyTorch-Demucs%20%2B%20Roformer-EE4C2C?logo=pytorch&logoColor=white)](https://pytorch.org)
[![Celery](https://img.shields.io/badge/Celery-Redis-37814A?logo=celery&logoColor=white)](https://docs.celeryq.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

</div>

---

## Why This Project

Most songs never got an official karaoke version. This started as a fix for that and grew into a full distributed system: a background ML pipeline, a real-time multi-device sync layer, and a browser audio engine that mixes separated stems live.

Built and maintained solo, end to end — frontend, backend, audio DSP, and infrastructure — including two significant mid-flight migrations: Flask → FastAPI, and Socket.IO → native WebSockets.

**Deliberately not enterprise scale.** It targets 5–10 concurrent users in a living room, and the architecture makes that trade-off explicitly rather than reaching for patterns the use case doesn't justify.

---

## Features

### Library & Processing
- **YouTube → karaoke** — Search YouTube Music, download any track, and separate it automatically. No manual audio work.
- **Three-track separation** — The default pipeline chains Demucs (`htdemucs_ft`) → Roformer → de-noise to produce *independent* lead vocal, backing vocal, and instrumental stems. Running Roformer on vocals-only audio eliminates instrumental bleed-through.
- **Seven pluggable separation engines** — Interchangeable implementations behind a common interface, from fast 2-stem Demucs to multi-stage three-track variants built on different Roformer models (InstVoc Duality V2, Mel-Roformer-Viperx-1143). GPU-accelerated with CPU fallback.
- **Automatic audio analysis** — beat-synced guitar chord detection, vocal range detection via librosa `pyin` (e.g. G2–E5), and RMS loudness measurement — all in the same background job.
- **Metadata enrichment** — MusicBrainz, iTunes, and AcoustID lookups for artwork, credits, and release data.

### Live Performance
- **Multi-device sessions** — One host on the big screen; performers join by session code or QR from their phones. Queue songs, reorder, skip.
- **Real-time sync** — Player state, queue, and performance controls propagate to every connected device instantly over WebSocket.
- **Web Audio mixing** — Separated stems play simultaneously through independent gain nodes, so singers can dial lead vocals, backing vocals, and instrumental separately, mid-song.
- **Loudness normalization** — A dedicated normalization gain node applies the server-measured per-song correction (`10^(dB/20)`) at playback, so no one gets blasted between tracks.
- **Synchronized lyrics** — LRC lyrics auto-fetched from multiple providers, displayed with auto-scroll, tap-to-seek, count-in cues, and per-song timing offset.
- **Guitar chord carousel** — Upcoming chords displayed in-player for anyone playing along.
- **Session resilience** — A 30-second grace period on host disconnect means a browser refresh doesn't end the party for everyone.
- **JWT authentication** — Admin actions (deleting songs, reprocessing audio) gated behind auth.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend — React 19 · TypeScript · Vite · Tailwind v4      │
│  TanStack Query (server state) · Zustand (client state)     │
│  Web Audio API multi-stem playback engine                   │
└────────────────────────┬────────────────────────────────────┘
                         │  REST + WebSocket
┌────────────────────────▼────────────────────────────────────┐
│  Backend — FastAPI · Uvicorn · SQLAlchemy · JWT auth        │
└──────────┬──────────────────┬───────────────────┬───────────┘
           │                  │                   │
    ┌──────▼──────┐   ┌───────▼──────┐   ┌────────▼────────┐
    │ PostgreSQL  │   │    Redis     │   │  Celery Worker  │
    │  (SQLite    │   │   (broker)   │   │                 │
    │   in dev)   │   └──────────────┘   └────────┬────────┘
    └─────────────┘                               │
                              ┌───────────────────▼──────────────────┐
                              │ yt-dlp → Demucs/Roformer (PyTorch)   │
                              │        → librosa analysis            │
                              └──────────────────────────────────────┘
```

### Design decisions worth calling out

**Exactly two WebSocket endpoints.** `/ws/jobs` carries global job progress; `/ws/session/{session_id}` carries *all* karaoke functionality for one session. Resisting the urge to add an endpoint per feature is what keeps session isolation tractable.

**Every piece of session state is keyed by `session_id`.** No global state dictionaries anywhere. This is the project's hard invariant — it's what lets multiple independent karaoke sessions share one server without leaking state into each other.

**The ML pipeline never blocks a request.** Downloads, GPU separation, and analysis all run as Celery tasks with progress streamed back over WebSocket, so a 5-minute separation job is a progress bar, not a hung UI.

**Separation quality is an interface problem.** Rather than hardcoding one model, engines implement a shared interface and are selected per job — which made it possible to evaluate seven approaches against real audio and change the default without touching the pipeline.

### Processing pipeline

```
YouTube URL
   ├─ Phase 1  Download          (0–30%)   yt-dlp → original.mp3
   ├─ Phase 2  Separation        (30–90%)  Demucs → Roformer → de-noise
   │                                       → vocals / backing_vocals / instrumental
   └─ Phase 3  Analysis          (90–100%) chords · vocal range · loudness
                                           → broadcast completion to all clients
```

Roughly 2–5 minutes per song on GPU, 10–20 on CPU.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19, TypeScript (strict), Vite, Tailwind CSS v4, Shadcn/UI |
| **Client state** | TanStack Query (server state), Zustand (client state), React Hook Form + Zod |
| **Audio (browser)** | Web Audio API — multi-stem playback with per-track gain |
| **Backend** | FastAPI, Uvicorn, SQLAlchemy, Alembic, JWT (python-jose) |
| **Database** | PostgreSQL (production) · SQLite (development) |
| **Jobs & realtime** | Celery, Redis, native WebSockets |
| **Audio ML/DSP** | Demucs, Roformer (PyTorch), librosa, pydub |
| **Ingestion** | yt-dlp, YouTube Music, MusicBrainz, iTunes, AcoustID |

**At a glance:** 117 backend modules · 269 frontend modules · 788 backend tests · 37 database migrations · 17 API routers.

---

## Getting Started

**Prerequisites:** Python 3.13+, Node.js 20+ with pnpm, Redis, and FFmpeg. A CUDA-capable GPU is optional but cuts separation time by ~4x.

```bash
git clone https://github.com/spencerfrost/open-karaoke-studio.git
cd open-karaoke-studio

./setup.sh              # creates venvs, installs deps, runs migrations
./scripts/dev-tmux.sh   # starts API, frontend, and Celery worker
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:5123 |
| API docs (Swagger) | http://localhost:5123/docs |

A `docker-compose.yml` is included for Postgres and Redis.

### Development

```bash
# Backend (from backend/, with venv active)
pytest                        # run the test suite
alembic upgrade head          # apply migrations

# Frontend (from frontend/)
pnpm run type-check           # TypeScript
pnpm run lint:check           # ESLint
pnpm build                    # production build
```

### Repository layout

```
backend/
  app/
    api/                 17 routers (songs, sessions, queue, lyrics, jobs, …)
    services/            business logic, incl. separation_engines/
    ws/                  WebSocket endpoints + connection manager
    jobs/                Celery tasks
  alembic/versions/      37 migrations
  tests/                 788 tests
frontend/
  src/
    components/          library, player, queue, lyrics
    features/            feature-scoped modules
    hooks/               API + domain hooks
    stores/              Zustand state
    services/            REST + WebSocket clients
docs/                    architecture, features, API reference, roadmap
```

---

## Documentation

- **[Architecture](docs/architecture.md)** — WebSocket design, processing pipeline, database schema, state management
- **[Features](docs/features.md)** — Full feature inventory with user stories
- **[WebSocket Protocol](docs/websocket-protocol.md)** — Message types and session isolation rules
- **[API Reference](docs/api-reference.md)** — REST endpoints
- **[Tech Debt](docs/tech-debt.md)** — Known issues, prioritized and tracked openly
- **[Roadmap](docs/roadmap.md)** — What's next

---

## License

MIT — see [LICENSE](./LICENSE).
