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
