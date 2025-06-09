#!/bin/bash
echo "Starting Open Karaoke Studio API Server..."
export FLASK_APP=app.main
export FLASK_ENV=development
source venv/bin/activate

# Run the Flask API server from the backend directory
python -m app.main
