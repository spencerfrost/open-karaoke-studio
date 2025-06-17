# Development Commands for Open Karaoke Studio

Open Karaoke Studio is designed as a **LOCAL NETWORK** karaoke party app where one device hosts the service and multiple devices connect to it.

## 🎉 Main Development Command

```bash
./scripts/dev.sh
```

**This is all you need!** - Starts all services configured for local network access:

- Backend API binds to `0.0.0.0:5123` (accessible from other devices)
- Frontend runs in host mode on `0.0.0.0:5173`
- Celery worker for background audio processing
- Auto-detects your IP address and configures frontend accordingly
- Other devices can connect via `http://YOUR_IP:5173`

## 🔧 Alternative Commands

### Localhost Only Mode (Single Device Development)

```bash
./scripts/dev-localhost.sh
```

Use this only when developing alone and don't need network access.

### Network Testing

```bash
./scripts/network-test.sh
```

Check connectivity and get URLs for sharing with other devices.

### Individual Services (Manual)

If you prefer separate terminals:

```bash
# Terminal 1: Backend API
cd backend && ./run_api.sh

# Terminal 2: Celery Worker
cd backend && ./run_celery.sh

# Terminal 3: Frontend (Host Mode)
cd frontend && pnpm run host

# Terminal 3: Frontend (Localhost Only)
cd frontend && pnpm dev
```

### Docker (Production-like Testing)

```bash
docker-compose up
```

## 🌐 Network Setup for Karaoke Parties

### Typical Usage Scenario:

1. **Host Device** (laptop/desktop): Runs the Open Karaoke Studio server
2. **Participant Devices** (phones, tablets, laptops): Connect to the host's IP address
3. **Everyone** can browse songs, add to queue, and control playback from their device

### Network Requirements:

- All devices must be on the **same local network** (same WiFi)
- Host device should have a **static IP** or IP reservation for consistency
- Firewall may need to allow incoming connections on ports **5173** and **5123**

### Firewall Setup (if needed):

```bash
# Linux (ufw)
sudo ufw allow 5173
sudo ufw allow 5123

# macOS: System Preferences > Security & Privacy > Firewall > Allow Node & Python
```

## What's Different Now

✅ **Simplified scripts**: Just 3 essential scripts instead of 12+
✅ **Better Python tooling**: pylance/pylint work perfectly in the `backend/` directory
✅ **Better JavaScript tooling**: ESLint/TypeScript work perfectly in the `frontend/` directory
✅ **No workspace complexity**: Each service uses its native tooling
✅ **Local network ready**: Perfect for karaoke parties with multiple devices

## Recommended Workflow

**For karaoke parties (most common):** `./scripts/dev.sh`
**For solo development:** `./scripts/dev-localhost.sh`
**For troubleshooting:** `./scripts/network-test.sh`

## Service URLs

- **Frontend**: http://192.168.50.112:5173 _(or your IP)_
- **Backend API**: http://192.168.50.112:5123 _(or your IP)_
- **Celery Worker**: Runs in background (check logs for status)

Your Docker setup remains unchanged and still works great for production-like testing!
