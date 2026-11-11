"""Tests for bringing a song up to date when it's queued to sing."""

from types import SimpleNamespace
from unittest.mock import call, patch

import pytest

from app.jobs.lyrics_tasks import _save_word_timing_version
from app.jobs.metadata_tasks import update_song_step
from app.jobs.song_updates import update_queued_song
from app.services import processing_versions as versions

SONG_ID = "song-1"

# A song no step is behind on.
UP_TO_DATE = {
    "loudness_version": versions.LOUDNESS_VERSION,
    "singing_map_version": versions.SINGING_MAP_VERSION,
    "vocal_range_version": versions.VOCAL_RANGE_VERSION,
    "word_timing_version": versions.WORD_TIMING_VERSION,
    "acoustid_fingerprint_status": "matched",
    "album_checked_at": None,
    "album": "Abbey Road",
    "synced_lyrics": "[00:01.00]Blackbird singing",
}


@pytest.fixture
def mocks(db):  # noqa: ARG001 - db gives each test clean tables
    with (
        patch("app.jobs.song_updates.celery") as celery,
        patch("app.jobs.song_updates.enqueue_song_alignment") as align,
        patch("app.services.file_service.FileService") as file_service,
    ):
        align.return_value = {"dispatched": True}
        vocals = file_service.return_value.get_vocals_path.return_value
        vocals.exists.return_value = True
        yield SimpleNamespace(celery=celery, align=align, vocals=vocals)


def _add_up_to_date(add_song, db, **fields):
    """A song with an album cover, so the album lookup has nothing to do."""
    from app.db.models import DbAlbum

    album = DbAlbum(title="Abbey Road", cover_path="covers/abbey-road.jpg")
    db.add(album)
    db.commit()
    add_song(SONG_ID, **{**UP_TO_DATE, "album_id": album.id, **fields})


class TestUpdateQueuedSong:
    def test_an_up_to_date_song_queues_nothing(self, mocks, add_song, db):
        _add_up_to_date(add_song, db)

        assert update_queued_song(SONG_ID) == []
        mocks.celery.send_task.assert_not_called()
        mocks.align.assert_not_called()

    def test_queues_each_step_the_song_is_behind_on(self, mocks, add_song, db):
        _add_up_to_date(
            add_song,
            db,
            singing_map_version=None,
            vocal_range_version=versions.VOCAL_RANGE_VERSION - 1,
            video_id="v-1",  # never checked for an album-art video
        )

        assert update_queued_song(SONG_ID) == [
            "singing_map",
            "vocal_range",
            "album_art_videos",
        ]
        assert mocks.celery.send_task.call_args_list == [
            call("update_song_step", args=[kind, SONG_ID])
            for kind in ("singing_map", "vocal_range", "album_art_videos")
        ]

    def test_old_word_timing_is_redone_keeping_the_words(self, mocks, add_song, db):
        _add_up_to_date(add_song, db, word_timing_version=None)

        assert update_queued_song(SONG_ID) == ["word_timing"]
        (song,), kwargs = mocks.align.call_args
        assert song.id == SONG_ID
        assert kwargs == {"include_remote": False}

    def test_a_song_without_lyrics_gets_the_full_search(self, mocks, add_song, db):
        _add_up_to_date(add_song, db, word_timing_version=None, synced_lyrics=None)

        update_queued_song(SONG_ID)

        assert mocks.align.call_args.kwargs == {"include_remote": True}

    def test_no_alignment_without_vocals(self, mocks, add_song, db):
        _add_up_to_date(add_song, db, word_timing_version=None)
        mocks.vocals.exists.return_value = False

        assert update_queued_song(SONG_ID) == []
        mocks.align.assert_not_called()

    def test_an_alignment_already_running_isnt_counted(self, mocks, add_song, db):
        _add_up_to_date(add_song, db, word_timing_version=None)
        mocks.align.return_value = {"dispatched": False}

        assert update_queued_song(SONG_ID) == []

    def test_a_song_still_processing_is_left_to_its_pipeline(self, mocks, add_song):
        add_song(SONG_ID, status="processing")

        assert update_queued_song(SONG_ID) == []
        mocks.celery.send_task.assert_not_called()
        mocks.align.assert_not_called()

    def test_never_raises(self, mocks, add_song, db):
        _add_up_to_date(add_song, db, loudness_version=None)
        mocks.celery.send_task.side_effect = ConnectionError("redis is down")

        assert update_queued_song(SONG_ID) == []


class TestUpdateSongStep:
    @pytest.fixture
    def step(self):
        with patch("app.jobs.metadata_tasks.detect_and_store_loudness") as step:
            step.return_value = "ok"
            yield step

    def test_runs_the_step_for_a_song_that_needs_it(self, add_song, step):
        add_song(SONG_ID)

        result = update_song_step("loudness", SONG_ID)

        assert result == {"status": "ok", "song_id": SONG_ID}
        step.assert_called_once_with(SONG_ID)

    def test_skips_a_song_done_since_it_was_queued(self, add_song, step):
        add_song(SONG_ID, loudness_version=versions.LOUDNESS_VERSION)

        result = update_song_step("loudness", SONG_ID)

        assert result["status"] == "up_to_date"
        step.assert_not_called()

    def test_refuses_a_job_without_a_per_song_task(self, add_song):
        add_song(SONG_ID)

        with pytest.raises(ValueError, match="no per-song task"):
            update_song_step("duration", SONG_ID)


class TestSaveWordTimingVersion:
    @pytest.mark.parametrize("status", ["ok", "retimed", "no_lyrics", "plain_only"])
    def test_any_answer_saves_the_version(self, add_song, fetch_song, status):
        add_song(SONG_ID)

        _save_word_timing_version(SONG_ID, {"status": status})

        assert fetch_song(SONG_ID).word_timing_version == versions.WORD_TIMING_VERSION

    @pytest.mark.parametrize("status", ["no_audio", "not_found", "invalid_source"])
    def test_a_run_that_never_looked_saves_nothing(self, add_song, fetch_song, status):
        add_song(SONG_ID)

        _save_word_timing_version(SONG_ID, {"status": status})

        assert fetch_song(SONG_ID).word_timing_version is None
