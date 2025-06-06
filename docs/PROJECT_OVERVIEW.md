# Open Karaoke Studio – Project Overview

## Project Summary
Open Karaoke Studio is an open-source, AI-powered web application that enables users to create karaoke tracks by separating vocals from music. It provides a modern, user-friendly interface for uploading songs, processing them with advanced AI models, and managing a personal karaoke library. The project is structured as a monorepo, supporting both a Python/Flask backend and a React/Vite frontend, and is designed for self-hosting and extensibility.

---

## Key Features
### Current Features
- **Upload & Process:** Users can upload songs and initiate AI-powered vocal separation.
- **Vocal Separation:** Utilizes Demucs (PyTorch-based) for high-quality extraction of vocals and instrumentals.
- **Instrumental Creation:** Generates karaoke-ready instrumental tracks.
- **Song Library:** Maintains a searchable, user-friendly library of processed songs.
- **YouTube Integration:** Search for songs on YouTube and automatically generate karaoke tracks.
- **Asynchronous Processing:** Supports queuing and background processing of multiple jobs (Celery planned for production).
- **Modern Web UI:** Fast, responsive interface built with React, Tailwind CSS, and Shadcn components.
- **Self-Hosting:** Designed for easy deployment and personal use.

### Planned Features
- **Settings/Configuration:** User-customizable processing and experience options.
- **Integrated Karaoke Player:** In-app playback with karaoke features.
- **Vocal Guide:** Adjustable original vocal volume for sing-along.
- **Beat Detection & Lyrics Display:** Automatic beat sync and karaoke-style lyrics graphics.
- **Mobile Support:** Upload and manage songs from mobile devices.
- **Audio Effects:** Real-time effects for vocals and instrumentals.

---

## Technology Stack
### Frontend
- **Framework:** React 19 (TypeScript)
- **Build Tool:** Vite
- **Styling:** Tailwind CSS, Shadcn/UI (for accessible, consistent UI components)
- **State/Data:** TanStack Query for API data fetching and caching
- **Component Structure:** Modular, with feature folders (e.g., `songs/`, `upload/`, `ui/`)

### Backend
- **Framework:** Python 3.10+, Flask (RESTful API)
- **Audio Processing:** Demucs (PyTorch), with GPU/CPU support
- **Async Jobs:** Celery (for background processing)
- **Database:** SQLite (with SQLAlchemy models for song metadata)
- **APIs:** Endpoints for file upload, processing, library management, YouTube search/download, lyrics, and metadata enrichment
- **External Integrations:**
  - **YouTube:** yt-dlp for search and download
  - **MusicBrainz:** Metadata enrichment
  - **LRCLIB:** Lyrics fetching

### Infrastructure & Tooling
- **Monorepo:** Managed with `pnpm` (workspace configuration)
- **Cross-Package Scripts:** Unified scripts for setup and running

---

## Architecture & Component Breakdown
### Monorepo Structure
- **Root:** Shared configuration, scripts, and documentation
- **`frontend/`:** React app (Vite, Tailwind, Shadcn, feature-based components)
- **`backend/`:** Flask API, audio processing, async tasking, and service modules
- **`karaoke_library/`:** Stores processed songs and metadata

### Frontend Highlights
- **UI Components:** Modular, reusable (e.g., `Button`, `Alert`, `FileUploader`)
- **Feature Components:**
  - `SongCard`: Displays song info, cover art, and actions
  - `FileUpload`: Handles audio file selection and validation
  - `YouTubeImporter`: Search and import from YouTube
- **Hooks:** Custom hooks for API communication and state management
- **UX:** Loading and error states, responsive design, mobile-first approach

### Backend Highlights
- **Service Modules:**
  - `audio.py`: Handles Demucs-based separation, progress reporting, and error handling
  - `file_management.py`: Manages file storage, directory structure, and metadata
  - `youtube_service.py`: Integrates yt-dlp for YouTube search/download
  - `musicbrainz_service.py`: Fetches and enriches song metadata
  - `lyrics_service.py`: Retrieves lyrics from LRCLIB
- **API Design:** RESTful endpoints for all major operations, with robust error handling
- **Extensibility:** Modular service design for easy feature addition

---

## Notable Implementation Details
- **AI Audio Separation:** Uses Demucs for state-of-the-art source separation, with GPU acceleration if available
- **Async Processing:** Designed for background task queuing (Celery), enabling scalable processing
- **Metadata Enrichment:** Integrates with MusicBrainz and LRCLIB for rich song data and lyrics
- **Error Handling:** Both backend and frontend include comprehensive error reporting and user feedback
- **Security:** Input validation, CORS handling, and safe file operations

---

## Contribution & Deployment
- **Contributing:** Fork, branch, and submit pull requests. See root README for guidelines.
- **Setup:**
  - Backend: Python virtualenv, install requirements, run Flask app
  - Frontend: `pnpm install`, `pnpm run dev`
  - Docker: Use provided Dockerfiles for containerized deployment
- **License:** MIT

---

## Further Resources
- [Root README](./README.md)
- [Frontend README](./frontend/README.md)
- [Backend README](./backend/README.md)

---

*This document is intended as a high-level overview for onboarding, development, and contribution to Open Karaoke Studio. For detailed setup and API documentation, refer to the respective READMEs and code comments.*
