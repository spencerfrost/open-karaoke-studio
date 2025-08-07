#!/bin/bash

# FastAPI Proof of Concept Setup Script
# Run this to quickly set up and test the FastAPI POC

echo "🚀 Setting up FastAPI Proof of Concept..."

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ Please run this script from the fastapi_poc directory"
    exit 1
fi

# Check for and activate virtual environment (should be in backend dir)
if [ -f "../venv/bin/activate" ]; then
    echo "🐍 Activating virtual environment from backend/venv..."
    source ../venv/bin/activate
else
    echo "⚠️  No virtual environment found in backend/venv. Please create one first:"
    echo "   cd ../backend && python -m venv venv && source venv/bin/activate"
    echo "   Then run this script again."
    exit 1
fi

# Install dependencies
echo "📦 Installing FastAPI dependencies..."
pip install -r requirements.txt

# Install test dependencies
echo "🧪 Installing test dependencies..."
pip install pytest pytest-asyncio httpx

echo "✅ Setup complete!"
echo ""
echo "🎯 Quick Start Commands:"
echo "  Activate venv:   source ../venv/bin/activate"
echo "  Run FastAPI:     uvicorn main:app --reload --port 8000"
echo "  Run tests:       pytest test_main.py -v"
echo "  View docs:       open http://localhost:8000/docs"
echo ""
echo "💡 Alternative ways to run FastAPI:"
echo "  Python directly: python main.py"
echo "  With uvicorn:    uvicorn main:app --reload --port 8000"
echo ""
echo "🔗 Useful URLs:"
echo "  Health Check:    http://localhost:8000/api/health"
echo "  API Docs:        http://localhost:8000/docs"
echo "  Songs API:       http://localhost:8000/api/songs"
echo "  Performance:     http://localhost:8000/api/performance-test"
echo ""
echo "🎭 Performance Comparison:"
echo "  Flask health:    curl http://localhost:5123/api/health"
echo "  FastAPI health:  curl http://localhost:8000/api/health"
echo ""
echo "✅ Virtual environment is activated!"
echo ""
echo "🚀 Ready to start! Choose one:"
echo "   python main.py                               # Just like Flask!"
echo "   uvicorn main:app --reload --port 8000        # Using uvicorn directly"
