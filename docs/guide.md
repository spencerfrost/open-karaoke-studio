# Getting Started Guide

Complete guide to setting up and using Open Karaoke Studio.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Installation](#installation)
3. [Basic Usage](#basic-usage)
4. [Adding Songs](#adding-songs)
5. [Running a Karaoke Session](#running-a-karaoke-session)
6. [Multi-Device Setup](#multi-device-setup)
7. [Troubleshooting](#troubleshooting)

---

## Quick Start

**Prerequisites:**
- Linux/macOS/WSL2 (Windows)
- Python 3.10+
- Node.js 18+
- pnpm (package manager)
- PostgreSQL (production) or SQLite (development)

**Fast Setup:**

```bash
# Clone repository
git clone https://github.com/spencerfrost/open-karaoke-studio.git
cd open-karaoke-studio

# Run setup script
./setup.sh

# Start development servers
./scripts/dev-tmux.sh
```

The setup script will:
1. Create Python virtual environment
2. Install backend dependencies
3. Install frontend dependencies
4. Set up database
5. Initialize configuration

After setup, the app will be available at:
- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:5123
- **API Docs:** http://localhost:5123/docs

---

## Installation

### 1. System Requirements

**Minimum:**
- 4GB RAM
- 10GB+ disk space
- Dual-core CPU

**Recommended:**
- 8GB+ RAM
- 50GB+ disk space (for song library)
- Quad-core CPU or GPU (CUDA-capable)

### 2. Dependencies

**Install system packages:**

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.10 python3-pip python3-venv \
  nodejs npm postgresql ffmpeg git

# macOS (with Homebrew)
brew install python@3.10 node postgresql ffmpeg git

# Install pnpm globally
npm install -g pnpm
```

### 3. Clone and Configure

```bash
# Clone repository
git clone https://github.com/spencerfrost/open-karaoke-studio.git
cd open-karaoke-studio

# Copy environment template
cp .env.example .env

# Edit configuration (optional)
nano .env
```

**Key Environment Variables:**

```bash
# Database
DATABASE_URL=sqlite:///backend/karaoke.db  # SQLite for dev
# DATABASE_URL=postgresql://user:pass@localhost/karaoke  # PostgreSQL for production

# Backend
FLASK_SECRET_KEY=your-secret-key-here
CELERY_BROKER_URL=redis://localhost:6379/0

# Paths
LIBRARY_PATH=/path/to/karaoke_library
```

### 4. Database Setup

**For SQLite (development):**
```bash
cd backend
source venv/bin/activate
alembic upgrade head
```

**For PostgreSQL (production):**
```bash
# Create database
createdb karaoke

# Run migrations
cd backend
source venv/bin/activate
alembic upgrade head
```

### 5. Start Services

**Development (Tmux):**
```bash
./scripts/dev-tmux.sh
```

This starts:
- Frontend dev server (port 5173)
- Backend API server (port 5123)
- Celery worker (background jobs)
- Redis (message broker)

**Production (separate terminals):**

```bash
# Terminal 1: Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 5123

# Terminal 2: Celery Worker
cd backend
source venv/bin/activate
celery -A app.jobs.celery_app worker --loglevel=info

# Terminal 3: Frontend Build
cd frontend
pnpm build
# Serve with nginx or similar
```

---

## Basic Usage

### First Time Setup

1. **Open the app:** Navigate to http://localhost:5173
2. **Create a session:** Click "Host Session"
3. **Note the session code:** 4-character code (e.g., "ABCD")
4. **Add songs:** Click "Add Song" or browse library

### Interface Overview

**Main Pages:**
- **Library** - Browse and search your song collection
- **Add Song** - Import songs from YouTube
- **Stage** - Main karaoke player and queue
- **Performance Controls** - Mobile-friendly playback controls

**Key Features:**
- Real-time queue management
- Synchronized playback across devices
- Adjustable vocals/instrumental volume
- Synced lyrics with timing controls

---

## Adding Songs

### Method 1: YouTube Music Search (Recommended)

1. Click **"Add Song"** from navigation
2. Enter **artist and song name** in search
3. **Browse results:**
   - Artist results (click to see full catalog)
   - Song results (with album info)
4. Click **"Add"** on desired song
5. **Lyrics search** (automatic or manual):
   - Choose from available lyrics
   - Preview before selecting
   - Skip if no lyrics needed
6. **Processing begins:**
   - YouTube download
   - AI vocal separation
   - Metadata extraction

**Processing Time:**
- With GPU: 2-5 minutes
- With CPU: 10-20 minutes

### Method 2: YouTube Video URL

1. Go to **"Add Song"**
2. Switch to **"Video Search"** tab
3. Enter **YouTube URL**
4. **Fill in metadata manually:**
   - Title
   - Artist
   - Album (optional)
5. Click **"Add Song"**

### Method 3: Local File Upload

**Note:** Direct file upload is planned but not yet implemented. See [Roadmap](ROADMAP.md).

---

## Running a Karaoke Session

### As Host (Main Device)

1. **Create Session:**
   ```
   Navigate to http://localhost:5173
   Click "Host Session"
   Note the 4-character code (e.g., "ABCD")
   ```

2. **Add Songs to Queue:**
   ```
   Browse library
   Click "Add to Queue" on any song
   Enter singer name
   Songs appear in queue sidebar
   ```

3. **Start Playing:**
   ```
   Click song in queue to start
   Or click "Play Now" from library
   Fullscreen mode recommended
   ```

4. **Control Playback:**
   ```
   Play/Pause
   Adjust vocals volume
   Adjust lyrics timing
   Change lyrics size
   ```

### As Performer (Secondary Device)

1. **Join Session:**
   ```
   Navigate to http://localhost:5173
   Click "Join Session"
   Enter 4-character code
   Select "Performer" device type
   ```

2. **Performance Controls:**
   ```
   Access /controls page
   Control vocals volume
   Adjust lyrics timing
   See current song and queue
   ```

3. **Mobile Usage:**
   ```
   Use phone/tablet as controller
   Adjust settings during performance
   Changes sync to main screen
   ```

---

## Multi-Device Setup

### Network Configuration

**Same Network (Easy):**
```
Host: http://192.168.1.100:5173
Other devices: Join using host's IP
Session Code: ABCD
```

**Different Networks (Advanced):**
```
Requires port forwarding or VPN
Not recommended for security reasons
```

### Device Roles

**Stage (Main Display):**
- Connected to TV/projector
- Shows player, lyrics, queue
- Host controls

**Performer (Mobile/Tablet):**
- Personal device for singer
- Performance controls page
- Adjust volume/timing

**Controller (Anyone):**
- Browse and add songs
- View queue
- Limited controls

### Session Sharing

**QR Code (Planned):**
```
Display QR code on stage view
Scan to join session
Automatic device detection
```

**Manual Code Entry:**
```
Share 4-character code
Join via /join page
Select device type
```

---

## Troubleshooting

### Common Issues

**1. Songs Not Processing**

```bash
# Check Celery worker
cd backend
source venv/bin/activate
celery -A app.jobs.celery_app inspect active

# Restart worker
# Ctrl+C to stop, then:
celery -A app.jobs.celery_app worker --loglevel=info
```

**2. No Lyrics Found**

- Try different search terms
- Search manually at [LRCLIB](https://lrclib.net)
- Paste lyrics manually
- Some songs don't have synced lyrics

**3. Audio Playback Issues**

- Check browser console for errors
- Ensure files exist in `karaoke_library/{song_id}/`
- Try different browser (Chrome/Edge recommended)
- Check file permissions

**4. WebSocket Connection Failed**

```bash
# Check backend is running
curl http://localhost:5123/api/health

# Check WebSocket endpoint
wscat -c ws://localhost:5123/ws/jobs

# Verify CORS settings in backend/app/main.py
```

**5. Database Errors**

```bash
# Reset database (WARNING: Deletes all data)
cd backend
source venv/bin/activate
alembic downgrade base
alembic upgrade head

# Or create fresh database
rm karaoke.db
alembic upgrade head
```

### Performance Issues

**Slow Processing:**
- GPU highly recommended (CUDA)
- Consider using `demucs` engine (faster)
- Close other applications
- Check system resources

**Slow UI:**
- Clear browser cache
- Reduce lyrics size
- Disable auto-scroll temporarily
- Check network latency

**High CPU Usage:**
- Normal during audio processing
- Reduce concurrent jobs
- Adjust Celery worker count

### Getting Help

**Documentation:**
- [Architecture](ARCHITECTURE.md) - System design
- [Features](FEATURES.md) - Feature details
- [Tech Debt](TECH-DEBT.md) - Known issues
- [API Reference](api-reference.md) - API docs

**Community:**
- GitHub Issues - Bug reports and features
- Discussions - Questions and support

---

## Next Steps

**After Setup:**

1. **Build Your Library:**
   - Add 10-20 popular songs
   - Test different genres
   - Verify lyrics quality

2. **Test Session:**
   - Host a test session
   - Join from another device
   - Try performance controls

3. **Customize:**
   - Adjust default settings
   - Configure audio quality
   - Set up persistent storage

4. **Production Deployment:**
   - Switch to PostgreSQL
   - Set up reverse proxy
   - Configure SSL/HTTPS
   - Set up backups

**Learn More:**

- [Architecture Overview](ARCHITECTURE.md) - How it works
- [API Documentation](api-reference.md) - API reference
- [Contributing Guide](contributing.md) - Contribute to project

---

## Related Documentation

- [Features](FEATURES.md) - Complete feature list
- [Architecture](ARCHITECTURE.md) - Technical architecture
- [Roadmap](ROADMAP.md) - Future plans
- [API Reference](api-reference.md) - API documentation
