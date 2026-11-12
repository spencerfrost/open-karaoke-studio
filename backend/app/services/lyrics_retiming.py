"""Time a lyrics text from an ASR transcript of the vocals.

A lyrics text has the right words but no times (plain lyrics) or wrong ones
(synced lyrics that fail alignment). ASR hears roughly when things are sung,
but mishears words and sometimes squeezes a whole verse into a few seconds.
So the transcript is only trusted where it clearly heard a line: those lines
cut the song into chunks, and forced alignment places every line within its
chunk. The aligned lines' first words give the LRC timestamps.

    plan_retiming   text + ASR words  -> chunks of lines over stretches of audio
    (align_line_chunks in lyrics_alignment does the forced alignment)
    lrc_from_aligned_lines  lines + aligned words -> LRC
"""

import hashlib
import re
from typing import Any, Literal, Sequence, TypedDict

from app.services.lyrics_alignment import AlignedWord, LineChunk
from app.services.lyrics_analysis import parse_lrc_lines

# A line cuts the song into chunks only when ASR heard at least this many of
# its words, each with at least this confidence. A lone "the" can pair with the
# wrong place, and low-confidence ASR words are where its timing goes wrong.
ANCHOR_MIN_WORDS = 2
ANCHOR_MIN_SCORE = 0.5
# Roughly how long one sung word takes, for backing a chunk's start up to the
# line's first word when ASR didn't hear that word.
WORD_SECONDS = 0.35
# Chunks reach this far past their estimated edges, so a line sung a little
# early or late still falls inside its chunk.
CHUNK_SLACK_SECONDS = 1.0
# LRC lines start this much before their first aligned word.
LEAD_IN_SECONDS = 0.25
# Two lines never share a start time.
MIN_LINE_GAP_SECONDS = 0.1
# The last chunk runs this long past the last word ASR heard.
_TAIL_SECONDS = 10.0

_SECTION_HEADER_RE = re.compile(r"^\s*\[[^\]]*\]\s*$")
_NON_WORD_RE = re.compile(r"[^\w\s]")


class RetimingPlan(TypedDict):
    chunks: list[LineChunk]
    # Share of the text's words that matched a timed ASR word.
    match_ratio: float
    line_count: int
    anchor_count: int


def lyrics_text_lines(
    content: str, source_type: Literal["plain", "synced"]
) -> list[str]:
    """The sung lines of a lyrics text, without timestamps, blanks or [Chorus]-style headers."""
    if source_type == "synced":
        texts = [line["text"] for line in parse_lrc_lines(content)]
    else:
        texts = content.splitlines()
    return [
        text.strip()
        for text in texts
        if _tokens(text) and not _SECTION_HEADER_RE.match(text)
    ]


def lyrics_words_key(
    content: str, source_type: Literal["plain", "synced"]
) -> str | None:
    """A key for a lyrics text's words: the same for the same words in order.

    Timestamps, punctuation, case, blank lines and [Chorus]-style headers don't
    change it, so a plain and a synced copy of the same lyrics share a key.
    None when the text has no words.
    """
    words = [
        token
        for line in lyrics_text_lines(content, source_type)
        for token in _tokens(line)
    ]
    if not words:
        return None
    return hashlib.sha256(" ".join(words).encode()).hexdigest()[:32]


def shown_lyrics_key(synced_lyrics: str | None, plain_lyrics: str | None) -> str | None:
    """The words key of the lyrics on screen: synced when there are any, else plain."""
    if synced_lyrics and synced_lyrics.strip():
        return lyrics_words_key(synced_lyrics, "synced")
    if plain_lyrics and plain_lyrics.strip():
        return lyrics_words_key(plain_lyrics, "plain")
    return None


def _tokens(text: str) -> list[str]:
    """Words compared between the text and the transcript: lowercase, no punctuation."""
    return _NON_WORD_RE.sub("", text.lower().replace("’", "'")).split()


def _format_timestamp(seconds: float) -> str:
    centiseconds = max(0, int(round(seconds * 100)))
    minutes, centiseconds = divmod(centiseconds, 6000)
    secs, hundredths = divmod(centiseconds, 100)
    return f"[{minutes:02d}:{secs:02d}.{hundredths:02d}]"


def plan_retiming(
    lines: Sequence[str], asr_words: Sequence[dict[str, Any]]
) -> RetimingPlan | None:
    """Cut `lines` into chunks at the lines ASR clearly heard, with their times.

    Returns None when no line was clearly heard. The caller decides from
    `match_ratio` whether the text and the recording are the same song.
    """
    text_tokens: list[str] = []
    token_lines: list[int] = []
    line_first_token: list[int] = []
    for line_index, line in enumerate(lines):
        line_first_token.append(len(text_tokens))
        for token in _tokens(line):
            text_tokens.append(token)
            token_lines.append(line_index)

    asr_tokens: list[str] = []
    asr_starts: list[float] = []
    asr_scores: list[float] = []
    for word in asr_words:
        for token in _tokens(str(word.get("word", ""))):
            asr_tokens.append(token)
            asr_starts.append(float(word["start"]))
            asr_scores.append(float(word.get("score") or 0.0))

    if not text_tokens or not asr_tokens:
        return None

    # Words the ASR left untimed (score 0) still pair up, so that the words
    # around them pair correctly, but count as unheard.
    pairs = [
        (text_index, asr_index)
        for text_index, asr_index in _longest_common_subsequence(
            text_tokens, asr_tokens
        )
        if asr_scores[asr_index] > 0.0
    ]

    heard: list[list[tuple[int, int]]] = [[] for _ in lines]
    for text_index, asr_index in pairs:
        if asr_scores[asr_index] >= ANCHOR_MIN_SCORE:
            heard[token_lines[text_index]].append((text_index, asr_index))

    word_counts = [len(_tokens(line)) for line in lines]
    anchors = [
        index
        for index in range(len(lines))
        if heard[index]
        and len(heard[index]) >= min(ANCHOR_MIN_WORDS, word_counts[index])
    ]
    if not anchors:
        return None

    # Where each anchor line starts: its first clearly heard word, backed up by
    # the words before it in the line.
    anchor_starts = {
        index: max(
            asr_starts[heard[index][0][1]]
            - (heard[index][0][0] - line_first_token[index]) * WORD_SECONDS,
            0.0,
        )
        for index in anchors
    }

    # A chunk runs from one anchor to the next. Lines before the first anchor
    # go in a chunk from the start of the song.
    chunk_firsts = anchors if anchors[0] == 0 else [0, *anchors]
    chunks: list[LineChunk] = []
    for position, first_line in enumerate(chunk_firsts):
        last_line = (
            chunk_firsts[position + 1] - 1
            if position + 1 < len(chunk_firsts)
            else len(lines) - 1
        )
        start = anchor_starts.get(first_line, 0.0)
        end = (
            anchor_starts[chunk_firsts[position + 1]]
            if position + 1 < len(chunk_firsts)
            else max(asr_starts[-1], start) + _TAIL_SECONDS
        )
        chunks.append(
            LineChunk(
                first_line=first_line,
                last_line=last_line,
                start=round(max(start - CHUNK_SLACK_SECONDS, 0.0), 3),
                end=round(end + CHUNK_SLACK_SECONDS, 3),
            )
        )

    return RetimingPlan(
        chunks=chunks,
        match_ratio=round(len(pairs) / len(text_tokens), 3),
        line_count=len(lines),
        anchor_count=len(anchors),
    )


def _longest_common_subsequence(
    a: Sequence[str], b: Sequence[str]
) -> list[tuple[int, int]]:
    """Index pairs of the most words `a` and `b` share in order.

    Unlike difflib, which takes the longest identical run first, this finds the
    best overall pairing, so a repeated chorus pairs with its own repetition.
    """
    rows = len(a)
    cols = len(b)
    # lengths[i][j]: LCS length of a[i:] and b[j:].
    lengths = [[0] * (cols + 1) for _ in range(rows + 1)]
    for i in range(rows - 1, -1, -1):
        row, below = lengths[i], lengths[i + 1]
        token = a[i]
        for j in range(cols - 1, -1, -1):
            if token == b[j]:
                row[j] = below[j + 1] + 1
            else:
                row[j] = below[j] if below[j] >= row[j + 1] else row[j + 1]

    pairs: list[tuple[int, int]] = []
    i = j = 0
    while i < rows and j < cols:
        if a[i] == b[j]:
            pairs.append((i, j))
            i += 1
            j += 1
        elif lengths[i + 1][j] >= lengths[i][j + 1]:
            i += 1
        else:
            j += 1
    return pairs


def lrc_from_aligned_lines(
    lines: Sequence[str], words: Sequence[AlignedWord]
) -> str | None:
    """An LRC of `lines`, each starting just before its first aligned word.

    A line none of whose words were aligned starts right after the line
    before it. Returns None when no word was aligned.
    """
    first_word_starts: dict[int, float] = {}
    last_word_ends: dict[int, float] = {}
    for word in words:
        first_word_starts.setdefault(word["line_index"], word["start"])
        last_word_ends[word["line_index"]] = word["end"]
    if not first_word_starts:
        return None

    lrc_lines: list[str] = []
    previous_start: float | None = None
    previous_end: float | None = None
    for index, line in enumerate(lines):
        if index in first_word_starts:
            start = first_word_starts[index] - LEAD_IN_SECONDS
            if previous_end is not None:
                start = max(start, previous_end)
        elif previous_end is not None:
            start = previous_end
        else:
            start = min(first_word_starts.values()) - LEAD_IN_SECONDS
        if previous_start is not None:
            start = max(start, previous_start + MIN_LINE_GAP_SECONDS)
        start = max(start, 0.0)
        lrc_lines.append(f"{_format_timestamp(start)}{line}")
        previous_start = start
        previous_end = last_word_ends.get(index, start)
    return "\n".join(lrc_lines)
