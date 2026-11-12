"""Tests for a song's show following its recording, and hand-set shows staying."""

from unittest.mock import patch

import pytest

from app.db.models import DbSong
from app.jobs.metadata_tasks import enrich_song_artist_credits
from app.services.artist_credits_rebuild import MusicBrainzData, rebuild
from app.utils.clock import utc_now


@pytest.fixture
def db(test_db_session):
    return test_db_session


def _song(db, song_id="s1", **fields):
    fields.setdefault("title", "Song")
    fields.setdefault("artist", "Artist")
    db.add(DbSong(id=song_id, **fields))
    db.commit()


def _show(db, song_id="s1"):
    db.expire_all()
    return db.get(DbSong, song_id).show_name


def _enrich(details):
    with patch(
        "app.services.musicbrainz_service.get_recording_details",
        return_value=details,
    ):
        return enrich_song_artist_credits("s1")


# --- Enrichment, for new or changed recordings ---


def test_enrichment_sets_the_show(db):
    _song(db, musicbrainz_recording_id="rec")
    _enrich(("Rent", None))
    assert _show(db) == "Rent"


def test_enrichment_clears_a_show_the_recording_isnt_from(db):
    _song(db, musicbrainz_recording_id="rec", show_name="Trailer Park Boys")
    _enrich((None, None))
    assert _show(db) is None


def test_enrichment_leaves_a_hand_set_show(db):
    _song(
        db,
        musicbrainz_recording_id="rec",
        show_name="Once",
        show_name_hand_set_at=utc_now(),
    )
    _enrich(("Something Else", None))
    assert _show(db) == "Once"


def test_a_hand_cleared_show_stays_cleared(db):
    _song(db, musicbrainz_recording_id="rec", show_name_hand_set_at=utc_now())
    _enrich(("Rent", None))
    assert _show(db) is None


def test_a_failed_lookup_keeps_the_show(db):
    _song(db, musicbrainz_recording_id="rec", show_name="Rent")
    assert _enrich(None)["status"] == "error"
    assert _show(db) == "Rent"


def test_a_song_that_lost_its_recording_loses_its_show(db):
    _song(db, show_name="Rent")
    assert _enrich(("Unused", None))["status"] == "no_recording"
    assert _show(db) is None


# --- The rebuild, for the whole library ---


def test_the_rebuild_sets_shows_from_recordings(db):
    _song(db, "rent", musicbrainz_recording_id="rec-rent")
    _song(db, "licensed", musicbrainz_recording_id="rec-hip", show_name="TPB")
    _song(db, "kept", musicbrainz_recording_id="rec-x", show_name="Once")
    _song(db, "failed", musicbrainz_recording_id="rec-down", show_name="Wicked")
    _song(db, "unlinked", show_name="Cats")
    _song(
        db,
        "hand",
        musicbrainz_recording_id="rec-hip",
        show_name="Mine",
        show_name_hand_set_at=utc_now(),
    )
    mb = MusicBrainzData(
        recordings={"rec-rent": None, "rec-hip": None, "rec-x": None, "rec-down": None},
        shows={"rec-rent": "Rent", "rec-hip": None, "rec-x": "Once"},
    )

    report = rebuild(db, mb)

    assert {s: _show(db, s) for s in ("rent", "licensed", "kept", "failed")} == {
        "rent": "Rent",
        "licensed": None,
        "kept": "Once",
        "failed": "Wicked",
    }
    assert _show(db, "unlinked") is None
    assert _show(db, "hand") == "Mine"
    assert report["shows"]["counts"] == {"changed": 3, "hand_set": 1}
    assert {
        (row["songId"], row["before"], row["after"])
        for row in report["shows"]["changed"]
    } == {("rent", None, "Rent"), ("licensed", "TPB", None), ("unlinked", "Cats", None)}
    assert report["before"]["songsWithShow"] == 5
    assert report["after"]["songsWithShow"] == 4


def test_fetch_keeps_each_recordings_show(db, tmp_path):
    from app.services.artist_credits_rebuild import fetch_musicbrainz

    _song(db, "a", musicbrainz_recording_id="rec-a")
    _song(db, "b", musicbrainz_recording_id="rec-b")

    def lookup(recording_id, cache_dir):
        return None if recording_id == "rec-b" else ("Rent", None)

    with patch(
        "app.services.musicbrainz_service.get_recording_details", side_effect=lookup
    ):
        data = fetch_musicbrainz(db, tmp_path)

    assert data.shows == {"rec-a": "Rent"}
    assert data.recordings == {"rec-a": None, "rec-b": None}
