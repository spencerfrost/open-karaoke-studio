"""Unit tests for app/services/acoustid_service.py."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.repositories.song_repository import SongRepository
from app.services.acoustid_service import AcoustIdService, _agrees

NO_SUGGESTION = {
    "acoustid_suggested_recording_id": None,
    "acoustid_suggested_title": None,
    "acoustid_suggested_artist": None,
}

# ─── Helpers ─────────────────────────────────────────────────────────────────


def _raw_response(*recordings_per_score):
    """
    Build a mock AcoustID raw API response dict.

    Each argument is a (score, list_of_recording_dicts) tuple.
    Recording dicts should have: id, title, artists, releases.
    """
    results = []
    for score, recordings in recordings_per_score:
        results.append({"score": score, "recordings": recordings})
    return {"status": "ok", "results": results}


def _rec(mbid, title, artist, albums=None, duration=None):
    """Shorthand for building a recording dict."""
    rec = {
        "id": mbid,
        "title": title,
        "artists": [{"name": artist}],
        "releases": [{"title": a} for a in (albums or [])],
    }
    if duration is not None:
        rec["duration"] = duration
    return rec


def _song(
    title="Hero of the Day",
    artist="Metallica",
    album=None,
    confirmed=False,
    recording_id=None,
    show_hand_set=False,
    duration=None,
):
    return SimpleNamespace(
        id="song-1",
        duration=duration,
        title=title,
        artist=artist,
        album=album,
        metadata_confirmed_at=datetime(2026, 10, 1) if confirmed else None,
        musicbrainz_recording_id=recording_id,
        show_name_hand_set_at=datetime(2026, 10, 1) if show_hand_set else None,
    )


def _run(svc, mock_config, raw=None, side_effect=None):
    with (
        patch("app.services.acoustid_service.get_config", return_value=mock_config),
        patch(
            "app.services.acoustid_service.acoustid.match",
            return_value=raw,
            side_effect=side_effect,
        ),
    ):
        return svc.fingerprint_and_link("song-1", "/fake/path.mp3")


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def song_repo():
    repo = Mock(spec=SongRepository)
    repo.fetch.return_value = _song()
    return repo


@pytest.fixture
def mock_config():
    cfg = MagicMock()
    cfg.ACOUSTID_API_KEY = "test-acoustid-key"
    return cfg


@pytest.fixture
def svc(song_repo):
    return AcoustIdService(song_repo=song_repo)


# ─── Failures and no match ───────────────────────────────────────────────────


def test_no_api_key_marks_failed(svc, song_repo):
    cfg = MagicMock()
    cfg.ACOUSTID_API_KEY = ""
    with patch("app.services.acoustid_service.get_config", return_value=cfg):
        assert svc.fingerprint_and_link("song-1", "/fake/path.mp3") == "failed"
    song_repo.update.assert_called_once_with(
        "song-1",
        acoustid_fingerprint_status="failed",
        acoustid_score=None,
        musicbrainz_recording_id=None,
        show_name=None,
        **NO_SUGGESTION,
    )


@pytest.mark.parametrize(
    "error",
    [
        "fingerprint",
        "web",
        "other",
    ],
)
def test_errors_mark_failed(svc, song_repo, mock_config, error):
    import acoustid

    side_effect = {
        "fingerprint": acoustid.FingerprintGenerationError("fpcalc missing"),
        "web": acoustid.WebServiceError("timeout"),
        "other": RuntimeError("oops"),
    }[error]
    assert _run(svc, mock_config, side_effect=side_effect) == "failed"
    assert song_repo.update.call_args.kwargs["acoustid_fingerprint_status"] == "failed"


def test_no_results_marks_no_match_and_drops_the_old_recording(
    svc, song_repo, mock_config
):
    song_repo.fetch.return_value = _song(recording_id="mbid-stale")
    assert _run(svc, mock_config, {"status": "ok", "results": []}) == "no_match"
    song_repo.update.assert_called_once_with(
        "song-1",
        acoustid_fingerprint_status="no_match",
        acoustid_score=None,
        musicbrainz_recording_id=None,
        show_name=None,
        **NO_SUGGESTION,
    )


# ─── Agreeing matches link, never rename ─────────────────────────────────────


def test_agreeing_match_links_the_recording_and_keeps_the_text(
    svc, song_repo, mock_config
):
    song_repo.fetch.return_value = _song("Hero Of The Day", "Metallica")
    raw = _raw_response((0.99, [_rec("mbid-hero", "Hero of the Day", "Metallica")]))
    assert _run(svc, mock_config, raw) == "matched"
    song_repo.update.assert_called_once_with(
        "song-1",
        **NO_SUGGESTION,
        acoustid_score=0.99,
        acoustid_fingerprint_status="matched",
        musicbrainz_recording_id="mbid-hero",
    )


def test_agreeing_match_below_the_bar_still_links(svc, song_repo, mock_config):
    raw = _raw_response((0.60, [_rec("mbid-hero", "Hero of the Day", "Metallica")]))
    assert _run(svc, mock_config, raw) == "matched"
    assert song_repo.update.call_args.kwargs["musicbrainz_recording_id"] == "mbid-hero"


def test_tied_candidates_link_the_one_named_like_the_song(svc, song_repo, mock_config):
    raw = _raw_response(
        (
            0.98,
            [
                _rec("mbid-cover", "Hero of the Day", "C for Caroline"),
                _rec("mbid-hero", "Hero of the Day", "Metallica"),
            ],
        )
    )
    assert _run(svc, mock_config, raw) == "matched"
    assert song_repo.update.call_args.kwargs["musicbrainz_recording_id"] == "mbid-hero"


def test_agreeing_ties_prefer_the_songs_album(svc, song_repo, mock_config):
    song_repo.fetch.return_value = _song(album="Load")
    raw = _raw_response(
        (
            0.98,
            [
                _rec(
                    "mbid-single", "Hero of the Day", "Metallica", ["Hero of the Day"]
                ),
                _rec("mbid-album", "Hero of the Day", "Metallica", ["Load"]),
            ],
        )
    )
    _run(svc, mock_config, raw)
    assert song_repo.update.call_args.kwargs["musicbrainz_recording_id"] == "mbid-album"


def test_agreeing_ties_link_the_version_of_the_songs_length(
    svc, song_repo, mock_config
):
    # The original and its extended remake share most of a fingerprint and tie.
    song_repo.fetch.return_value = _song(
        title="Ma Meilleure Ennemie", artist="Stromae, Pomme", duration=148.0
    )
    raw = _raw_response(
        (
            0.99,
            [
                _rec(
                    "mbid-extended", "Ma Meilleure Ennemie", "Stromae", duration=201.9
                ),
                _rec(
                    "mbid-original", "Ma meilleure ennemie", "Stromae", duration=148.0
                ),
            ],
        )
    )
    assert _run(svc, mock_config, raw) == "matched"
    assert (
        song_repo.update.call_args.kwargs["musicbrainz_recording_id"] == "mbid-original"
    )


def test_only_a_different_length_is_no_match(svc, song_repo, mock_config):
    song_repo.fetch.return_value = _song(duration=148.0, recording_id="mbid-old")
    raw = _raw_response(
        (0.99, [_rec("mbid-extended", "Hero of the Day", "Metallica", duration=202)])
    )
    assert _run(svc, mock_config, raw) == "no_match"
    assert song_repo.update.call_args.kwargs["musicbrainz_recording_id"] is None


def test_a_small_length_difference_still_links(svc, song_repo, mock_config):
    # A video's few seconds of silence or a fade aren't another version.
    song_repo.fetch.return_value = _song(duration=270.0)
    raw = _raw_response(
        (0.98, [_rec("mbid-hero", "Hero of the Day", "Metallica", duration=262)])
    )
    assert _run(svc, mock_config, raw) == "matched"


def test_unknown_lengths_dont_block_a_link(svc, song_repo, mock_config):
    song_repo.fetch.return_value = _song(duration=None)
    raw = _raw_response(
        (0.98, [_rec("mbid-hero", "Hero of the Day", "Metallica", duration=262)])
    )
    assert _run(svc, mock_config, raw) == "matched"


def test_confirmed_song_keeps_the_recording_a_person_picked(
    svc, song_repo, mock_config
):
    song_repo.fetch.return_value = _song(confirmed=True, recording_id="mbid-picked")
    raw = _raw_response((0.99, [_rec("mbid-other", "Hero of the Day", "Metallica")]))
    assert _run(svc, mock_config, raw) == "matched"
    assert "musicbrainz_recording_id" not in song_repo.update.call_args.kwargs


def test_confirmed_song_without_a_recording_gets_an_agreeing_one(
    svc, song_repo, mock_config
):
    song_repo.fetch.return_value = _song(confirmed=True)
    raw = _raw_response((0.99, [_rec("mbid-hero", "Hero of the Day", "Metallica")]))
    _run(svc, mock_config, raw)
    assert song_repo.update.call_args.kwargs["musicbrainz_recording_id"] == "mbid-hero"


# ─── Disagreeing matches become suggestions ──────────────────────────────────


def test_disagreeing_match_becomes_a_suggestion(svc, song_repo, mock_config):
    song_repo.fetch.return_value = _song("Stick Season", "Walk off the Earth")
    raw = _raw_response((1.0, [_rec("mbid-kidz", "Stick Season", "Kidz Bop")]))
    assert _run(svc, mock_config, raw) == "suggested"
    song_repo.update.assert_called_once_with(
        "song-1",
        acoustid_suggested_recording_id="mbid-kidz",
        acoustid_suggested_title="Stick Season",
        acoustid_suggested_artist="Kidz Bop",
        acoustid_score=1.0,
        musicbrainz_recording_id=None,
        show_name=None,
        acoustid_fingerprint_status="suggested",
    )
    assert "title" not in song_repo.update.call_args.kwargs
    assert "artist" not in song_repo.update.call_args.kwargs


def test_disagreeing_match_below_the_bar_is_no_match(svc, song_repo, mock_config):
    raw = _raw_response((0.60, [_rec("mbid-x", "Maybe Title", "Maybe Artist")]))
    assert _run(svc, mock_config, raw) == "no_match"
    kwargs = song_repo.update.call_args.kwargs
    assert kwargs["acoustid_score"] == 0.60
    assert kwargs["musicbrainz_recording_id"] is None
    assert kwargs["acoustid_suggested_recording_id"] is None


def test_picks_highest_score_from_multiple_results(svc, song_repo, mock_config):
    raw = _raw_response(
        (0.70, [_rec("mbid-low", "Low Match", "Artist A")]),
        (0.92, [_rec("mbid-high", "High Match", "Artist B")]),
    )
    assert _run(svc, mock_config, raw) == "suggested"
    kwargs = song_repo.update.call_args.kwargs
    assert kwargs["acoustid_suggested_recording_id"] == "mbid-high"


def test_confirmed_song_is_never_suggested_or_renamed(svc, song_repo, mock_config):
    song_repo.fetch.return_value = _song(
        "Steady", "Giant Panda Guerilla Dub Squad", confirmed=True
    )
    raw = _raw_response(
        (0.97, [_rec("mbid-sol", "Solution", "Giant Panda Guerilla Dub Squad")])
    )
    assert _run(svc, mock_config, raw) == "skipped"
    song_repo.update.assert_called_once_with(
        "song-1",
        acoustid_fingerprint_status="skipped",
        acoustid_score=0.97,
        **NO_SUGGESTION,
    )


def test_confirmed_song_with_a_recording_stays_matched(svc, song_repo, mock_config):
    song_repo.fetch.return_value = _song(
        "Steady", "Giant Panda", confirmed=True, recording_id="mbid-picked"
    )
    raw = _raw_response((0.97, [_rec("mbid-sol", "Solution", "Giant Panda")]))
    assert _run(svc, mock_config, raw) == "matched"
    assert "musicbrainz_recording_id" not in song_repo.update.call_args.kwargs


# ─── Ties nobody agrees with ─────────────────────────────────────────────────


def test_disagreeing_ties_without_album_are_ambiguous(svc, song_repo, mock_config):
    song_repo.fetch.return_value = _song(recording_id="mbid-stale")
    raw = _raw_response(
        (
            0.98,
            [
                _rec("mbid-a", "Title A", "Artist A"),
                _rec("mbid-b", "Title B", "Artist B"),
            ],
        )
    )
    assert _run(svc, mock_config, raw) == "ambiguous"
    song_repo.update.assert_called_once_with(
        "song-1",
        acoustid_fingerprint_status="ambiguous",
        acoustid_score=0.98,
        musicbrainz_recording_id=None,
        show_name=None,
        **NO_SUGGESTION,
    )


def test_album_narrows_disagreeing_ties_to_a_suggestion(svc, song_repo, mock_config):
    song_repo.fetch.return_value = _song(
        "Man of Constant Sorrow", "Soggy Bottom", album="O Brother, Where Art Thou?"
    )
    raw = _raw_response(
        (
            0.98,
            [
                _rec("mbid-wrong", "16", "DJ Panin", albums=["Some Random Album"]),
                _rec(
                    "mbid-correct",
                    "I Am a Man of Constant Sorrow",
                    "The Soggy Bottom Boys",
                    albums=[
                        "O Brother, Where Art Thou? (Soundtrack from the Motion Picture)"
                    ],
                ),
            ],
        )
    )
    assert _run(svc, mock_config, raw) == "suggested"
    kwargs = song_repo.update.call_args.kwargs
    assert kwargs["acoustid_suggested_recording_id"] == "mbid-correct"
    assert kwargs["acoustid_suggested_title"] == "I Am a Man of Constant Sorrow"


def test_album_matching_several_ties_is_ambiguous(svc, song_repo, mock_config):
    song_repo.fetch.return_value = _song("X", "Y", album="Greatest Hits")
    raw = _raw_response(
        (
            0.98,
            [
                _rec("mbid-a", "Title A", "Artist A", albums=["Greatest Hits"]),
                _rec("mbid-b", "Title B", "Artist B", albums=["Greatest Hits Vol 2"]),
            ],
        )
    )
    assert _run(svc, mock_config, raw) == "ambiguous"


# ─── What counts as agreeing ─────────────────────────────────────────────────


@pytest.mark.parametrize(
    "song_title, song_artist, title, artist",
    [
        ("War", "Bob Marley", "War", "Bob Marley & The Wailers"),
        ("Ignition (Remix)", "R.Kelly", "Ignition (remix)", "R. Kelly"),
        ("Roses", "Outkast", "Roses", "OutKast"),
        (
            "Rock 'n' Roll Fantasy",
            "Bad Company",
            "Rock ’n’ Roll Fantasy",
            "Bad Company",
        ),
        ("Creep - 2009 Remaster", "Radiohead", "Creep", "Radiohead"),
        (
            "Trouble",
            "Sub Focus feat. Rudimental, Chronixx",
            "Trouble",
            "Sub Focus & Rudimental ft. Chronixx & Maverick Sabre",
        ),
    ],
)
def test_agrees(song_title, song_artist, title, artist):
    assert _agrees(song_title, song_artist, title, artist)


@pytest.mark.parametrize(
    "song_title, song_artist, title, artist",
    [
        ("Stick Season", "Walk off the Earth", "Stick Season", "Kidz Bop"),
        (
            "Steady",
            "Giant Panda Guerilla Dub Squad",
            "Solution",
            "Giant Panda Guerilla Dub Squad",
        ),
        ("One Song Glory", "Adam Pascal", "One Song Glory", "Jonathan Larson"),
        ("Beside You", "Marianas Trench", "Beside You", "Mariana Trench"),
        ("Crazy", "Bob", "Crazy", "Bobby Brown"),
        ("Crazy", None, "Crazy", "Gnarls Barkley"),
    ],
)
def test_disagrees(song_title, song_artist, title, artist):
    assert not _agrees(song_title, song_artist, title, artist)


def test_a_hand_set_show_survives_losing_the_recording(svc, song_repo, mock_config):
    song_repo.fetch.return_value = _song(recording_id="mbid-old", show_hand_set=True)
    _run(svc, mock_config, raw={"status": "ok", "results": []})
    kwargs = song_repo.update.call_args.kwargs
    assert kwargs["musicbrainz_recording_id"] is None
    assert "show_name" not in kwargs
