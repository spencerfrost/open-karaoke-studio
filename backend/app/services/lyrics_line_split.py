"""Breaking timed words into lyric lines a singer can read.

Speech recognition hands back its words in chunks of up to ~30 seconds, cut
where the singing pauses. WhisperX splits a chunk only where it heard the end
of a sentence, so a verse sung without full stops came back as one line with
a minute of words on it. Lines here are cut from the words' own timing:

- at a pause in the singing (`PAUSE_BREAK_SECONDS`),
- after a word ending a sentence,
- and a line still longer than `MAX_LINE_WORDS` is cut in two where the
  singer breathes longest (a comma counts as a little more breath), again
  and again until every part fits.

`split_words_into_lines` serves the speech-recognition fallback.
`split_long_lines` does the same to lyrics already stored with word timing,
for the lines that are too long, and is what the "Long lyric lines" job runs.
A transcript's lines are cut past MAX_LINE_WORDS, as a new one would be; a
written LRC's only past WRITTEN_LINE_MAX_WORDS.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Mapping, Optional, Sequence, TypedDict

from app.services.lyrics_analysis import LRC_LINE_PATTERN, parse_lrc_lines
from app.services.lyrics_line_fixes import line_key

logger = logging.getLogger(__name__)

# A gap between two words longer than this starts a new line, in seconds.
PAUSE_BREAK_SECONDS = 1.25
# A line with more words than this is cut in two.
MAX_LINE_WORDS = 12
# Stored lyrics a person wrote (an LRC from a lyrics site) are only cut where
# a line has more words than this: rap verses often run past MAX_LINE_WORDS on
# purpose, but no one writes a line this long.
WRITTEN_LINE_MAX_WORDS = 20
# Neither part of a cut line is shorter than this.
MIN_PART_WORDS = 3
# A comma (or ; or :) before a gap counts as this much more gap, in seconds.
_CLAUSE_BONUS_SECONDS = 0.3
# Between equal gaps, the cut nearer the middle wins by up to this, in seconds.
_MIDDLE_BONUS_SECONDS = 0.05

_SENTENCE_END = (".", "?", "!")
_CLAUSE_END = (",", ";", ":")
# Closing quotes and brackets after the punctuation that ends a word.
_TRAILING_CLOSERS = "\"'”’)]"


def _ending(word: Mapping[str, Any]) -> str:
    return str(word.get("word", "")).rstrip(_TRAILING_CLOSERS)


def _gap(before: Mapping[str, Any], after: Mapping[str, Any]) -> float:
    return float(after["start"]) - float(before["end"])


def _cut_long_line(words: Sequence[Mapping[str, Any]]) -> list[list[Any]]:
    """Cut a line into parts of at most MAX_LINE_WORDS, each at the longest breath."""
    if len(words) <= MAX_LINE_WORDS:
        return [list(words)]

    middle = len(words) / 2

    def score(cut: int) -> float:
        before = words[cut - 1]
        value = _gap(before, words[cut])
        if _ending(before).endswith(_CLAUSE_END):
            value += _CLAUSE_BONUS_SECONDS
        return value - _MIDDLE_BONUS_SECONDS * abs(cut - middle) / middle

    cut = max(range(MIN_PART_WORDS, len(words) - MIN_PART_WORDS + 1), key=score)
    return _cut_long_line(words[:cut]) + _cut_long_line(words[cut:])


def split_words_into_lines(words: Sequence[Mapping[str, Any]]) -> list[list[Any]]:
    """The words, in order, grouped into lines.

    Each word needs "word", "start" and "end". The words themselves are
    returned unchanged, so callers keep whatever else they carry.
    """
    lines: list[list[Any]] = []
    current: list[Any] = []
    for word in words:
        if current and (
            _gap(current[-1], word) > PAUSE_BREAK_SECONDS
            or _ending(current[-1]).endswith(_SENTENCE_END)
        ):
            lines.append(current)
            current = []
        current.append(word)
    if current:
        lines.append(current)
    return [part for line in lines for part in _cut_long_line(line)]


def format_lrc_timestamp(seconds: float) -> str:
    total_centiseconds = max(0, int(round(seconds * 100)))
    minutes, centiseconds = divmod(total_centiseconds, 6000)
    secs, centis = divmod(centiseconds, 100)
    return f"[{minutes:02d}:{secs:02d}.{centis:02d}]"


# ---------------------------------------------------------------------------
# Stored lyrics
# ---------------------------------------------------------------------------


class SplitLyrics(TypedDict):
    synced_lyrics: str
    # None when the plain lyrics aren't the synced lines' text, so stay as they are.
    plain_lyrics: Optional[str]
    word_payload: dict[str, Any]
    lines_split: int


def _line_parts(
    text: str, line_words: Sequence[Mapping[str, Any]], too_long: int
) -> Optional[list[tuple[list[str], list[Mapping[str, Any]]]]]:
    """The line cut where its words split, as (text tokens, words) per part,
    or None when it stays whole.

    A line is only cut when its stored words are its text, word for word:
    the cut is made in the text, at the places the timing chose.
    """
    tokens = text.split()
    if len(tokens) <= too_long or len(line_words) != len(tokens):
        return None
    if any(
        line_key(str(word.get("word", ""))) != line_key(token)
        for word, token in zip(line_words, tokens)
    ):
        return None
    parts = split_words_into_lines(line_words)
    if len(parts) < 2:
        return None
    result: list[tuple[list[str], list[Mapping[str, Any]]]] = []
    taken = 0
    for part in parts:
        result.append((tokens[taken : taken + len(part)], part))
        taken += len(part)
    return result


def _seconds(match: re.Match[str]) -> float:
    fraction = match.group(3) or "0"
    return (
        int(match.group(1)) * 60
        + int(match.group(2))
        + int(fraction) / (1000 if len(fraction) == 3 else 100)
    )


def _sung_lines(content: str) -> list[str]:
    return [line_key(line) for line in content.splitlines() if line_key(line)]


# How a transcript's word payload names its source, as stored (json.dumps).
TRANSCRIPT_SOURCE_MARK = '"lyrics_source": "asr:'


def is_transcript(word_payload: Optional[Mapping[str, Any]]) -> bool:
    """Whether the lyrics came from speech recognition, not from a person."""
    source = str((word_payload or {}).get("lyrics_source") or "")
    return source.startswith("asr:")


def _too_long(transcript: bool) -> int:
    """How many words make a stored line too long to be one line."""
    return MAX_LINE_WORDS if transcript else WRITTEN_LINE_MAX_WORDS


def long_line_count(synced_lyrics: Optional[str], *, transcript: bool) -> int:
    """How many of the stored lines are too long to be one line."""
    if not synced_lyrics:
        return 0
    too_long = _too_long(transcript)
    return sum(
        1
        for line in parse_lrc_lines(synced_lyrics)
        if len(line["text"].split()) > too_long
    )


def split_long_lines(
    synced_lyrics: str,
    word_payload: Mapping[str, Any],
    plain_lyrics: Optional[str] = None,
) -> Optional[SplitLyrics]:
    """The stored lyrics with each too-long line cut into lines, or None if none is.

    Lines that fit and tag lines are kept exactly. A cut line's first part
    keeps its timestamp; each later part starts when its first word does. A
    blank line after a cut line that was timed before the line's words end
    moves to when they do. Word line numbers move with the lines. Plain lyrics that are
    the synced lines' text (as the speech-recognition fallback stores them)
    are rebuilt from the new lines.
    """
    too_long = _too_long(is_transcript(word_payload))
    words = list(word_payload.get("words") or [])
    by_line: dict[int, list[Mapping[str, Any]]] = {}
    for word in words:
        by_line.setdefault(int(word["line_index"]), []).append(word)

    out_lines: list[str] = []
    renumbered: list[dict[str, Any]] = []
    old_index = 0
    next_index = 0
    lines_split = 0
    # When the last cut line's words end, until a sung line follows it.
    cut_line_end: Optional[float] = None
    for raw_line in synced_lyrics.strip().splitlines():
        match = LRC_LINE_PATTERN.match(raw_line.strip())
        if not match:
            out_lines.append(raw_line)
            continue
        line_words = by_line.pop(old_index, [])
        old_index += 1
        text = match.group(4).strip()
        if not text and cut_line_end is not None and _seconds(match) < cut_line_end:
            # A break timed inside the long line clears the screen while its
            # later parts are sung: it moves to when the line's words end.
            raw_line = format_lrc_timestamp(cut_line_end)
        parts = _line_parts(text, line_words, too_long) if text else None
        if text:
            cut_line_end = None
        if parts is None:
            out_lines.append(raw_line)
            renumbered.extend({**word, "line_index": next_index} for word in line_words)
            next_index += 1
            continue
        lines_split += 1
        stamp = raw_line.strip()[: match.start(4)].rstrip()
        for part_number, (part_tokens, part_words) in enumerate(parts):
            line_stamp = (
                stamp
                if part_number == 0
                else format_lrc_timestamp(float(part_words[0]["start"]))
            )
            out_lines.append(f"{line_stamp}{' '.join(part_tokens)}")
            renumbered.extend({**word, "line_index": next_index} for word in part_words)
            next_index += 1
        cut_line_end = float(parts[-1][1][-1]["end"])

    # Words on a line the text doesn't have: the timing isn't this text's, so
    # there's no telling where the lines would fall. Leave the song alone.
    if lines_split == 0 or by_line:
        return None

    new_synced = "\n".join(out_lines)
    new_plain: Optional[str] = None
    if plain_lyrics and _sung_lines(plain_lyrics) == _sung_lines(
        "\n".join(line["text"] for line in parse_lrc_lines(synced_lyrics))
    ):
        new_plain = "\n".join(
            line["text"] for line in parse_lrc_lines(new_synced) if line["text"]
        )

    payload = {**word_payload, "words": renumbered}
    if "line_count" in payload:
        payload["line_count"] = sum(
            1 for line in parse_lrc_lines(new_synced) if line["text"].strip()
        )
    return {
        "synced_lyrics": new_synced,
        "plain_lyrics": new_plain,
        "word_payload": payload,
        "lines_split": lines_split,
    }
