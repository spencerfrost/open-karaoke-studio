"""What the vocal range method reads from a song, and when its range is out of date.

The range is decided from the lead vocal's pitch, kept only where the singing
map says the lead sings and a synced-lyrics line is on screen (see
vocal_range_child.py). So it needs the singing map first, and a range measured
before the song's synced lyrics arrived, or against older ones, is measured
again: the stored detail keeps the md5 of the lyrics it read.
"""

import hashlib
import json
from typing import Optional, cast

from app.db.models import DbSong
from app.services.audio import VocalRangeContext
from app.services.processing_versions import VOCAL_RANGE_VERSION, is_behind

# A line with no next timestamp, or a long gap before it, is on screen at most
# this long: the gap after a last line is rarely all singing.
MAX_LINE_SECONDS = 10.0

Interval = tuple[float, float]


def lyric_line_windows(
    synced_lyrics: Optional[str], duration: Optional[float]
) -> Optional[list[Interval]]:
    """Each non-blank LRC line from its timestamp to the next line's, capped.

    None without synced lyrics. Times only: the method reads no lyric text.
    """
    from app.services.lyrics_analysis import parse_lrc_lines

    if not synced_lyrics:
        return None
    starts = sorted(
        line["timestamp"]
        for line in parse_lrc_lines(synced_lyrics)
        if line["text"].strip()
    )
    if not starts:
        return None
    ends = starts[1:] + [starts[-1] + MAX_LINE_SECONDS]
    windows: list[Interval] = []
    for start, end in zip(starts, ends):
        end = min(end, start + MAX_LINE_SECONDS)
        if duration:
            end = min(end, duration)
        if end > start:
            windows.append((round(start, 2), round(end, 2)))
    return windows or None


def lead_intervals(singing_map: Optional[str]) -> Optional[list[Interval]]:
    """The singing map's lead intervals; None when the song has no map yet."""
    if not singing_map:
        return None
    return [(float(a), float(b)) for a, b in json.loads(singing_map).get("lead", [])]


def lyrics_md5(synced_lyrics: Optional[str]) -> Optional[str]:
    if not synced_lyrics:
        return None
    return hashlib.md5(synced_lyrics.encode("utf-8")).hexdigest()


def context_for(song: DbSong) -> Optional[VocalRangeContext]:
    """The method's inputs for this song, or None until its singing map exists."""
    lead = lead_intervals(cast(Optional[str], song.singing_map))
    if lead is None:
        return None
    return VocalRangeContext(
        lead=lead,
        lyric_lines=lyric_line_windows(
            cast(Optional[str], song.synced_lyrics),
            cast(Optional[float], song.duration),
        ),
    )


def is_out_of_date(song: DbSong) -> bool:
    """Whether the song's range needs measuring: never measured, by an older
    version, or against other synced lyrics than the song has now."""
    if is_behind(cast(Optional[int], song.vocal_range_version), VOCAL_RANGE_VERSION):
        return True
    stored = cast(Optional[str], song.vocal_range_detail)
    detail = json.loads(stored) if stored else {}
    return detail.get("lyrics_md5") != lyrics_md5(
        cast(Optional[str], song.synced_lyrics)
    )
