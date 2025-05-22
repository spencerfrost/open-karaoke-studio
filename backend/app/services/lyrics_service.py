# backend/app/services/lyrics_service.py
import requests
from typing import Tuple, Dict, Optional, Any
from flask import current_app

USER_AGENT = "OpenKaraokeStudio/0.1 (https://github.com/spencerfrost/open-karaoke)"


def make_request(path: str, params: dict) -> Tuple[int, Any]:
    """
    Helper function to call LRCLIB API

    Args:
        path (str): API endpoint path
        params (dict): Query parameters to include in the request

    Returns:
        Tuple[int, Any]: HTTP status code and response data as returned from LRCLIB
    """
    url = f"https://lrclib.net{path}"
    headers = {"User-Agent": USER_AGENT}
    current_app.logger.info(f"LRCLIB request: {url} params={params}")
    resp = requests.get(url, params=params, headers=headers, timeout=10)
    status = resp.status_code

    try:
        data = resp.json()
    except ValueError:
        text = resp.text.strip()
        if status >= 400:
            data = {"error": text}
        else:
            data = {"error": "Invalid JSON from LRCLIB"}

    return status, data

