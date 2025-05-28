#!/bin/bash

# Auto-detect the machine's IP address for external access
HOST_IP=$(hostname -I | awk '{print $1}')
echo "Detected host IP: $HOST_IP"

# Create/update the frontend .env.local file with the correct backend URL
echo "VITE_BACKEND_URL=http://$HOST_IP:5123" > frontend/.env.local

tmux new-session -d -s karaoke
tmux set -g -t karaoke mouse on

# Split the tmux window into three panes
tmux split-window -h -t karaoke
tmux split-window -v -t karaoke:0.1

# Start the backend API server
tmux send-keys -t karaoke:0.0 "cd $(pwd)/backend && source venv/bin/activate && ./run_api.sh" C-m
# Start the Celery worker
tmux send-keys -t karaoke:0.1 "cd $(pwd)/backend && source venv/bin/activate && ./run_celery.sh" C-m
# Start the frontend development server
tmux send-keys -t karaoke:0.2 "cd $(pwd)/frontend && pnpm run dev --host 0.0.0.0" C-m

# Attach to the tmux session
tmux a -t karaoke
