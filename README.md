# Open Karaoke Studio

**Self-hosted AI-powered karaoke for small gatherings.**

Open Karaoke Studio lets you build a karaoke library from YouTube, separates vocals with AI, displays synchronized lyrics, and keeps multiple devices in sync in real time. Designed for 5–10 people at a party or event.

## Features

- **YouTube to Karaoke:** Search YouTube Music, download any song, and automatically separate vocals from the instrumental using AI (Demucs, Roformer, or three-track separation)
- **Synchronized Lyrics:** Auto-fetches LRC lyrics from multiple providers; displays them synchronized to music with auto-scroll, tap-to-seek, and timing offset adjustment
- **Multi-Device Sessions:** Host on the main screen, performers join by session code or QR code from their phones to queue songs and control the performance
- **Performance Controls:** Independent volume sliders for vocals, instrumental, and backing vocals; lyrics size; guitar chord display — all synchronized across devices in real time
- **Chord & BPM Analysis:** Automatic chord detection and BPM analysis during processing; guitar chord carousel displays upcoming chords during playback
- **Vocal Range Detection:** Detects the lowest and highest sung notes for each song (e.g. G2–E5); displayed on song cards and in song details
- **Loudness Normalization:** Measures RMS loudness and applies per-song gain correction at playback time so every song plays at a consistent volume
- **Session Resilience:** 30-second grace period on host disconnect so a browser refresh doesn't end the session for everyone
- **Authentication:** JWT-based login; admin actions (delete songs, reprocess audio) are gated behind authentication
- **Queue Management:** Add songs with singer names, reorder, and skip — all reflected instantly on all connected devices
- **Background Processing:** Celery worker handles downloads and separation without blocking the UI; live progress via WebSocket

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19 + TypeScript + Vite + Tailwind CSS v4 |
| UI Components | Shadcn/UI + React Hook Form + Zod |
| State | TanStack Query (server state) + Zustand (client state) |
| Backend | FastAPI + Uvicorn + SQLAlchemy + Alembic |
| Database | PostgreSQL (production) / SQLite (dev) |
| Queue | Celery + Redis |
| Audio AI | Demucs + Audio-Sep Roformer + librosa + pydub |
| Downloader | yt-dlp |

## Getting Started

```bash
# 1. Clone the repo
git clone https://github.com/your-org/open-karaoke-studio.git
cd open-karaoke-studio

# 2. Run initial setup (creates venvs, installs deps, sets up DB)
./setup.sh

# 3. Start all services in a tmux session
./scripts/dev-tmux.sh
```

Services run at:
- Frontend: http://localhost:5173
- Backend API: http://localhost:5123

See [ARCHITECTURE.md](docs/architecture.md) for a full technical overview and [FEATURES.md](docs/features.md) for a complete feature inventory.

## Documentation

- [FEATURES.md](docs/features.md) — Complete feature inventory with user stories
- [ARCHITECTURE.md](docs/architecture.md) — Technical deep-dive: WebSocket design, processing pipeline, database schema
- [TECH-DEBT.md](docs/tech-debt.md) — Known issues prioritized by severity
- [ROADMAP.md](ROADMAP.md) — Future improvements

## Contributing

1. Fork the repository
2. Create a branch off `develop`
3. Implement your change
4. Submit a pull request targeting `develop`

## License

MIT — see [LICENSE](./LICENSE) for details.
