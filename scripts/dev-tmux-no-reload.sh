#!/bin/bash
# Development script using tmux WITHOUT hot reload
# Starts frontend (production build), backend API (no reload), and Celery worker
# Each service runs in its own tmux pane for better control and debugging
#
# Use this script when you want stable services that don't restart on file changes.
# Useful for testing, debugging, or when hot reload causes issues.
#
# Usage:
#   ./dev-tmux-no-reload.sh

echo "🎤 Starting Open Karaoke Studio with tmux (No Hot Reload Mode)..."

# Auto-detect the machine's IP address for external access
HOST_IP=$(ip addr show | grep 'inet ' | grep -v '127.0.0.1' | head -1 | awk '{print $2}' | cut -d'/' -f1)
echo "📡 Detected host IP: $HOST_IP"

# Create/update the frontend .env.local file with the correct backend URL
echo "VITE_BACKEND_URL=http://$HOST_IP:5123" >frontend/.env.local
echo "✅ Frontend configured to connect to: http://$HOST_IP:5123"

# Session name
SESSION_NAME="open-karaoke-studio"

# Kill existing session if it exists
tmux has-session -t $SESSION_NAME 2>/dev/null && tmux kill-session -t $SESSION_NAME

# Create new tmux session with tiled layout
echo "📡 Creating tmux session with tiled layout..."
tmux new-session -d -s $SESSION_NAME -n "services" -c "$(pwd)"

# Enable mouse mode for easier scrolling and copying
tmux set-option -t $SESSION_NAME mouse on

# Start backend API in the first pane (WITHOUT --reload)
echo "📡 Starting backend API in pane 0 (no hot reload)..."
tmux send-keys -t $SESSION_NAME:services.0 "cd backend" C-m
tmux send-keys -t $SESSION_NAME:services.0 "source venv/bin/activate" C-m
tmux send-keys -t $SESSION_NAME:services.0 "export PYTHONPATH=." C-m
tmux send-keys -t $SESSION_NAME:services.0 "echo 'Starting API server (no hot reload)...'" C-m
tmux send-keys -t $SESSION_NAME:services.0 "python -m uvicorn app.main:app --host 0.0.0.0 --port 5123" C-m

# Split horizontally to create second pane for Celery worker
echo "⚙️  Adding Celery worker in pane 1..."
tmux split-window -h -t $SESSION_NAME:services -c "$(pwd)/backend"
tmux send-keys -t $SESSION_NAME:services.1 "sleep 1" C-m # Wait for backend to start
tmux send-keys -t $SESSION_NAME:services.1 "./run_celery.sh" C-m

# Split the right pane vertically to create third pane for frontend
echo "🌐 Adding frontend in pane 2 (production build)..."
tmux split-window -v -t $SESSION_NAME:services.1 -c "$(pwd)/frontend"
tmux send-keys -t $SESSION_NAME:services.2 "sleep 2" C-m # Wait for backend services to start
tmux send-keys -t $SESSION_NAME:services.2 "echo 'Building frontend for production...'" C-m
tmux send-keys -t $SESSION_NAME:services.2 "pnpm run build && pnpm run preview --host 0.0.0.0 --port 5192" C-m

# Adjust pane sizes for better visibility
# Make the backend pane (left) take up 50% of width
tmux resize-pane -t $SESSION_NAME:services.0 -x 50%
# Make the celery and frontend panes split the right side equally
tmux resize-pane -t $SESSION_NAME:services.1 -y 50%

# Create a status window for info
echo "📊 Adding status window..."
tmux new-window -t $SESSION_NAME -n "status" -c "$(pwd)"
tmux send-keys -t $SESSION_NAME:status "clear" C-m
tmux send-keys -t $SESSION_NAME:status "echo '🎤 Open Karaoke Studio - No Hot Reload Mode'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '========================================='" C-m
tmux send-keys -t $SESSION_NAME:status "echo ''" C-m
tmux send-keys -t $SESSION_NAME:status "echo '🔒 Hot Reload: DISABLED'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   - Backend API:  Running without --reload flag'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   - Frontend:     Production build with preview server'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   - Celery:       Never hot reloads (unchanged)'" C-m
tmux send-keys -t $SESSION_NAME:status "echo ''" C-m
tmux send-keys -t $SESSION_NAME:status "echo '⚠️  To apply code changes, restart the affected service:'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   - Ctrl+C in the pane, then re-run the command'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   - Or kill session and restart: tmux kill-session -t $SESSION_NAME'" C-m
tmux send-keys -t $SESSION_NAME:status "echo ''" C-m
tmux send-keys -t $SESSION_NAME:status "echo '🌐 LOCAL NETWORK ACCESS:'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   🎤 Main Device:     http://localhost:5192'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   📱 Other Devices:   http://$HOST_IP:5192'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   🔧 Backend API:     http://$HOST_IP:5123'" C-m
tmux send-keys -t $SESSION_NAME:status "echo ''" C-m
tmux send-keys -t $SESSION_NAME:status "echo '📋 Tmux Controls:'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   Ctrl+B + 0-1:   Switch between windows (services/status)'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   Ctrl+B + o:     Cycle through panes in services window'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   Ctrl+B + arrow: Navigate between panes'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   Ctrl+B + d:     Detach from session'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   Ctrl+B + x:     Kill current pane'" C-m
tmux send-keys -t $SESSION_NAME:status "echo ''" C-m
tmux send-keys -t $SESSION_NAME:status "echo '📋 Copy/Paste Logs:'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   Mouse Mode:      Scroll with mouse wheel, drag to select'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   Keyboard Mode:   Ctrl+B + [ (enter copy mode)'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '                    Space (start select), Enter (copy)'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '                    Ctrl+B + ] (paste)'" C-m
tmux send-keys -t $SESSION_NAME:status "echo ''" C-m
tmux send-keys -t $SESSION_NAME:status "echo '📱 Pane Layout (Window 0 - services):'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   ┌─────────────┬─────────────┐'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   │             │   Celery    │'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   │   Backend   │   Worker    │'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   │     API     ├─────────────┤'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   │ (no reload) │  Frontend   │'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   │             │ Preview Srv │'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   └─────────────┴─────────────┘'" C-m
tmux send-keys -t $SESSION_NAME:status "echo ''" C-m
tmux send-keys -t $SESSION_NAME:status "echo '🎉 Ready for karaoke party! (No hot reload mode)'" C-m
tmux send-keys -t $SESSION_NAME:status "echo ''" C-m
tmux send-keys -t $SESSION_NAME:status "echo '💡 Tips:'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   - Use \"tmux attach -t $SESSION_NAME\" to reattach'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   - Use \"tmux kill-session -t $SESSION_NAME\" to stop all services'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   - Switch to services window (Ctrl+B + 0) to see all logs'" C-m
tmux send-keys -t $SESSION_NAME:status "echo '   - For hot reload, use ./scripts/dev-tmux.sh instead'" C-m

# Select the services window as default
tmux select-window -t $SESSION_NAME:services

echo ""
echo "✅ Tmux session '$SESSION_NAME' created (No Hot Reload Mode)!"
echo ""
echo "🔒 Hot Reload: DISABLED"
echo "   - Backend: Running without --reload"
echo "   - Frontend: Production build + preview server"
echo ""
echo "🌐 LOCAL NETWORK ACCESS:"
echo "   🎤 Main Device:     http://localhost:5192"
echo "   📱 Other Devices:   http://$HOST_IP:5192"
echo "   🔧 Backend API:     http://$HOST_IP:5123"
echo ""
echo "📋 Tmux Commands:"
echo "   Attach to session:  tmux attach -t $SESSION_NAME"
echo "   Kill all services:  tmux kill-session -t $SESSION_NAME"
echo ""
echo "🚀 Attaching to tmux session now..."

# Attach to the session
tmux attach -t $SESSION_NAME
