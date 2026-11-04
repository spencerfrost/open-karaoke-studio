"""The admin "Compare breaks" page: breaks from the singing map next to the
breaks the TV shows today (gaps between aligned words), and the moments
worth listening to.

Nothing here changes what the TV shows. The page exists to check, by ear,
whether the map finds breaks as well as the word gaps or better.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, Optional

from app.db.models import DbSong
from app.services.singing_map import (
    Interval,
    LineWindow,
    breaks_from_map,
    intersect,
    line_windows,
    subtract,
)

logger = logging.getLogger(__name__)

# Two breaks agree when both their ends are within this of each other.
AGREE_SECONDS = 1.5
# Backing-only stretches shorter than this aren't listed as moments.
BACKING_ONLY_MIN_SECONDS = 2.0
# A backing-only stretch has lyrics on screen when it overlaps a line by this.
ON_SCREEN_MIN_SECONDS = 0.5

# What can be said about each kind of moment, by ear.
BREAK_ANSWERS = ("map_right", "today_right", "both_wrong", "either_fine")
# Backing alone with no lyrics on screen: the map lets it be part of a break.
BACKING_OFF_SCREEN_ANSWERS = ("bar_fine", "no_bar")
# Backing alone with lyrics on screen: they count as singing, so no break.
BACKING_ON_SCREEN_ANSWERS = ("lyrics_match", "lyrics_dont_match")


def allowed_answers(moment: dict[str, Any]) -> tuple[str, ...]:
    if moment["kind"] == "break":
        return BREAK_ANSWERS
    return (
        BACKING_ON_SCREEN_ANSWERS if moment["onScreen"] else BACKING_OFF_SCREEN_ANSWERS
    )


def map_is_right_answer(moment: dict[str, Any]) -> str:
    """The answer that says the map's call on this moment is right."""
    if moment["kind"] == "break":
        return "map_right"
    return "lyrics_match" if moment["onScreen"] else "bar_fine"


def needs_answer(moment: dict[str, Any]) -> bool:
    """Breaks both methods agree on have nothing to decide."""
    return not (moment["kind"] == "break" and moment["agree"])


def _key_span(span: Optional[list[float]]) -> str:
    return "-" if span is None else f"{span[0]:.2f}-{span[1]:.2f}"


def moment_key(moment: dict[str, Any]) -> str:
    """Identifies a moment by its exact times: a re-measure that moves it
    makes it a new moment."""
    if moment["kind"] == "break":
        return f"break:{_key_span(moment['map'])}:{_key_span(moment['wordGaps'])}"
    return f"backing:{_key_span([moment['start'], moment['end']])}"


def _load_json(text: Optional[str]) -> Optional[dict[str, Any]]:
    if not text:
        return None
    try:
        value = json.loads(text)
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


@dataclass
class SongComparison:
    singing_map: Optional[dict[str, Any]]
    windows: list[LineWindow]
    has_word_timing: bool
    map_breaks: Optional[list[dict[str, Any]]]  # None: not measured yet
    word_gap_breaks: list[dict[str, Any]]
    moments: Optional[list[dict[str, Any]]]  # None: not measured yet

    @property
    def disagreements(self) -> Optional[int]:
        if self.moments is None:
            return None
        return sum(1 for m in self.moments if m["kind"] == "break" and not m["agree"])


def compare_song(song: DbSong) -> SongComparison:
    word_synced = _load_json(song.word_synced_lyrics)
    words = (word_synced or {}).get("words") or []
    windows = line_windows(song.synced_lyrics, words)
    word_gap_breaks = list((word_synced or {}).get("instrumental_intervals") or [])
    singing_map = _load_json(song.singing_map)

    map_breaks = moments = None
    if singing_map is not None:
        map_breaks = breaks_from_map(singing_map, windows)
        moments = build_moments(singing_map, windows, map_breaks, word_gap_breaks)

    return SongComparison(
        singing_map=singing_map,
        windows=windows,
        has_word_timing=bool(words),
        map_breaks=map_breaks,
        word_gap_breaks=word_gap_breaks,
        moments=moments,
    )


def _span(interval: dict[str, Any]) -> Interval:
    return (float(interval["start"]), float(interval["end"]))


def _overlap(a: Interval, b: Interval) -> float:
    return max(0.0, min(a[1], b[1]) - max(a[0], b[0]))


def build_moments(
    singing_map: dict[str, Any],
    windows: list[LineWindow],
    map_breaks: list[dict[str, Any]],
    word_gap_breaks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Everything worth a listen, in song order.

    - `break`: a break either method found. `map` and `wordGaps` hold each
      method's version ([start, end]) or None; `agree` is true when both found
      it and their ends are within AGREE_SECONDS.
    - `backing_only`: backing singing while the lead is silent, with whether
      a lyric line is on screen then (`onScreen`, and that line's text).
    """
    moments: list[dict[str, Any]] = []

    unmatched_gaps = [_span(b) for b in word_gap_breaks]
    for map_break in map_breaks:
        mine = _span(map_break)
        best = max(unmatched_gaps, key=lambda g: _overlap(mine, g), default=None)
        if best is not None and _overlap(mine, best) > 0:
            unmatched_gaps.remove(best)
            agree = (
                abs(mine[0] - best[0]) <= AGREE_SECONDS
                and abs(mine[1] - best[1]) <= AGREE_SECONDS
            )
            moments.append(_break_moment(mine, best, agree))
        else:
            moments.append(_break_moment(mine, None, False))
    for gap in unmatched_gaps:
        moments.append(_break_moment(None, gap, False))

    lead = [tuple(i) for i in singing_map.get("lead") or []]
    backing = [tuple(i) for i in singing_map.get("backing") or []]
    for start, end in subtract(backing, lead):
        if end - start < BACKING_ONLY_MIN_SECONDS:
            continue
        line = max(
            windows,
            key=lambda w: _overlap((start, end), (w.start, w.end)),
            default=None,
        )
        on_screen = (
            line is not None
            and _overlap((start, end), (line.start, line.end)) >= ON_SCREEN_MIN_SECONDS
        )
        moments.append(
            {
                "kind": "backing_only",
                "start": round(start, 2),
                "end": round(end, 2),
                "onScreen": on_screen,
                "lineText": line.text if on_screen and line else None,
            }
        )

    moments.sort(key=lambda m: (m["start"], m["end"]))
    for moment in moments:
        moment["key"] = moment_key(moment)
    return moments


def _break_moment(
    map_span: Optional[Interval], gap_span: Optional[Interval], agree: bool
) -> dict[str, Any]:
    spans = [s for s in (map_span, gap_span) if s is not None]
    return {
        "kind": "break",
        "start": round(min(s[0] for s in spans), 2),
        "end": round(max(s[1] for s in spans), 2),
        "map": [round(v, 2) for v in map_span] if map_span else None,
        "wordGaps": [round(v, 2) for v in gap_span] if gap_span else None,
        "agree": agree,
    }


def summarize(song: DbSong, answers: dict[str, str]) -> dict[str, Any]:
    """One row of the song list. `answers` is the song's, by moment key."""
    comparison = compare_song(song)
    to_answer = [m for m in comparison.moments or [] if needs_answer(m)]
    answered = [
        answers[m["key"]] for m in comparison.moments or [] if m["key"] in answers
    ]
    return {
        "songId": song.id,
        "title": song.title,
        "artist": song.artist,
        "measured": comparison.singing_map is not None,
        "hasWordTiming": comparison.has_word_timing,
        "wordGapBreaks": len(comparison.word_gap_breaks),
        "mapBreaks": (
            None if comparison.map_breaks is None else len(comparison.map_breaks)
        ),
        "disagreements": comparison.disagreements,
        # Moments still to listen to, and the answers about what it shows now.
        "toCheck": sum(1 for m in to_answer if m["key"] not in answers),
        "answers": answered,
    }


def tally(rows: list[dict[str, Any]]) -> dict[str, int]:
    """How many of each answer, over every song's current moments."""
    counts: dict[str, int] = {}
    for row in rows:
        for answer in row["answers"]:
            counts[answer] = counts.get(answer, 0) + 1
    return counts


def detail(song: DbSong, answers: dict[str, str]) -> dict[str, Any]:
    """Everything the page shows for one song, each moment with its answer."""
    comparison = compare_song(song)
    for moment in comparison.moments or []:
        moment["answer"] = answers.get(moment["key"])
    singing_map = comparison.singing_map or {}
    lead = [tuple(i) for i in singing_map.get("lead") or []]
    backing = singing_map.get("backing")
    return {
        "songId": song.id,
        "title": song.title,
        "artist": song.artist,
        "duration": singing_map.get("duration") or song.duration,
        "measured": comparison.singing_map is not None,
        "measuredAt": singing_map.get("measured_at"),
        "params": singing_map.get("params"),
        "hasWordTiming": comparison.has_word_timing,
        "lead": [list(i) for i in lead],
        "backing": backing,
        # Backing while a line is on screen: what counts as singing for breaks.
        "backingOnScreen": [
            [round(s, 2), round(e, 2)]
            for s, e in intersect(
                [tuple(i) for i in backing or []],
                [(w.start, w.end) for w in comparison.windows],
            )
        ],
        "lines": [
            {
                "index": w.index,
                "start": round(w.start, 2),
                "end": round(w.end, 2),
                "text": w.text,
                "timed": w.timed,
            }
            for w in comparison.windows
        ],
        "mapBreaks": comparison.map_breaks,
        "wordGapBreaks": comparison.word_gap_breaks,
        "moments": comparison.moments,
    }


class BadAnswer(ValueError):
    pass


def save_answers(
    db: Any, song: DbSong, items: list[dict[str, Any]], user_id: Optional[int]
) -> None:
    """Save answers ({"key", "answer"}, answer None to clear) about moments
    the song shows now, and commit. A key it no longer shows, or an answer
    that doesn't fit the moment, raises BadAnswer and saves nothing."""
    from app.repositories.break_check_repository import BreakCheckRepository

    comparison = compare_song(song)
    if comparison.singing_map is None:
        raise BadAnswer("This song has no singing map yet")
    moments = {m["key"]: m for m in comparison.moments or []}

    checked = []
    for item in items:
        moment = moments.get(item.get("key"))
        if moment is None:
            raise BadAnswer(f"No moment {item.get('key')!r} on this song now")
        answer = item.get("answer")
        if answer is not None and answer not in allowed_answers(moment):
            raise BadAnswer(f"{answer!r} isn't an answer for this moment")
        checked.append((moment, answer))

    repo = BreakCheckRepository(db)
    for moment, answer in checked:
        repo.save(
            song_id=song.id,
            moment=moment,
            answer=answer,
            singing_map=comparison.singing_map,
            user_id=user_id,
        )
    db.commit()
