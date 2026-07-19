"""Tests for MusicBrainz soundtrack/show-name extraction."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.musicbrainz_service import (
    _strip_show_name_boilerplate,
    get_recording_show_name,
)


@pytest.mark.parametrize(
    "title, expected",
    [
        ("Wicked (Original Broadway Cast Recording)", "Wicked"),
        ("Hamilton", "Hamilton"),
        ("Frozen (Original Motion Picture Soundtrack)", "Frozen"),
        ("  Cats (2019)  ", "Cats"),
        ("Dear Evan Hansen (Original Cast) (Deluxe)", "Dear Evan Hansen"),
    ],
)
def test_strip_show_name_boilerplate(title, expected):
    assert _strip_show_name_boilerplate(title) == expected


def _mock_response(payload):
    resp = MagicMock()
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    client = MagicMock()
    client.get.return_value = resp
    client.__enter__.return_value = client
    client.__exit__.return_value = False
    return client


@patch("app.services.musicbrainz_service.time.sleep", return_value=None)
@patch("app.services.musicbrainz_service.httpx.Client")
def test_get_recording_show_name_soundtrack(mock_client_cls, _sleep):
    payload = {
        "releases": [
            {
                "title": "Some Single",
                "release-group": {"primary-type": "Single", "secondary-types": []},
            },
            {
                "title": "Wicked (Original Broadway Cast Recording)",
                "release-group": {
                    "primary-type": "Album",
                    "secondary-types": ["Soundtrack"],
                    "title": "Wicked (Original Broadway Cast Recording)",
                },
            },
        ]
    }
    mock_client_cls.return_value = _mock_response(payload)

    assert get_recording_show_name("some-mbid") == "Wicked"


@patch("app.services.musicbrainz_service.time.sleep", return_value=None)
@patch("app.services.musicbrainz_service.httpx.Client")
def test_get_recording_show_name_no_soundtrack(mock_client_cls, _sleep):
    payload = {
        "releases": [
            {
                "title": "Regular Album",
                "release-group": {"primary-type": "Album", "secondary-types": []},
            }
        ]
    }
    mock_client_cls.return_value = _mock_response(payload)

    assert get_recording_show_name("some-mbid") is None
