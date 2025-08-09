#!/bin/bash
# Development script - starts frontend, backend API, and Celery worker
# Configured for LOCAL NETWORK access (karaoke party setup)
#
# Usage:
#   ./dev.sh          # Start with frontend in development mode (default)
#   ./dev.sh --build  # Start with frontend built for production

# Parse command line arguments
BUILD_FRONTEND=false
for arg in "$@"; do
    case $arg in
        --build)
            BUILD_FRONTEND=true
            shift
            ;;
        *)
            # Unknown option
            ;;
    esac
done

if [ "$BUILD_FRONTEND" = true ]; then
    echo "🎤 Starting Open Karaoke Studio (Local Network Mode - Production Build)..."
else
    echo "🎤 Starting Open Karaoke Studio (Local Network Mode - Development Mode)..."
fi

# Auto-detect the machine's IP address for external access
HOST_IP=$(ip addr show | grep 'inet ' | grep -v '127.0.0.1' | head -1 | awk '{print $2}' | cut -d'/' -f1)
echo "📡 Detected host IP: $HOST_IP"

# Create/update the frontend .env.local file with the correct backend URL
echo "VITE_BACKEND_URL=http://$HOST_IP:5123" >frontend/.env.local
echo "✅ Frontend configured to connect to: http://$HOST_IP:5123"

# Function to cleanup background processes
cleanup() {
  echo "🛑 Shutting down services..."
  kill $(jobs -p) 2>/dev/null
  exit 0
}

# Trap Ctrl+C
trap cleanup INT

# Start backend API
echo "📡 Starting backend API..."
(cd backend && ./run_api.sh) 2>&1 | sed 's/^/[API] /' &
API_PID=$!

# Wait a moment for backend to start
sleep 2

# Start Celery worker
echo "⚙️  Starting Celery worker..."
(cd backend && ./run_celery.sh) 2>&1 | sed 's/^/[CELERY] /' &
CELERY_PID=$!

# Wait a moment for Celery to start
sleep 2

# Start frontend
if [ "$BUILD_FRONTEND" = true ]; then
    echo "🏗️  Building frontend for production..."
    (cd frontend && pnpm run build) 2>&1 | sed 's/^/[FRONTEND-BUILD] /' &
    BUILD_PID=$!
    wait $BUILD_PID # Wait for the build to complete
    echo "🌐 Starting frontend preview server..."
    (cd frontend && pnpm run preview --host 0.0.0.0 --port 5192) 2>&1 | sed 's/^/[FRONTEND-PREVIEW] /' &
    FRONTEND_PID=$!
else
    echo "🌐 Starting frontend (dev mode)..."
    (cd frontend && pnpm run host --port 5192) 2>&1 | sed 's/^/[FRONTEND] /' &
    FRONTEND_PID=$!
fi

echo "✅ All services started!"
echo ""
echo "🌐 LOCAL NETWORK ACCESS:"

if [ "$BUILD_FRONTEND" = true ]; then
    echo "   🎤 Main Device:     http://localhost:5192 (Production Build)"
    echo "   📱 Other Devices:   http://$HOST_IP:5192"
else
    echo "   🎤 Main Device:     http://localhost:5192 (Development Mode)"
    echo "   📱 Other Devices:   http://$HOST_IP:5192"
fi

echo "   🔧 Backend API:     http://$HOST_IP:5123"
echo ""
echo "📋 Background services:"
echo "   API Server (PID: $API_PID)"
echo "   Celery Worker (PID: $CELERY_PID)"
echo "   Frontend Server (PID: $FRONTEND_PID)"
echo ""
echo "🎉 Ready for karaoke party! Other devices can now connect."
echo "Press Ctrl+C to stop all services"

# Wait for any background job to finish
wait
