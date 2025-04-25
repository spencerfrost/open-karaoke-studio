#!/bin/bash
echo "Starting Open Karaoke Studio - All Services..."

# Create a new tmux session with 3 panes
tmux new-session -d -s karaoke
# Split horizontally for backend services
tmux split-window -h -t karaoke
# Split the right pane vertically for frontend
tmux split-window -v -t karaoke:0.1

# Start the API server in the first pane
tmux send-keys -t karaoke:0.0 "cd $(pwd)/backend && ./run_api.sh" C-m

# Start the Celery worker in the second pane
tmux send-keys -t karaoke:0.1 "cd $(pwd)/backend && ./run_celery.sh" C-m

# Start the frontend in the third pane
tmux send-keys -t karaoke:0.2 "cd $(pwd)/frontend && pnpm run dev" C-m

echo "All services are starting in a tmux session with 3 panes:"
echo "- Left pane: Backend API"
echo "- Top-right pane: Celery worker"
echo "- Bottom-right pane: Frontend"
echo ""
echo "tmux commands:"
echo "- Press Ctrl+B then D to detach from the session"
echo "- To reattach later, run: tmux a -t karaoke"
echo "- Press Ctrl+B then arrow keys to navigate between panes"

# Attach to the tmux session
tmux a -t karaoke