"""Tests for MusicBrainz soundtrack/show-name extraction."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.musicbrainz_service import (
    _strip_show_name_boilerplate,
    get_recording_details,
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
def test_get_recording_details_show_name_soundtrack(mock_client_cls, _sleep):
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

    assert get_recording_details("some-mbid")[0] == "Wicked"


@patch("app.services.musicbrainz_service.time.sleep", return_value=None)
@patch("app.services.musicbrainz_service.httpx.Client")
def test_get_recording_details_show_name_no_soundtrack(mock_client_cls, _sleep):
    payload = {
        "releases": [
            {
                "title": "Regular Album",
                "release-group": {"primary-type": "Album", "secondary-types": []},
            }
        ]
    }
    mock_client_cls.return_value = _mock_response(payload)

    assert get_recording_details("some-mbid")[0] is None


@patch("app.services.musicbrainz_service.time.sleep", return_value=None)
@patch("app.services.musicbrainz_service.httpx.Client")
def test_get_recording_details_fetches_both_in_one_request(mock_client_cls, _sleep):
    """Show name and credits share a request — asking twice doubles the sleep."""
    payload = {
        "releases": [
            {
                "title": "Wicked (Original Broadway Cast Recording)",
                "release-group": {
                    "primary-type": "Album",
                    "secondary-types": ["Soundtrack"],
                    "title": "Wicked (Original Broadway Cast Recording)",
                },
            }
        ],
        "artist-credit": [
            {
                "name": "Idina Menzel",
                "artist": {"name": "Idina Menzel"},
                "joinphrase": "",
            }
        ],
    }
    client = _mock_response(payload)
    mock_client_cls.return_value = client

    show_name, credits = get_recording_details("some-mbid")

    assert show_name == "Wicked"
    assert credits == [("Idina Menzel", "primary")]
    assert client.get.call_count == 1


@patch("app.services.musicbrainz_service.time.sleep", return_value=None)
@patch("app.services.musicbrainz_service.httpx.Client")
def test_get_recording_details_without_credits(mock_client_cls, _sleep):
    mock_client_cls.return_value = _mock_response({"releases": []})

    assert get_recording_details("some-mbid") == (None, None)
