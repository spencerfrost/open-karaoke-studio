# backend/app/api/responses.py
"""
Standard API response utilities
"""

from flask import jsonify
from typing import Any, Optional


def success_response(
    data: Any = None, 
    message: str = "Success", 
    status_code: int = 200
):
    """Create a standard success response"""
    response_data = {
        "success": True,
        "message": message
    }
    
    if data is not None:
        response_data["data"] = data
    
    return jsonify(response_data), status_code


def error_response(
    message: str = "An error occurred", 
    status_code: int = 500,
    errors: Optional[dict] = None
):
    """Create a standard error response"""
    response_data = {
        "success": False,
        "error": message
    }
    
    if errors:
        response_data["errors"] = errors
    
    return jsonify(response_data), status_code