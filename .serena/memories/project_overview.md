# Open Karaoke Studio - Project Overview

## Purpose
Open Karaoke Studio is an open-source AI-powered karaoke studio web application that makes it easy to generate instrumental versions of favorite songs using AI-powered vocal separation.

## Key Features
- **Upload & Process**: Upload songs and let AI extract vocals
- **Vocal Separation**: Clean vocal extraction from any song using Demucs AI
- **Create Instrumentals**: High-quality instrumental tracks for karaoke
- **Song Library**: User-friendly library management
- **Song Search**: Search and download from YouTube
- **Asynchronous Processing**: Background job processing with Celery
- **Lyric Timing Solutions**: AI-generated and aligned lyrics
- **Self-hosting**: Personal karaoke library and player

## Architecture
- **Frontend**: React 19 + TypeScript, Vite, Tailwind CSS, Shadcn/UI
- **Backend**: Python + Flask, Demucs AI, SQLAlchemy, Celery + Redis
- **Database**: SQLite with SQLAlchemy ORM
- **Task Queue**: Celery with Redis broker
- **Deployment**: Docker Compose for production

## Project Structure
- `frontend/` - React application
- `backend/` - Python Flask API and services
- `docs/` - Comprehensive documentation
- `scripts/` - Development and utility scripts
- `karaoke_library/` - Processed song files storage