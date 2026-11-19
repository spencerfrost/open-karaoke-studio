"""align_lyrics_line: one fixed line is timed in its own window and patched in."""

import json
import uuid
from unittest.mock import patch

from app.db.database import SessionLocal
from app.db.models import DbSong, LyricsLineFix
from app.jobs.lyrics_line_tasks import _align_line, align_lyrics_line

LRC = "[00:10.00]Is this the real life\n[00:14.00]Is this just fantasy\n[00:18.00]Caught in a landslide"
WORDS = {
    "words": [
        {"word": "Is", "start": 10.0, "end": 10.5, "score": 0.9, "line_index": 0},
        {"word": "life", "start": 10.5, "end": 12.0, "score": 0.9, "line_index": 0},
        {"word": "Caught", "start": 18.2, "end": 18.6, "score": 0.9, "line_index": 2},
    ],
    "instrumental_intervals": [],
    "aligned_at": "2026-11-11T00:00:00+00:00",
    "language": "en",
}
ALIGNED_AT = WORDS["aligned_at"]
NEW_WORDS = [
    {
        "word": w,
        "start": 14.0 + i * 0.4,
        "end": 14.3 + i * 0.4,
        "score": 0.8,
        "line_index": 0,
    }
    for i, w in enumerate("Is this just fantasy".split())
]


def _seed(*, words=True) -> str:
    song_id = str(uuid.uuid4())
    db = SessionLocal()
    db.add(
        DbSong(
            id=song_id,
            title="Bohemian",
            artist="Queen",
            synced_lyrics=LRC,
            word_synced_lyrics=json.dumps(WORDS) if words else None,
            language="en",
            duration=200.0,
        )
    )
    db.commit()
    db.close()
    return song_id


def _words(song_id: str) -> list[dict]:
    db = SessionLocal()
    raw = db.get(DbSong, song_id).word_synced_lyrics
    db.close()
    return json.loads(raw)["words"]


def _aligning(result):
    return patch("app.services.lyrics_alignment.align_line_chunks", return_value=result)


def _vocals_exist():
    return patch("app.services.file_service.FileService.get_vocals_path")


def test_the_line_is_aligned_in_its_window_and_patched_in():
    song_id = _seed()

    with _vocals_exist(), _aligning({"words": NEW_WORDS}) as align:
        status = _align_line(song_id, 1, "Is this just fantasy", ALIGNED_AT)

    assert status == "aligned"
    chunk = align.call_args.args[1][0]
    assert (chunk["start"], chunk["end"]) == (12.0, 18.2)
    words = _words(song_id)
    assert [w["word"] for w in words] == [
        "Is",
        "life",
        "Is",
        "this",
        "just",
        "fantasy",
        "Caught",
    ]
    assert [w["line_index"] for w in words] == [0, 0, 1, 1, 1, 1, 2]


def test_word_timing_replaced_since_the_fix_is_left_alone():
    song_id = _seed()

    with _vocals_exist(), _aligning({"words": NEW_WORDS}) as align:
        status = _align_line(song_id, 1, "Is this just fantasy", "an-older-run")

    assert status == "superseded"
    align.assert_not_called()


def test_a_line_edited_again_is_left_to_its_own_run():
    song_id = _seed()

    with _vocals_exist(), _aligning({"words": NEW_WORDS}) as align:
        status = _align_line(song_id, 1, "Is this just fantasty", ALIGNED_AT)

    assert status == "superseded"
    align.assert_not_called()


def test_another_line_fixed_meanwhile_doesnt_stop_the_run():
    song_id = _seed()
    db = SessionLocal()
    song = db.get(DbSong, song_id)
    song.synced_lyrics = LRC.replace("Caught in a landslide", "Caught in a land slide")
    db.commit()
    db.close()

    with _vocals_exist(), _aligning({"words": NEW_WORDS}):
        status = _align_line(song_id, 1, "Is this just fantasy", ALIGNED_AT)

    assert status == "aligned"
    assert [w["line_index"] for w in _words(song_id)] == [0, 0, 1, 1, 1, 1, 2]


def test_a_word_count_that_doesnt_match_the_line_fails():
    song_id = _seed()

    with _vocals_exist(), _aligning({"words": NEW_WORDS[:2]}):
        status = _align_line(song_id, 1, "Is this just fantasy", ALIGNED_AT)

    assert status == "failed"
    assert len(_words(song_id)) == 3


def test_word_timing_that_is_gone_means_nothing_to_patch():
    song_id = _seed(words=False)

    with _vocals_exist(), _aligning({"words": NEW_WORDS}) as align:
        status = _align_line(song_id, 1, "Is this just fantasy", ALIGNED_AT)

    assert status == "superseded"
    align.assert_not_called()


def _pending_fix(song_id: str, *, new_text="Is this just fantasy") -> int:
    db = SessionLocal()
    fix = LyricsLineFix(
        song_id=song_id,
        old_text="Is this just fantasty",
        new_text=new_text,
        line_start=14.0,
        occurrence=0,
        align_status="pending",
    )
    db.add(fix)
    db.commit()
    fix_id = fix.id
    db.close()
    return fix_id


def _status(fix_id: int) -> str:
    db = SessionLocal()
    status = db.get(LyricsLineFix, fix_id).align_status
    db.close()
    return status


def test_the_task_records_how_it_went_on_the_fix():
    song_id = _seed()
    fix_id = _pending_fix(song_id)

    with _vocals_exist(), _aligning({"words": NEW_WORDS}):
        result = align_lyrics_line.run(
            song_id, 1, "Is this just fantasy", ALIGNED_AT, fix_id=fix_id
        )

    assert result["status"] == "aligned"
    db = SessionLocal()
    stored = db.get(LyricsLineFix, fix_id)
    assert stored.align_status == "aligned"
    assert stored.aligned_at is not None
    db.close()


def test_a_superseded_run_doesnt_leave_the_fix_pending():
    """A whole-song run stored new timing: it timed the fixed line too."""
    song_id = _seed()
    fix_id = _pending_fix(song_id)

    with _vocals_exist(), _aligning({"words": NEW_WORDS}) as align:
        result = align_lyrics_line.run(
            song_id, 1, "Is this just fantasy", "an-older-run", fix_id=fix_id
        )

    assert result["status"] == "superseded"
    align.assert_not_called()
    assert _status(fix_id) == "aligned"


def test_a_superseded_run_leaves_a_fix_edited_again_to_the_newer_run():
    song_id = _seed()
    fix_id = _pending_fix(song_id, new_text="Is this just a fantasy")

    with _vocals_exist(), _aligning({"words": NEW_WORDS}):
        result = align_lyrics_line.run(
            song_id, 1, "Is this just fantasy", "an-older-run", fix_id=fix_id
        )

    assert result["status"] == "superseded"
    assert _status(fix_id) == "pending"
