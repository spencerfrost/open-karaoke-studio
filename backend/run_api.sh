#!/bin/bash
echo "Starting Open Karaoke Studio API Server..."
source venv/bin/activate
export PYTHONPATH=.
python -m uvicorn app.main:app --host 0.0.0.0 --port 5123 --reload