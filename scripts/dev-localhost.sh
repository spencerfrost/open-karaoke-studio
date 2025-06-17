#!/bin/bash
# Development script - LOCALHOST ONLY mode (for single-device development)

echo "🚀 Starting Open Karaoke Studio (Localhost Only)..."

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
cd backend && ./run_api.sh 2>&1 | sed 's/^/[API] /' &
API_PID=$!

# Wait a moment for backend to start
sleep 2

# Start Celery worker
echo "⚙️  Starting Celery worker..."
cd backend && ./run_celery.sh 2>&1 | sed 's/^/[CELERY] /' &
CELERY_PID=$!

# Wait a moment for Celery to start
sleep 2

# Start frontend (localhost only)
echo "🌐 Starting frontend (localhost only)..."
cd ../frontend && pnpm dev 2>&1 | sed 's/^/[FRONTEND] /' &
FRONTEND_PID=$!

echo "✅ All services started!"
echo ""
echo "🔗 Access points (localhost only):"
echo "   Frontend: http://localhost:5173"
echo "   Backend:  http://localhost:5123"
echo ""
echo "📋 Background services:"
echo "   API Server (PID: $API_PID)"
echo "   Celery Worker (PID: $CELERY_PID)"
echo "   Frontend Dev Server (PID: $FRONTEND_PID)"
echo ""
echo "⚠️  Note: This mode only works on this device."
echo "   For karaoke party mode, use: ./scripts/dev.sh"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for any background job to finish
wait
