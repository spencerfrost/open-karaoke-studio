#!/bin/bash
# Quick script to start the FastAPI session server
# Usage: ./run_fastapi_sessions.sh

echo "🎪 Starting FastAPI Session Management Server..."

# Check if we're in the backend directory
if [ ! -f "fastapi_poc/main.py" ]; then
    echo "❌ Please run this script from the backend directory"
    echo "   Expected: backend/fastapi_poc/main.py"
    exit 1
fi

# Check for and activate virtual environment
if [ -f "venv/bin/activate" ]; then
    echo "🐍 Activating virtual environment..."
    source venv/bin/activate
else
    echo "⚠️  No virtual environment found. Please create one first:"
    echo "   python -m venv venv && source venv/bin/activate"
    exit 1
fi

# Navigate to FastAPI directory and start server
cd fastapi_poc

echo "⚡ Starting FastAPI session server on port 5124..."
echo "📊 Session Test Page: http://localhost:5124/session-test"
echo "📚 API Documentation: http://localhost:5124/docs"
echo "🔌 WebSocket Endpoint: ws://localhost:5124/ws/session"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python main.py