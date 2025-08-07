import time
from datetime import datetime

from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__, url_prefix="/api")


@health_bp.route("/health", methods=["GET"])
def health():
    """
    Health check endpoint with performance timing.
    Enhanced to match FastAPI's health endpoint for comparison.
    """
    start_time = time.time()
    
    # Simulate some work (same as FastAPI version)
    time.sleep(0.001)  # 1ms of "work"
    
    end_time = time.time()
    response_time = (end_time - start_time) * 1000  # Convert to milliseconds
    
    return jsonify({
        "status": "ok",
        "framework": "flask",
        "timestamp": datetime.now().isoformat(),
        "response_time_ms": round(response_time, 2)
    }), 200
