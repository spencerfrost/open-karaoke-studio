#!/bin/bash
echo "Starting Open Karaoke Studio API Server..."
export FLASK_APP=app.main
export FLASK_ENV=development
source venv/bin/activate
export PYTHONPATH=.
python app/main.py