#!/bin/bash
# Development script using tmux - starts frontend, backend API, FastAPI sessions, and Celery worker
# Each service runs in its own tmux pane for better control and debugging
#
# Usage:
#   ./dev-tmux.sh          # Start with frontend in development mode (default)
#   ./dev-tmux.sh --build  # Start with frontend built for production

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
    echo "🎤 Starting Open Karaoke Studio with tmux (Local Network Mode - Production Build)..."
else
    echo "🎤 Starting Open Karaoke Studio with tmux (Local Network Mode - Development Mode)..."
fi

# Auto-detect the machine's IP address for external access
HOST_IP=$(ip addr show | grep 'inet ' | grep -v '127.0.0.1' | head -1 | awk '{print $2}' | cut -d'/' -f1)
echo "📡 Detected host IP: $HOST_IP"

# Create/update the frontend .env.local file with the correct backend URLs
echo "VITE_BACKEND_URL=http://$HOST_IP:5123" >frontend/.env.local
echo "VITE_FASTAPI_URL=http://$HOST_IP:5124" >>frontend/.env.local
echo "✅ Frontend configured to connect to:"
echo "   Flask API: http://$HOST_IP:5123"
echo "   FastAPI Sessions: http://$HOST_IP:5124"

# Session name
SESSION_NAME="open-karaoke-studio"

# Kill existing session if it exists
tmux has-session -t $SESSION_NAME 2>/dev/null && tmux kill-session -t $SESSION_NAME

# Create new tmux session with quad layout
echo "📡 Creating tmux session with quad layout..."
tmux new-session -d -s $SESSION_NAME -n "services" -c "$(pwd)"

# Enable mouse mode for easier scrolling and copying
tmux set-option -t $SESSION_NAME mouse on

# Start Flask backend API in the first pane
echo "📡 Starting Flask backend API in pane 0..."
tmux send-keys -t $SESSION_NAME:services.0 "cd backend" C-m
tmux send-keys -t $SESSION_NAME:services.0 "./run_api.sh" C-m

# Split horizontally to create second pane for Celery worker (following original pattern)
echo "⚙️  Adding Celery worker in pane 1..."
tmux split-window -h -t $SESSION_NAME:services -c "$(pwd)/backend"
tmux send-keys -t $SESSION_NAME:services.1 "sleep 1" C-m # Wait for backend to start
tmux send-keys -t $SESSION_NAME:services.1 "./run_celery.sh" C-m

# Split the right pane (Celery) vertically to create third pane for FastAPI sessions
echo "🎪 Adding FastAPI session server in pane 2..."
tmux split-window -v -t $SESSION_NAME:services.1 -c "$(pwd)/backend"
tmux send-keys -t $SESSION_NAME:services.2 "source venv/bin/activate" C-m
tmux send-keys -t $SESSION_NAME:services.2 "cd fastapi_poc" C-m
tmux send-keys -t $SESSION_NAME:services.2 "sleep 1" C-m # Wait for Flask to start
tmux send-keys -t $SESSION_NAME:services.2 "hypercorn main:app --bind 0.0.0.0:5124 --reload" C-m

# Split the left pane (Flask backend) vertically to create fourth pane for frontend
echo "🌐 Adding frontend in pane 3..."
tmux split-window -v -t $SESSION_NAME:services.0 -c "$(pwd)/frontend"
# The new pane becomes the active one, so we can send commands to it directly
# But let's be explicit and target the bottom-left pane
tmux send-keys -t $SESSION_NAME:services "sleep 2" C-m # Wait for backend services to start

if [ "$BUILD_FRONTEND" = true ]; then
    echo "🏗️  Building frontend for production..."
    tmux send-keys -t $SESSION_NAME:services "pnpm run build" C-m
    tmux send-keys -t $SESSION_NAME:services "sleep 3" C-m # Wait for build to complete
    tmux send-keys -t $SESSION_NAME:services "pnpm run preview --host 0.0.0.0 --port 5192" C-m
else
    tmux send-keys -t $SESSION_NAME:services "pnpm run host" C-m
fi

# Adjust pane sizes for equal quad layout (like the original script)
# Make the backend pane (left side) take up 50% of width  
tmux resize-pane -t $SESSION_NAME:services.0 -x 50%
# Make the celery and fastapi panes split the right side equally
tmux resize-pane -t $SESSION_NAME:services.1 -y 50%

# Create a status window for info
echo "📊 Adding status window..."
tmux new-window -t $SESSION_NAME -n "status" -c "$(pwd)"
tmux send-keys -t $SESSION_NAME:status "clear" C-m
tmux send-keys -t $SESSION_NAME:status "echo '🎤 Open Karaoke Studio - Development Environment (Dual Backend)'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '================================================================'" C-m
tmux send-keys -t $SESSION_NAME:status "echo ''" C-m

if [ "$BUILD_FRONTEND" = true ]; then
    tmux send-keys -t $SESSION_NAME:status "echo '🏗️  Frontend Mode: Production Build (preview server)'" C-m
else
    tmux send-keys -t $SESSION_NAME:status "echo '🚀 Frontend Mode: Development (dev server with HMR)'" C-m
fi

tmux send-keys -t $SESSION_NAME:status "echo ''" C-m
tmux send-keys -t $SESSION_NAME:status "echo '🌐 LOCAL NETWORK ACCESS:'" C-m

if [ "$BUILD_FRONTEND" = true ]; then
    tmux send-keys -t $SESSION_NAME:status "echo '   🎤 Main Device:        http://localhost:5192'" C-m
    tmux send-keys -t $SESSION_NAME:status "echo '   📱 Other Devices:      http://$HOST_IP:5192'" C-m
else
    tmux send-keys -t $SESSION_NAME:status "echo '   🎤 Main Device:        http://localhost:5192'" C-m
    tmux send-keys -t $SESSION_NAME:status "echo '   📱 Other Devices:      http://$HOST_IP:5192'" C-m
fi

tmux send-keys -t $SESSION_NAME:status "echo ''" C-m
tmux send-keys -t $SESSION_NAME:status "echo '🔧 BACKEND SERVICES:'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   🐍 Flask API:          http://$HOST_IP:5123 (songs, jobs, uploads)'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   ⚡ FastAPI Sessions:   http://$HOST_IP:5124 (session management)'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   🎪 Session Test Page:  http://$HOST_IP:5124/session-test'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   📚 FastAPI Docs:       http://$HOST_IP:5124/docs'" C-m
tmux send-keys -t $SESSION_NAME:status "echo ''" C-m
tmux send-keys -t $SESSION_NAME:status "echo '🔌 WEBSOCKET ENDPOINTS:'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   🎭 Sessions:           ws://$HOST_IP:5124/ws/session'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   📋 Jobs (Flask):       ws://$HOST_IP:5123/jobs'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   🎛️  Performance:        ws://$HOST_IP:5124/ws/performance'" C-m
tmux send-keys -t $SESSION_NAME:status "echo ''" C-m
tmux send-keys -t $SESSION_NAME:status "echo '📋 Tmux Controls:'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   Ctrl+B + 0-1:   Switch between windows (services/status)'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   Ctrl+B + o:     Cycle through panes in services window'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   Ctrl+B + arrow: Navigate between panes'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   Ctrl+B + d:     Detach from session'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   Ctrl+B + x:     Kill current pane'" C-m
tmux send-keys -t $SESSION_NAME:status "echo ''" C-m
tmux send-keys -t $SESSION_NAME:status "echo '📱 Pane Layout (Window 0 - services):'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   ┌─────────────┬─────────────┐'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   │    Flask    │   FastAPI   │'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   │  Backend    │  Sessions   │'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   │ (Port 5123) │ (Port 5124) │'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   ├─────────────┼─────────────┤'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   │   Celery    │  Frontend   │'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   │   Worker    │'" C-m

if [ "$BUILD_FRONTEND" = true ]; then
    tmux send-keys -t $SESSION_NAME:status "echo '   │             │ Preview Srv │'" C-m
else
    tmux send-keys -t $SESSION_NAME:status "echo '   │             │  Dev Server │'" C-m
fi

tmux send-keys -t $SESSION_NAME:status "echo '   │             │ (Port 5192) │'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   └─────────────┴─────────────┘'" C-m
tmux send-keys -t $SESSION_NAME:status "echo ''" C-m
tmux send-keys -t $SESSION_NAME:status "echo '🎉 Ready for karaoke party with session management!'" C-m
tmux send-keys -t $SESSION_NAME:status "echo ''" C-m
tmux send-keys -t $SESSION_NAME:status "echo '💡 Migration Strategy:'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   📱 Frontend connects to BOTH backends'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   🎪 Session features → FastAPI (new, fast)'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   🎵 Songs/Jobs/etc → Flask (existing, stable)'" C-m
tmux send-keys -t $SESSION_NAME:status "echo ''" C-m
tmux send-keys -t $SESSION_NAME:status "echo '🧪 Quick Tests:'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   Flask Health:       curl http://$HOST_IP:5123/api/health'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   FastAPI Health:     curl http://$HOST_IP:5124/api/health'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   Session Test:       http://$HOST_IP:5124/session-test'" C-m
tmux send-keys -t $SESSION_NAME:status "echo ''" C-m
tmux send-keys -t $SESSION_NAME:status "echo '💡 Tips:'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   - Use \"tmux attach -t $SESSION_NAME\" to reattach'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   - Use \"tmux kill-session -t $SESSION_NAME\" to stop all services'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   - Switch to services window (Ctrl+B + 0) to see all logs'" C-m

# Select the services window as default
tmux select-window -t $SESSION_NAME:services

echo ""
echo "✅ Tmux session '$SESSION_NAME' created with DUAL BACKEND setup!"
echo ""
echo "🌐 LOCAL NETWORK ACCESS:"

if [ "$BUILD_FRONTEND" = true ]; then
    echo "   🎤 Main Device:        http://localhost:5192 (Production Build)"
    echo "   📱 Other Devices:      http://$HOST_IP:5192"
else
    echo "   🎤 Main Device:        http://localhost:5192 (Development Mode)"
    echo "   📱 Other Devices:      http://$HOST_IP:5192"
fi

echo ""
echo "🔧 BACKEND SERVICES:"
echo "   🐍 Flask API:          http://$HOST_IP:5123 (existing features)"
echo "   ⚡ FastAPI Sessions:   http://$HOST_IP:5124 (session management)"
echo "   🎪 Session Test Page:  http://$HOST_IP:5124/session-test"
echo "   📚 FastAPI Docs:       http://$HOST_IP:5124/docs"
echo ""
echo "📋 Tmux Commands:"
echo "   Attach to session:  tmux attach -t $SESSION_NAME"
echo "   Kill all services:  tmux kill-session -t $SESSION_NAME"
echo ""

if [ "$BUILD_FRONTEND" = true ]; then
    echo "🏗️  Frontend built for production and served via preview server"
    echo ""
fi

echo "🎯 DUAL BACKEND STRATEGY:"
echo "   📱 Frontend connects to BOTH Flask (5123) + FastAPI (5124)"
echo "   🎪 Session management → FastAPI (new, 30x faster)"
echo "   🎵 Songs/Jobs/Uploads → Flask (existing, stable)"
echo ""

echo "🚀 Attaching to tmux session now..."

# Attach to the session
tmux attach -t $SESSION_NAME