"""Which version of each processing step is current.

Each step saves its version on the song with its result (songs.<step>_version).
A song whose saved version is empty or lower than the one here needs the step
again: it's redone when the song is next queued to sing (app.jobs.song_updates),
or by the step's library-wide run in "missing" mode.

Add 1 when a change to a step should redo songs already processed.
"""

from sqlalchemy import or_

# services/audio.py detect_loudness
LOUDNESS_VERSION = 1
# services/singing_map.py measure_singing_map
SINGING_MAP_VERSION = 1
# services/audio.py detect_vocal_range
VOCAL_RANGE_VERSION = 1
# jobs/lyrics_tasks.py align_song_lyrics. 1: aligns on the lead + backing mix.
WORD_TIMING_VERSION = 1
# services/lrc_offset_layer.py, the LRC offset sweep job. 1: ±12 s in 1 s steps,
# then 0.1 s steps around a best shift that isn't 0, on the lead + backing mix.
LRC_OFFSET_VERSION = 1


def behind(column, current: int):
    """SQL filter: the step never reached an answer, or an older version did."""
    return or_(column.is_(None), column < current)


def is_behind(saved: int | None, current: int) -> bool:
    return saved is None or saved < current
