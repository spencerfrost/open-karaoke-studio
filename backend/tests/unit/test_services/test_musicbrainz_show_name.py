"""Tests for MusicBrainz soundtrack/show-name extraction."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.musicbrainz_service import (
    _extract_show_name,
    _strip_show_name_boilerplate,
    get_recording_details,
)

# Real /recording lookups (inc=releases release-groups artist-credits),
# trimmed to the fields the lookup reads.
FIXTURES = Path(__file__).parents[2] / "fixtures" / "musicbrainz"


def _recording(name: str) -> dict:
    return json.loads((FIXTURES / f"recording_{name}.json").read_text())


@pytest.mark.parametrize(
    "title, expected",
    [
        ("Wicked (Original Broadway Cast Recording)", "Wicked"),
        ("Hamilton", "Hamilton"),
        ("Frozen (Original Motion Picture Soundtrack)", "Frozen"),
        ("  Cats (2019)  ", "Cats"),
        ("Dear Evan Hansen (Original Cast) (Deluxe)", "Dear Evan Hansen"),
        ("The Lion King: Original Motion Picture Soundtrack", "The Lion King"),
        ("Rent: Original Motion Picture Soundtrack", "Rent"),
        ("Dear Evan Hansen: Original Broadway Cast Recording", "Dear Evan Hansen"),
        ("Once: Music From the Motion Picture", "Once"),
        ("28 Days Later: The Soundtrack Album", "28 Days Later"),
        ("Wicked: The Soundtrack", "Wicked"),
        ("Hamilton - Original Broadway Cast Recording", "Hamilton"),
        ("Grease: Original Soundtrack From the Motion Picture", "Grease"),
        (
            "Arcane: League of Legends: Season Two Original Soundtrack",
            "Arcane: League of Legends",
        ),
        # A colon that's part of the title stays
        ("Spider-Man: Turn Off the Dark", "Spider-Man: Turn Off the Dark"),
        ("Hamilton: An American Musical", "Hamilton: An American Musical"),
        ("Cloverfield: Rob's Party Mix", "Cloverfield: Rob's Party Mix"),
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
        "first-release-date": "2003-12-16",
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
                    "first-release-date": "2003-12-16",
                },
            },
        ],
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
        "first-release-date": "2003-12-16",
        "releases": [
            {
                "title": "Wicked (Original Broadway Cast Recording)",
                "release-group": {
                    "primary-type": "Album",
                    "secondary-types": ["Soundtrack"],
                    "title": "Wicked (Original Broadway Cast Recording)",
                    "first-release-date": "2003-12-16",
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
    assert [(c.name, c.role) for c in credits] == [("Idina Menzel", "primary")]
    assert client.get.call_count == 1


@patch("app.services.musicbrainz_service.time.sleep", return_value=None)
@patch("app.services.musicbrainz_service.httpx.Client")
def test_get_recording_details_without_credits(mock_client_cls, _sleep):
    mock_client_cls.return_value = _mock_response({"releases": []})

    assert get_recording_details("some-mbid") == (None, None)


@patch("app.services.musicbrainz_service.time.sleep", return_value=None)
@patch("app.services.musicbrainz_service.httpx.Client")
def test_lookups_are_cached_on_disk(mock_client_cls, _sleep, tmp_path):
    client = _mock_response({"releases": [], "artist-credit": []})
    mock_client_cls.return_value = client

    get_recording_details("rec-1", tmp_path)
    get_recording_details("rec-1", tmp_path)

    assert client.get.call_count == 1
    assert (tmp_path / "recording-rec-1.json").exists()


@patch("app.services.musicbrainz_service.time.sleep", return_value=None)
@patch("app.services.musicbrainz_service.httpx.Client")
def test_a_rate_limited_lookup_is_retried(mock_client_cls, sleep, tmp_path):
    import httpx

    busy = httpx.Response(503, request=httpx.Request("GET", "https://mb"))
    ok = _mock_response({"releases": []}).get.return_value
    client = _mock_response({})
    client.get.side_effect = [busy, ok]
    mock_client_cls.return_value = client

    show_name, credits = get_recording_details("rec-2", tmp_path)

    assert client.get.call_count == 2
    assert [c.args[0] for c in sleep.call_args_list] == [1, 4]
    assert (tmp_path / "recording-rec-2.json").exists()


@patch("app.services.musicbrainz_service.time.sleep", return_value=None)
@patch("app.services.musicbrainz_service.httpx.Client")
def test_a_failed_lookup_is_none_not_no_show(mock_client_cls, _sleep):
    import httpx

    client = _mock_response({})
    client.get.side_effect = httpx.ConnectError("down")
    mock_client_cls.return_value = client

    assert get_recording_details("rec-3") is None


# --- The first-release rule, on real recordings ---


@pytest.mark.parametrize(
    "recording, show",
    [
        # Written for the show: first released on its soundtrack
        ("circle_of_life", "The Lion King"),
        ("ill_cover_you_reprise", "Rent"),
        ("defying_gravity", "Wicked"),
        ("falling_slowly_once", "Once"),
        # Licensed: on its artist's album years before the soundtrack
        ("bobcaygeon", None),
        # The same song's earlier recording, on a non-soundtrack album
        ("falling_slowly_swell_season", None),
    ],
)
def test_show_from_the_first_release(recording, show):
    assert _extract_show_name(_recording(recording)) == show


def _soundtrack(
    title, date, primary="Album", secondary=("Soundtrack",), artist="Composer"
):
    artist_id = (
        "89ad4ac3-39f7-470e-963a-56509c546377"
        if artist == "Various Artists"
        else "mb-" + artist
    )
    return {
        "title": title,
        "artist-credit": [{"name": artist, "artist": {"id": artist_id}}],
        "release-group": {
            "id": title,
            "title": title,
            "primary-type": primary,
            "secondary-types": list(secondary),
            "first-release-date": date,
        },
    }


def _first_released_2001(*releases):
    return {"first-release-date": "2001-03-01", "releases": list(releases)}


def test_a_single_is_never_the_show():
    data = _first_released_2001(_soundtrack("Song Title", "2001", primary="Single"))
    assert _extract_show_name(data) is None


def test_a_compilation_soundtrack_isnt_a_show():
    data = _first_released_2001(
        _soundtrack(
            "Music From the OC: Mix 5", "2001", secondary=("Compilation", "Soundtrack")
        )
    )
    assert _extract_show_name(data) is None


def test_a_various_artists_soundtrack_isnt_a_show():
    data = _first_released_2001(
        _soundtrack("Burnout 3: Takedown", "2001", artist="Various Artists")
    )
    assert _extract_show_name(data) is None


def test_another_release_of_the_album_can_qualify():
    data = _first_released_2001(
        _soundtrack("Big Fish", "2001", artist="Various Artists"),
        _soundtrack("Big Fish", "2001"),
    )
    assert _extract_show_name(data) == "Big Fish"


def test_the_original_wins_over_a_same_year_edition_without_a_full_date():
    data = {
        "first-release-date": "1994-05-31",
        "releases": [
            _soundtrack("O Rei Leão", "1994"),
            _soundtrack(
                "The Lion King: Original Motion Picture Soundtrack", "1994-05-31"
            ),
        ],
    }
    assert _extract_show_name(data) == "The Lion King"


def test_a_lead_single_out_before_the_album_still_counts():
    data = {
        "first-release-date": "2007-03-01",
        "releases": [_soundtrack("Once: Music From the Motion Picture", "2007-05-22")],
    }
    assert _extract_show_name(data) == "Once"


def test_no_first_release_date_means_no_show():
    data = {"releases": [_soundtrack("Rent", "1996-08-27")]}
    assert _extract_show_name(data) is None
