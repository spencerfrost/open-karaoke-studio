"""Lyrics line fixes: a person's correction of one line, kept over every later job.

A fix is stored as a row (`lyrics_line_fixes`), not only as an edit to the LRC.
Every path that stores lyrics runs the text through `apply_line_fixes` first,
so a re-time, a new fetch or a re-alignment puts the fixed text back on its
line instead of losing it.

Finding the line again
----------------------
Line numbers and timestamps both move: re-timing rewrites every timestamp,
break formatting inserts blank lines, a fetched LRC may have a line more or
less. So a fix remembers what is stable about its line:

- its words before and after the fix (a line reading either is a candidate),
- the sung lines either side of it,
- which of the candidates it was, counting from the start of the song,
- its LRC time, as the last tie-break.

Candidates are ranked by neighbours matched, then place among candidates, then
closeness in time. A fix with no candidate is "lost": nothing is changed, and
the admin lists it.

Words on a line are compared without case or punctuation (as lyrics words
keys are), so a fix that only changes punctuation or case still finds its line.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable, Literal, Mapping, Optional, Protocol, Sequence

from app.services.lyrics_analysis import (
    LRC_LINE_PATTERN,
    LrcLine,
    parse_lrc_lines,
    word_tokens,
)

# A line's text is at most this long; anything longer is not one line.
MAX_LINE_LENGTH = 300

# How close a line's timestamp must be to the one the screen sent, in seconds.
_TIMESTAMP_TOLERANCE = 0.011
# Window edges when a line has no neighbour on one side, in seconds.
_NO_PREVIOUS_LEAD = 5.0
_NO_NEXT_TAIL = 10.0
_MIN_WINDOW = 0.5


class LineFixLike(Protocol):
    """What matching needs from a fix: the model row or a plain stand-in."""

    old_text: str
    new_text: str
    line_start: Optional[float]
    prev_text: Optional[str]
    next_text: Optional[str]
    occurrence: int


@dataclass
class LineAnchor:
    """Where a line sits, as a new fix records it."""

    prev_text: Optional[str]
    next_text: Optional[str]
    occurrence: int


@dataclass
class _Line:
    """One line of a lyrics text, in the order it appears."""

    text: str
    timestamp: Optional[float]


def line_key(text: Optional[str]) -> str:
    """A line's words for comparing: lowercase, no punctuation, single spaces."""
    return " ".join(word_tokens(text)) if text else ""


def clean_line_text(text: str) -> str:
    """What a person typed, as one stored line: trimmed, inner spaces collapsed."""
    return " ".join(text.split())


# ---------------------------------------------------------------------------
# Lines of a lyrics text
# ---------------------------------------------------------------------------


def _synced_lines(content: str) -> list[_Line]:
    """LRC lines, positioned as word timings' `line_index` counts them."""
    return [_Line(line["text"], line["timestamp"]) for line in parse_lrc_lines(content)]


def _plain_lines(content: str) -> list[_Line]:
    return [_Line(text.strip(), None) for text in content.splitlines()]


def _lines(content: str, source_type: Literal["plain", "synced"]) -> list[_Line]:
    return _synced_lines(content) if source_type == "synced" else _plain_lines(content)


def _neighbour_index(lines: Sequence[_Line], index: int, step: int) -> Optional[int]:
    """The nearest sung line before (step -1) or after (step 1) `index`."""
    i = index + step
    while 0 <= i < len(lines):
        if line_key(lines[i].text):
            return i
        i += step
    return None


def _neighbour_keys(lines: Sequence[_Line], index: int) -> tuple[str, str]:
    """The words of the sung lines before and after `index` ("" if none)."""
    prev_index = _neighbour_index(lines, index, -1)
    next_index = _neighbour_index(lines, index, 1)
    return (
        line_key(lines[prev_index].text) if prev_index is not None else "",
        line_key(lines[next_index].text) if next_index is not None else "",
    )


def _candidates(lines: Sequence[_Line], keys: set[str]) -> list[int]:
    return [i for i, line in enumerate(lines) if line_key(line.text) in keys]


# ---------------------------------------------------------------------------
# Finding a line
# ---------------------------------------------------------------------------


def find_shown_line(content: str, *, line_start: float, text: str) -> Optional[int]:
    """The LRC line the screen showed at `line_start` reading `text`, if it's still there.

    Returns its position as word timings count lines (`line_index`).
    """
    wanted = clean_line_text(text)
    for index, line in enumerate(_synced_lines(content)):
        if (
            line.timestamp is not None
            and abs(line.timestamp - line_start) <= _TIMESTAMP_TOLERANCE
            and clean_line_text(line.text) == wanted
        ):
            return index
    return None


def anchor_for_line(content: str, index: int, *, reads: Sequence[str]) -> LineAnchor:
    """What a fix on line `index` remembers about where it is.

    `reads` are the fix's texts, old and new: every line reading either is
    counted for its place, the same way matching counts them later.
    """
    lines = _synced_lines(content)
    keys = {line_key(text) for text in [lines[index].text, *reads]} - {""}
    prev_index = _neighbour_index(lines, index, -1)
    next_index = _neighbour_index(lines, index, 1)
    return LineAnchor(
        prev_text=lines[prev_index].text if prev_index is not None else None,
        next_text=lines[next_index].text if next_index is not None else None,
        occurrence=_candidates(lines, keys).index(index),
    )


def _locate(
    lines: Sequence[_Line], fix: LineFixLike, *, anchored: bool = False
) -> Optional[int]:
    """The best candidate line for `fix`.

    With `anchored`, the best candidate only counts when something besides
    its words ties it to the fix: a neighbour that matches, or the same LRC
    time. Without that, a line that merely reads the same is not the fix's.
    """
    keys = {line_key(fix.old_text), line_key(fix.new_text)} - {""}
    candidates = _candidates(lines, keys)
    if not candidates:
        return None
    want_prev, want_next = line_key(fix.prev_text), line_key(fix.next_text)

    def rank(position: int) -> tuple[int, int, float]:
        index = candidates[position]
        prev_key, next_key = _neighbour_keys(lines, index)
        neighbours = int(prev_key == want_prev) + int(next_key == want_next)
        same_place = int(position == fix.occurrence)
        timestamp = lines[index].timestamp
        distance = (
            abs(timestamp - fix.line_start)
            if timestamp is not None and fix.line_start is not None
            else 0.0
        )
        return (neighbours, same_place, -distance)

    best = max(range(len(candidates)), key=rank)
    if anchored:
        timestamp = lines[candidates[best]].timestamp
        same_time = (
            timestamp is not None
            and fix.line_start is not None
            and abs(timestamp - fix.line_start) <= _TIMESTAMP_TOLERANCE
        )
        if not rank(best)[0] and not same_time:
            return None
    return candidates[best]


def locate_fix(
    content: Optional[str],
    fix: LineFixLike,
    source_type: Literal["plain", "synced"] = "synced",
    *,
    anchored: bool = False,
) -> Optional[int]:
    """The line `fix` belongs on in `content`, or None when it's lost.

    `anchored` asks for more than matching words (see `_locate`).
    """
    if not content or not content.strip():
        return None
    return _locate(_lines(content, source_type), fix, anchored=anchored)


def fixes_shown(content: Optional[str], fixes: Sequence[LineFixLike]) -> list[bool]:
    """For each fix, whether the synced lyrics show its text on its line.

    The lyrics are parsed once for all of them.
    """
    if not content or not content.strip():
        return [False] * len(fixes)
    lines = _synced_lines(content)
    shown = []
    for fix in fixes:
        index = _locate(lines, fix)
        shown.append(
            index is not None
            and clean_line_text(lines[index].text) == clean_line_text(fix.new_text)
        )
    return shown


def fix_is_shown(content: Optional[str], fix: LineFixLike) -> bool:
    """Whether the synced lyrics show the fixed text on the fix's line."""
    return fixes_shown(content, [fix])[0]


# ---------------------------------------------------------------------------
# Applying fixes
# ---------------------------------------------------------------------------


def _replace_synced_line(content: str, index: int, text: str) -> str:
    """Set the text of LRC line `index` (word-timing numbering), keeping its timestamp."""
    raw_lines = content.strip().splitlines()
    raw_index = parse_lrc_lines(content)[index]["line_index"]
    stripped = raw_lines[raw_index].strip()
    match = LRC_LINE_PATTERN.match(stripped)
    if match is None:  # parse_lrc_lines only returns matching lines
        return content
    raw_lines[raw_index] = stripped[: match.start(4)] + text
    return "\n".join(raw_lines)


def _replace_plain_line(content: str, index: int, text: str) -> str:
    raw_lines = content.splitlines()
    raw_lines[index] = text
    return "\n".join(raw_lines)


def replace_line(
    content: str, index: int, text: str, source_type: Literal["plain", "synced"]
) -> str:
    """`content` with line `index` reading `text`."""
    if source_type == "synced":
        return _replace_synced_line(content, index, text)
    return _replace_plain_line(content, index, text)


def apply_line_fixes(
    content: Optional[str],
    fixes: Iterable[LineFixLike],
    source_type: Literal["plain", "synced"] = "synced",
) -> Optional[str]:
    """`content` with every fix's text on its line, oldest fix first.

    Returns `content` itself (the same object) when nothing changes. Lost
    fixes change nothing.
    """
    if not content or not content.strip():
        return content
    result = content
    for fix in fixes:
        lines = _lines(result, source_type)
        index = _locate(lines, fix)
        if index is None:
            continue
        new_text = clean_line_text(fix.new_text)
        if lines[index].text == new_text:
            continue
        result = replace_line(result, index, new_text, source_type)
    return result


# ---------------------------------------------------------------------------
# One line's word timing
# ---------------------------------------------------------------------------


def _word_span(
    words: Sequence[Mapping[str, Any]], index: int
) -> Optional[tuple[float, float]]:
    times = [(w["start"], w["end"]) for w in words if w.get("line_index") == index]
    if not times:
        return None
    return min(start for start, _ in times), max(end for _, end in times)


def line_window(
    lrc_lines: Sequence[LrcLine],
    words: Sequence[Mapping[str, Any]],
    index: int,
    song_duration: Optional[float] = None,
) -> tuple[float, float]:
    """Where line `index` may be sung: from the previous line's end to the next one's start.

    A neighbour with word timing ends (or starts) where its words do; one
    without uses its LRC time, and for the previous line that is when it
    starts, so this line's own time opens the window instead. With no sung
    line before it, the window opens a few seconds before the line's own
    time; with none after, it runs a few seconds past it.
    """
    own = lrc_lines[index]["timestamp"]
    prev_index = next(
        (i for i in range(index - 1, -1, -1) if lrc_lines[i]["text"].strip()), None
    )
    next_index = next(
        (i for i in range(index + 1, len(lrc_lines)) if lrc_lines[i]["text"].strip()),
        None,
    )

    if prev_index is None:
        start = max(0.0, own - _NO_PREVIOUS_LEAD)
    else:
        span = _word_span(words, prev_index)
        start = span[1] if span else own

    if next_index is None:
        end = own + _NO_NEXT_TAIL
        if song_duration:
            end = min(end, song_duration)
    else:
        span = _word_span(words, next_index)
        end = span[0] if span else lrc_lines[next_index]["timestamp"]

    if end - start < _MIN_WINDOW:
        end = start + _MIN_WINDOW
    return start, end


def carry_line_words(
    payload: Mapping[str, Any], index: int, text: str
) -> tuple[list[dict[str, Any]], bool]:
    """Line `index`'s words reading `text`, on the timing the line already has.

    The line keeps its place in time until its new words are timed: with the
    same number of words each keeps its own times, otherwise the new words
    share the line's span evenly (score 0: nothing heard them there).

    Returns the words and whether they are still the sung words, word for
    word (only case or punctuation changed), so their timing needs no new
    listen. A line with no words has none to carry.
    """
    old = [w for w in payload.get("words", []) if w.get("line_index") == index]
    tokens = text.split()
    if not old or not tokens:
        return [], False
    if len(tokens) == len(old):
        words = [{**w, "word": token} for w, token in zip(old, tokens)]
        same_words = all(
            line_key(str(w.get("word", ""))) == line_key(token)
            for w, token in zip(old, tokens)
        )
        return words, same_words
    start = min(w["start"] for w in old)
    end = max(w["end"] for w in old)
    step = (end - start) / len(tokens)
    return [
        {
            "word": token,
            "start": round(start + i * step, 3),
            "end": round(start + (i + 1) * step, 3),
            "score": 0.0,
            "line_index": index,
        }
        for i, token in enumerate(tokens)
    ], False


def replace_line_words(
    payload: dict[str, Any], index: int, line_words: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """The word-timing payload with line `index`'s words replaced by `line_words`.

    Words stay in line order (the order the token walk expects), and the
    breaks, counts and mean score are worked out again from the new words.
    """
    from app.services.lyrics_alignment import _build_instrumental_intervals

    kept = [w for w in payload.get("words", []) if w.get("line_index") != index]
    added = [{**w, "line_index": index} for w in line_words]
    # sorted() is stable, so each line's words keep their order.
    words = sorted(kept + added, key=lambda w: w["line_index"])
    mean_score = (
        round(sum(w.get("score", 0.0) for w in words) / len(words), 3) if words else 0.0
    )
    return {
        **payload,
        "words": words,
        "instrumental_intervals": _build_instrumental_intervals(words),  # type: ignore[arg-type]
        "word_count": len(words),
        "mean_score": mean_score,
    }


def read_word_payload(raw: Optional[str]) -> Optional[dict[str, Any]]:
    """The stored word-timing JSON, or None when there's none or it's unreadable."""
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError):
        return None
    if not isinstance(payload, dict) or not isinstance(payload.get("words"), list):
        return None
    return payload


@dataclass
class LineFixSnapshot:
    """A fix's matching fields on their own: a row read out of the database
    for use after its session is closed, or a stand-in for an edit being made."""

    old_text: str
    new_text: str
    line_start: Optional[float]
    prev_text: Optional[str]
    next_text: Optional[str]
    occurrence: int
    id: Optional[int] = None


def snapshot_fix(fix: LineFixLike, fix_id: int) -> LineFixSnapshot:
    return LineFixSnapshot(
        id=fix_id,
        old_text=fix.old_text,
        new_text=fix.new_text,
        line_start=fix.line_start,
        prev_text=fix.prev_text,
        next_text=fix.next_text,
        occurrence=fix.occurrence,
    )


def apply_fixes_to_attempts(
    attempts: Sequence[dict[str, Any]],
    fixes: Sequence[LineFixLike],
    rejected_keys: Iterable[str] = (),
) -> list[dict[str, Any]]:
    """Alignment candidates with every fix on its line.

    A candidate whose fixed words were reported as wrong is dropped, and
    candidates that read the same once fixed are kept once.
    """
    if not fixes:
        return list(attempts)
    from app.services.lyrics_retiming import lyrics_words_key

    rejected = set(rejected_keys)
    fixed: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for attempt in attempts:
        source_type = attempt["source_type"]
        content = apply_line_fixes(attempt["content"], fixes, source_type)
        if content is not attempt["content"]:
            if content and lyrics_words_key(content, source_type) in rejected:
                continue
            attempt = {**attempt, "content": content}
        key = (source_type, attempt["content"])
        if key in seen:
            continue
        seen.add(key)
        fixed.append(attempt)
    return fixed
