#!/bin/bash
echo "Starting Open Karaoke Studio Services..."

tmux new-session -d -s karaoke
tmux split-window -h -t karaoke
tmux send-keys -t karaoke:0.0 "cd $(pwd) && ./run_api.sh" C-m
tmux send-keys -t karaoke:0.1 "cd $(pwd) && ./run_celery.sh" C-m

echo "Services starting in tmux session. Press Ctrl+B then D to detach."
echo "To reattach later, run: tmux a -t karaoke"
tmux a -t karaoke
