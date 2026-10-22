"""Tests for the fingerprint_single_song Celery task."""

from unittest.mock import Mock, patch

import acoustid
import pytest

from app.jobs.jobs import fingerprint_single_song

SONG_ID = "song-abc-123"
RECORDING_ID = "rec-blackbird"


def _match(score, title="Blackbird", artist="The Beatles", recording_id=RECORDING_ID):
    """One AcoustID result, in the raw shape acoustid.match(parse=False) returns."""
    return {
        "score": score,
        "recordings": [
            {
                "id": recording_id,
                "title": title,
                "artists": [{"name": artist}],
                "releases": [],
            }
        ],
    }


def _response(*results):
    return {"status": "ok", "results": list(results)}


def _add_audio(library, *names, song_id=SONG_ID):
    song_dir = library / song_id
    song_dir.mkdir(exist_ok=True)
    for name in names:
        (song_dir / name).write_bytes(b"fake")


@pytest.fixture
def acoustid_match():
    """Stand in for the AcoustID web lookup; everything after it runs for real."""
    with (
        patch(
            "app.services.acoustid_service.get_config",
            return_value=Mock(ACOUSTID_API_KEY="test-key"),
        ),
        patch("app.services.acoustid_service.acoustid.match") as match,
    ):
        match.return_value = _response(_match(0.95))
        yield match


@pytest.fixture
def mock_celery():
    with patch("app.jobs.metadata_tasks.celery") as celery:
        yield celery


@pytest.fixture
def song(add_song):
    return add_song(SONG_ID)


@pytest.mark.parametrize(
    "files, used",
    [
        (["original.mp3", "instrumental.mp3", "vocals.mp3"], "original.mp3"),
        (["instrumental.mp3", "vocals.mp3"], "instrumental.mp3"),
        (["vocals.mp3"], "vocals.mp3"),
    ],
)
def test_fingerprints_the_first_audio_file_it_finds(
    library, song, acoustid_match, mock_celery, fetch_song, files, used
):
    _add_audio(library, *files)

    result = fingerprint_single_song(SONG_ID)

    assert result == {"status": "matched", "song_id": SONG_ID}
    assert acoustid_match.call_args.args[1] == str(library / SONG_ID / used)
    saved = fetch_song(SONG_ID)
    assert saved.acoustid_fingerprint_status == "matched"
    assert saved.musicbrainz_recording_id == RECORDING_ID
    assert saved.acoustid_score == 0.95


def test_no_audio_marks_the_song_failed(
    library, song, acoustid_match, mock_celery, fetch_song
):
    result = fingerprint_single_song(SONG_ID)

    assert result == {"status": "no_audio", "song_id": SONG_ID}
    assert fetch_song(SONG_ID).acoustid_fingerprint_status == "failed"
    acoustid_match.assert_not_called()


def test_an_unexpected_error_is_swallowed(library, song, mock_celery, fetch_song):
    _add_audio(library, "original.mp3")

    with patch(
        "app.services.acoustid_service.AcoustIdService.fingerprint_and_link",
        side_effect=Exception("AcoustID API down"),
    ):
        result = fingerprint_single_song(SONG_ID)

    assert result == {"status": "error", "song_id": SONG_ID}
    assert fetch_song(SONG_ID).acoustid_fingerprint_status == "not_checked"
    mock_celery.send_task.assert_not_called()


def test_a_link_sends_the_credits_step(library, song, acoustid_match, mock_celery):
    _add_audio(library, "original.mp3")

    fingerprint_single_song(SONG_ID)

    mock_celery.send_task.assert_called_once_with(
        "enrich_song_artist_credits", args=[SONG_ID]
    )


@pytest.mark.parametrize(
    "lookup, outcome",
    [
        ({"return_value": _response(_match(0.95, title="Yesterday"))}, "suggested"),
        (
            {
                "return_value": _response(
                    _match(0.95, title="Yesterday", recording_id="rec-1"),
                    _match(0.95, title="Help!", recording_id="rec-2"),
                )
            },
            "ambiguous",
        ),
        ({"return_value": _response()}, "no_match"),
        ({"side_effect": acoustid.WebServiceError("rate limited")}, "failed"),
    ],
)
def test_no_link_sends_no_credits_step(
    library, song, acoustid_match, mock_celery, fetch_song, lookup, outcome
):
    _add_audio(library, "original.mp3")
    acoustid_match.configure_mock(**lookup)

    result = fingerprint_single_song(SONG_ID)

    assert result["status"] == outcome
    saved = fetch_song(SONG_ID)
    assert saved.acoustid_fingerprint_status == outcome
    assert saved.musicbrainz_recording_id is None
    mock_celery.send_task.assert_not_called()
