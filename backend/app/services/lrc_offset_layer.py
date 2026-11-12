"""
The LRC offset sweep layer: how far each song's whole LRC is off, measured
once and kept, so the shift can be heard before it's applied.

An LRC can be off by seconds and still pass the alignment gate: each line's
window then holds someone singing, just the wrong line, which scores about
0.4–0.5. The sweep re-aligns the LRC at every shift from −12 to +12 s and
keeps the scores. A shift that passes the gate (see _offset_rejection_reason
in jobs/lyrics_tasks.py) waits on the song as `lrc_offset_pending_shift`,
with its aligned words in the layer, for the Compare word timing page.
"Apply shifts" then shifts and re-aligns the songs waiting, without sweeping
again. The sweep and apply run in jobs/lrc_offset_tasks.py.

Stored per song:

- `lrc_offset_sweep` (JSON): {"version", "measured_at", "max_shift", "step",
  "fine_step", "shift", "score", "baseline_score", "gain", "scores":
  {shift: score}, "passes", "rejection", "shifted": {"words", "mean_score"}
  when it passes, "answers": {moment key: answer} from Compare word timing,
  "applied_at" and "applied_shift" once applied}; {"failed": true, ...} when
  the sweep couldn't run.
- `lrc_offset_version`: services/processing_versions.py LRC_OFFSET_VERSION.
- `lrc_offset_lrc_md5`: md5 of the synced_lyrics it measured. When the
  lyrics change, the layer is stale and "missing" sweeps the song again.
- `lrc_offset_pending_shift`: the shift waiting to be applied, or null.
"""

import hashlib
import json
from typing import Any, Optional

from sqlalchemy.orm import Session, undefer

from app.db.models import DbSong
from app.services.processing_versions import LRC_OFFSET_VERSION, is_behind

# The sweep: every whole second out to ±12 s, then 0.1 s steps within half a
# second of the best, which finds the peak (about 1.5 s wide) without the
# fine pass on songs whose best is no shift. 25 alignments for most songs.
SWEEP_MAX_SECONDS = 12.0
SWEEP_STEP_SECONDS = 1.0
SWEEP_FINE_STEP_SECONDS = 0.1
SWEEP_FINE_REACH_SECONDS = 0.5

# A gain this many times the gate's is "clear" on Compare word timing; less is
# "borderline", the songs most likely to be noise.
CLEAR_GAIN_MULTIPLE = 2

REVIEW_ID = "lrc_offset_sweep"


def lrc_md5(content: Optional[str]) -> Optional[str]:
    if not content:
        return None
    return hashlib.md5(content.encode("utf-8")).hexdigest()


def read_layer(song: DbSong) -> Optional[dict[str, Any]]:
    if not song.lrc_offset_sweep:
        return None
    try:
        layer = json.loads(song.lrc_offset_sweep)
    except (TypeError, ValueError):
        return None
    return layer if isinstance(layer, dict) else None


def is_current(song_lyrics_md5: Optional[str], version, measured_md5) -> bool:
    """Whether a song's sweep is of its lyrics as they are now, by this version."""
    return (
        not is_behind(version, LRC_OFFSET_VERSION)
        and measured_md5 is not None
        and measured_md5 == song_lyrics_md5
    )


def _rows(session: Session) -> list:
    """Every song with synced lyrics, with what selection needs and no more."""
    return (
        session.query(
            DbSong.id,
            DbSong.synced_lyrics,
            DbSong.lrc_offset_version,
            DbSong.lrc_offset_lrc_md5,
            DbSong.lrc_offset_pending_shift,
        )
        .filter(DbSong.synced_lyrics.isnot(None), DbSong.synced_lyrics != "")
        .order_by(DbSong.id)
        .all()
    )


def _has_vocals(song_id: str) -> bool:
    from app.services.file_service import FileService

    return FileService().get_vocals_path(song_id, ".mp3").exists()


def _selection(session: Session) -> dict[str, list[str]]:
    covered, missing, apply = [], [], []
    for row in _rows(session):
        if not _has_vocals(row.id):
            continue
        covered.append(row.id)
        current = is_current(
            lrc_md5(row.synced_lyrics), row.lrc_offset_version, row.lrc_offset_lrc_md5
        )
        if not current:
            missing.append(row.id)
        elif row.lrc_offset_pending_shift is not None:
            apply.append(row.id)
    return {"all": covered, "missing": missing, "apply": apply}


def select_ids(session: Session, mode: str) -> list[str]:
    """The songs a run in `mode` works through: "missing" sweeps songs never
    swept, or whose lyrics changed since; "all" sweeps every song with synced
    lyrics and vocals; "apply" shifts the ones waiting with a current sweep."""
    return _selection(session)[mode]


def summary(session: Session) -> dict:
    selection = _selection(session)
    covered = len(selection["all"])
    return {
        "coverage": {"have": covered - len(selection["missing"]), "of": covered},
        "modeCounts": {mode: len(ids) for mode, ids in selection.items()},
    }


# --- Compare word timing ---------------------------------------------------


class LrcOffsetReview:
    """The songs waiting for "Apply shifts", as a Compare word timing experiment:
    today's timing against the timing with the sweep's shift.

    Reads the database instead of an experiment folder, and keeps the answers
    in each song's layer, so it works wherever the job ran (prod included).
    """

    def __init__(self, session: Session):
        self.session = session

    def meta(self) -> dict:
        from app.jobs.lyrics_tasks import MIN_OFFSET_GAIN

        return {
            "id": REVIEW_ID,
            "name": "LRC offset sweep: shifts to apply",
            "description": (
                "Songs whose whole LRC the sweep job found off, by up to 12 s, waiting "
                "for Apply shifts on the jobs page. Today's timing against the timing "
                "with the shift. Applying shifts every song listed here."
            ),
            "a": {"key": "today", "label": "Today's timing"},
            "b": {"key": "shifted", "label": "Shifted by the sweep"},
            "groups": [
                {
                    "key": "clear",
                    "label": f"Gains {CLEAR_GAIN_MULTIPLE * MIN_OFFSET_GAIN:.2f} or more",
                },
                {"key": "borderline", "label": "Only just passes the gate"},
            ],
            "compareEnds": False,
        }

    def _songs(self, song_id: Optional[str] = None) -> list[DbSong]:
        query = (
            self.session.query(DbSong)
            .options(undefer(DbSong.lrc_offset_sweep))
            .filter(DbSong.lrc_offset_pending_shift.isnot(None))
        )
        if song_id is not None:
            query = query.filter(DbSong.id == song_id)
        return [
            song
            for song in query.order_by(DbSong.id).all()
            if is_current(
                lrc_md5(song.synced_lyrics),
                song.lrc_offset_version,
                song.lrc_offset_lrc_md5,
            )
        ]

    def _result(self, song: DbSong) -> Optional[dict]:
        from app.jobs.lyrics_tasks import MIN_OFFSET_GAIN

        layer = read_layer(song) or {}
        shifted = layer.get("shifted")
        try:
            today = json.loads(song.word_synced_lyrics or "null")
        except ValueError:
            today = None
        gain = layer.get("gain") or 0.0
        return {
            "id": song.id,
            "title": song.title,
            "artist": song.artist,
            "group": (
                "clear"
                if gain >= CLEAR_GAIN_MULTIPLE * MIN_OFFSET_GAIN
                else "borderline"
            ),
            "shift": layer.get("shift"),
            "gain": gain,
            "today": (
                {
                    "words": today.get("words"),
                    "mean_score": today.get("mean_score"),
                    "bad": None,
                    "lines": None,
                }
                if isinstance(today, dict)
                else None
            ),
            "shifted": (
                {
                    "words": shifted.get("words"),
                    "mean_score": shifted.get("mean_score"),
                    "bad": None,
                    "lines": None,
                }
                if isinstance(shifted, dict)
                else None
            ),
        }

    def results(self) -> list[dict]:
        return [r for song in self._songs() if (r := self._result(song)) is not None]

    def result(self, song_id: str) -> Optional[dict]:
        songs = self._songs(song_id)
        return self._result(songs[0]) if songs else None

    def answers(self) -> dict[str, dict[str, str]]:
        return {
            song.id: (read_layer(song) or {}).get("answers") or {}
            for song in self._songs()
        }

    def write_song_answers(self, song_id: str, song_answers: dict[str, str]) -> None:
        songs = self._songs(song_id)
        if not songs:
            return
        song = songs[0]
        layer = read_layer(song) or {}
        layer["answers"] = song_answers
        song.lrc_offset_sweep = json.dumps(layer)
        self.session.commit()
