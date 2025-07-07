"""
API utilities for testing.
"""

import json
from typing import Any, Dict
from unittest.mock import Mock


def create_mock_response(data: Dict[str, Any], status_code: int = 200):
    """Create a mock response object"""
    response = Mock()
    response.status_code = status_code
    response.json.return_value = data
    response.text = json.dumps(data)
    response.content = json.dumps(data).encode()
    return response


def assert_api_response_structure(response_data: Dict[str, Any], expected_keys: list):
    """Assert that API response has expected structure"""
    for key in expected_keys:
        assert key in response_data, f"Expected key '{key}' not found in response"


def assert_success_response(response_data: Dict[str, Any]):
    """Assert that response indicates success"""
    assert "success" in response_data or "error" not in response_data


def assert_error_response(
    response_data: Dict[str, Any], expected_error_message: str = None
):
    """Assert that response indicates an error"""
    assert (
        "error" in response_data
        or "success" in response_data
        and not response_data["success"]
    )

    if expected_error_message:
        error_msg = response_data.get("error", {}).get(
            "message", response_data.get("error", "")
        )
        assert expected_error_message.lower() in str(error_msg).lower()


class MockRequest:
    """Mock Flask request object for testing"""

    def __init__(self, json_data=None, args=None, files=None):
        self.json = json_data or {}
        self.args = args or {}
        self.files = files or {}
        self.method = "GET"
        self.url = "http://localhost/test"

    def get_json(self):
        return self.json


class MockFlaskApp:
    """Mock Flask app for testing"""

    def __init__(self):
        self.logger = Mock()
        self.config = {}

    def test_client(self):
        return Mock()


def create_test_client_response(data: Any, status_code: int = 200):
    """Create a mock client response for Flask test client"""
    response = Mock()
    response.status_code = status_code
    response.data = json.dumps(data).encode() if isinstance(data, dict) else data
    response.get_json = lambda: data if isinstance(data, dict) else json.loads(data)
    return response
