#!/bin/bash
# Development script - starts frontend, backend API, and Celery worker
# Configured for LOCAL NETWORK access (karaoke party setup)

echo "🎤 Starting Open Karaoke Studio (Local Network Mode)..."

# Auto-detect the machine's IP address for external access
HOST_IP=$(hostname -I | awk '{print $1}')
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
echo "🌐 Starting frontend (host mode)..."
(cd frontend && pnpm run host) 2>&1 | sed 's/^/[FRONTEND] /' &
FRONTEND_PID=$!

echo "✅ All services started!"
echo ""
echo "🌐 LOCAL NETWORK ACCESS:"
echo "   🎤 Main Device:     http://localhost:5173"
echo "   📱 Other Devices:   http://$HOST_IP:5173"
echo "   🔧 Backend API:     http://$HOST_IP:5123"
echo ""
echo "📋 Background services:"
echo "   API Server (PID: $API_PID)"
echo "   Celery Worker (PID: $CELERY_PID)"
echo "   Frontend Dev Server (PID: $FRONTEND_PID)"
echo ""
echo "🎉 Ready for karaoke party! Other devices can now connect."
echo "Press Ctrl+C to stop all services"

# Wait for any background job to finish
wait
