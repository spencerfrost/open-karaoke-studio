#!/bin/bash
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
