# Tmux Development Environment

## Session Structure
The development environment runs in a tmux session called `open-karaoke`.

### Windows and Panes
- **Window 0 (`services`)**: Contains 3 panes for the main services
  - **Pane 0.0**: Backend API server (FastAPI/Uvicorn)
  - **Pane 0.1**: Frontend dev server (Vite)
  - **Pane 0.2**: Celery worker
- **Window 1 (`status`)**: Status/monitoring

## Common Commands

### Check API server logs
```bash
tmux capture-pane -t open-karaoke:0.0 -p | tail -20
```

### Restart API server
```bash
tmux send-keys -t open-karaoke:0.0 C-c && sleep 2 && tmux send-keys -t open-karaoke:0.0 "./run_api.sh" Enter
```

### Check Celery logs
```bash
tmux capture-pane -t open-karaoke:0.2 -p | tail -20
```

### Restart Celery worker
```bash
tmux send-keys -t open-karaoke:0.2 C-c && sleep 2 && tmux send-keys -t open-karaoke:0.2 "./run_celery.sh" Enter
```

### List all windows/panes
```bash
tmux list-windows -t open-karaoke
```

## Notes
- The API server has hot-reload enabled via Uvicorn's WatchFiles
- Celery does NOT hot-reload - must be manually restarted after backend code changes
- Backend runs on `http://0.0.0.0:5123`
- Frontend runs on `http://localhost:5173`
