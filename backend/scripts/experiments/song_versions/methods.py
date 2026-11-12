"""
The ways of fitting album lyrics onto another version of a song.

A method only plans: from the album lines, the cached transcript and the
singing map it decides which lines are shown and the stretch of audio each is
aligned in. run.py does the forced alignment, the same way for every method.
See docs/plans/2026-11-10-song-versions.md for what each method is for.
"""

from __future__ import annotations

import math
from bisect import bisect_right
from dataclasses import dataclass
from statistics import median
from typing import Any, Callable, Optional

from common import (
    AlbumLine,
    Interval,
    Plan,
    PlanChunk,
    PlanLine,
    TestSong,
    album_lines,
    intersect,
    tokens,
    total,
)

from app.jobs.lyrics_tasks import MIN_RETIME_MATCH_RATIO  # noqa: E402
from app.services.lyrics_analysis import parse_lrc_lines  # noqa: E402
from app.services.lyrics_retiming import (  # noqa: E402
    ANCHOR_MIN_SCORE,
    CHUNK_SLACK_SECONDS,
    WORD_SECONDS,
    _format_timestamp,
    _longest_common_subsequence,
    plan_retiming,
)

# A heard word counts as clearly heard at or above this score (the re-timer's).
HEARD_MIN_SCORE = ANCHOR_MIN_SCORE
# A line matches a stretch of the transcript when this share of its words were
# clearly heard there, and at least 2 (all of them for a line of 1 or 2 words).
MATCH_MIN_SHARE = 0.6
# Album lines between two matched lines, in album order, are kept in the gap
# between them when there are at most this many.
BRIDGE_MAX_LINES = 4
# Unmatched transcript words become a heard line when at least this many were
# clearly heard and this share of their stretch has singing in the singing map.
FILL_MIN_WORDS = 3
FILL_MIN_SUNG_SHARE = 0.5
FILL_PAD_SECONDS = 0.3
# anchor-shift needs this many lines that occur once in the album lyrics.
SHIFT_MIN_ANCHORS = 3
# retime-inorder-anchors runs with at least this many clearly heard lines.
RETIME_MIN_ANCHORS = 10
# The shifted album part ends this long after its last line starts.
SPAN_TAIL_SECONDS = 10.0


@dataclass(frozen=True)
class Context:
    song: TestSong
    album: list[AlbumLine]
    transcript: Optional[dict[str, Any]]
    sung: list[Interval]


@dataclass(frozen=True)
class Method:
    name: str
    description: str
    uses_asr: bool
    ready: bool
    plan: Callable[[Context], Optional[Plan]]


METHODS: dict[str, Method] = {}


def method(name: str, description: str, *, uses_asr: bool = True, ready: bool = True):
    def register(fn: Callable[[Context], Optional[Plan]]):
        METHODS[name] = Method(name, description, uses_asr, ready, fn)
        return fn

    return register


# ---------------------------------------------------------------------------
# The transcript as a stream of tokens
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Heard:
    token: str
    start: float
    end: float
    score: float
    segment: int
    word_index: int


def heard_tokens(transcript: dict[str, Any]) -> list[Heard]:
    heard: list[Heard] = []
    for word_index, word in enumerate(transcript["words"]):
        for token in tokens(str(word.get("word", ""))):
            heard.append(
                Heard(
                    token=token,
                    start=float(word["start"]),
                    end=float(word["end"]),
                    score=float(word.get("score") or 0.0),
                    segment=int(word["line_index"]),
                    word_index=word_index,
                )
            )
    return heard


# ---------------------------------------------------------------------------
# Matching each album line on its own
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LineMatch:
    album_index: int
    # First and last paired transcript token, inclusive.
    first: int
    last: int
    clear: int
    # Album-line words before the first / after the last paired one.
    lead_missing: int
    tail_missing: int


def find_line_matches(album: list[AlbumLine], heard: list[Heard]) -> list[LineMatch]:
    """Every place in the transcript where an album line was clearly heard."""
    heard_words = [h.token for h in heard]
    found: dict[tuple[int, int, int], LineMatch] = {}
    for line in album:
        line_tokens = tokens(line["text"])
        n = len(line_tokens)
        if not n:
            continue
        need = n if n <= 2 else max(2, math.ceil(MATCH_MIN_SHARE * n))
        window = n + max(2, n // 2)
        vocabulary = set(line_tokens)
        for start in range(len(heard)):
            if heard_words[start] not in vocabulary:
                continue
            stretch = heard_words[start : start + window]
            pairs = _longest_common_subsequence(line_tokens, stretch)
            clear = [
                (i, j) for i, j in pairs if heard[start + j].score >= HEARD_MIN_SCORE
            ]
            if len(clear) < need:
                continue
            match = LineMatch(
                album_index=line["index"],
                first=start + pairs[0][1],
                last=start + pairs[-1][1],
                clear=len(clear),
                lead_missing=pairs[0][0],
                tail_missing=n - 1 - pairs[-1][0],
            )
            key = (match.album_index, match.first, match.last)
            if key not in found or found[key].clear < match.clear:
                found[key] = match
    return list(found.values())


def best_matches(matches: list[LineMatch]) -> list[LineMatch]:
    """The non-overlapping matches with the most clearly heard words, in time order.

    Weighted interval scheduling over transcript positions: an album line can
    win more than once (a repeat), in any order, or not at all.
    """
    ordered = sorted(matches, key=lambda m: m.last)
    ends = [m.last for m in ordered]
    best = [0.0] * (len(ordered) + 1)
    take = [False] * len(ordered)
    for k, match in enumerate(ordered):
        before = bisect_right(ends, match.first - 1, 0, k)
        # A whole line heard beats a part of it by a little, all else equal.
        weight = match.clear + 0.01 * (match.lead_missing == match.tail_missing == 0)
        with_it = best[before] + weight
        take[k] = with_it > best[k]
        best[k + 1] = max(best[k], with_it)
    chosen: list[LineMatch] = []
    k = len(ordered) - 1
    while k >= 0:
        if take[k]:
            chosen.append(ordered[k])
            k = bisect_right(ends, ordered[k].first - 1, 0, k) - 1
        else:
            k -= 1
    return sorted(chosen, key=lambda m: m.first)


def follow_album_order(
    album: list[AlbumLine], chosen: list[LineMatch]
) -> list[LineMatch]:
    """Matches relabelled so word-for-word identical album lines are used in order.

    Album lyrics repeat lines exactly ("Terrible lie" four times), and a match
    can't tell the copies apart. Each match takes the first copy after the
    previous match's line; only when none is left is it a repeat (the first copy).
    """
    copies: dict[str, list[int]] = {}
    for line in album:
        copies.setdefault(" ".join(tokens(line["text"])), []).append(line["index"])
    out: list[LineMatch] = []
    cursor = -1
    for match in chosen:
        same = copies[" ".join(tokens(album[match.album_index]["text"]))]
        later = [i for i in same if i > cursor]
        index = later[0] if later else same[0]
        out.append(
            LineMatch(
                album_index=index,
                first=match.first,
                last=match.last,
                clear=match.clear,
                lead_missing=match.lead_missing,
                tail_missing=match.tail_missing,
            )
        )
        cursor = index
    return out


@dataclass
class _Chunk:
    start: float
    end: float
    # The heard words that pin it, which neighbouring chunks may not cut into.
    core_start: float
    core_end: float
    lines: list[PlanLine]


def _album_line(line: AlbumLine) -> PlanLine:
    return PlanLine(text=line["text"], source="album", album_index=line["index"])


def _chunks_from_matches(
    album: list[AlbumLine], heard: list[Heard], chosen: list[LineMatch]
) -> list[_Chunk]:
    chunks: list[_Chunk] = []
    for position, match in enumerate(chosen):
        core_start, core_end = heard[match.first].start, heard[match.last].end
        chunks.append(
            _Chunk(
                start=core_start
                - match.lead_missing * WORD_SECONDS
                - CHUNK_SLACK_SECONDS,
                end=core_end + match.tail_missing * WORD_SECONDS + CHUNK_SLACK_SECONDS,
                core_start=core_start,
                core_end=core_end,
                lines=[_album_line(album[match.album_index])],
            )
        )
        # Lines ASR missed between two lines sung in album order.
        if position + 1 < len(chosen):
            following = chosen[position + 1]
            missing = range(match.album_index + 1, following.album_index)
            gap_start, gap_end = core_end, heard[following.first].start
            words = sum(len(tokens(album[i]["text"])) for i in missing)
            if (
                0 < len(missing) <= BRIDGE_MAX_LINES
                and gap_end - gap_start >= 0.5 * words * WORD_SECONDS
            ):
                chunks.append(
                    _Chunk(
                        start=gap_start,
                        end=gap_end,
                        core_start=gap_start,
                        core_end=gap_end,
                        lines=[_album_line(album[i]) for i in missing],
                    )
                )
    return chunks


def _fill_chunks(
    heard: list[Heard],
    transcript: dict[str, Any],
    chosen: list[LineMatch],
    taken: list[_Chunk],
    sung: list[Interval],
) -> list[_Chunk]:
    """Heard lines for clearly heard singing that matched no album line."""
    covered = set()
    for match in chosen:
        covered.update(range(match.first, match.last + 1))
    spans = [(c.core_start, c.core_end) for c in taken]

    def free(h: Heard) -> bool:
        return not any(a <= h.start < b for a, b in spans)

    # Runs of unmatched words, split at matched words and at Whisper's segments.
    groups: list[list[Heard]] = []
    current: list[Heard] = []
    for position, h in enumerate(heard):
        if position in covered or not free(h):
            if current:
                groups.append(current)
            current = []
            continue
        if current and current[-1].segment != h.segment:
            groups.append(current)
            current = []
        current.append(h)
    if current:
        groups.append(current)

    chunks: list[_Chunk] = []
    for group in groups:
        clear = [h for h in group if h.score >= HEARD_MIN_SCORE]
        if len(clear) < FILL_MIN_WORDS:
            continue
        start, end = group[0].start, group[-1].end
        if end <= start:
            continue
        if total(intersect([(start, end)], sung)) / (end - start) < FILL_MIN_SUNG_SHARE:
            continue
        word_indices = sorted({h.word_index for h in group})
        text = " ".join(str(transcript["words"][i]["word"]) for i in word_indices)
        chunks.append(
            _Chunk(
                start=start - FILL_PAD_SECONDS,
                end=end + FILL_PAD_SECONDS,
                core_start=start,
                core_end=end,
                lines=[PlanLine(text=text, source="heard", album_index=None)],
            )
        )
    return chunks


def _finish(chunks: list[_Chunk], notes: dict[str, Any]) -> Optional[Plan]:
    """Time-ordered chunks that don't cut into their neighbours' heard words."""
    if not chunks:
        return None
    chunks = sorted(chunks, key=lambda c: c.core_start)
    out: list[PlanChunk] = []
    for k, chunk in enumerate(chunks):
        start, end = chunk.start, chunk.end
        if k > 0:
            start = max(start, chunks[k - 1].core_end)
        if k + 1 < len(chunks):
            end = min(end, chunks[k + 1].core_start)
        start = max(start, 0.0)
        if end <= start:
            end = start + 0.1
        out.append(
            PlanChunk(start=round(start, 3), end=round(end, 3), lines=chunk.lines)
        )
    return Plan(chunks=out, notes=notes)


def _line_match_plan(ctx: Context, fill: bool) -> Optional[Plan]:
    assert ctx.transcript is not None
    heard = heard_tokens(ctx.transcript)
    if not heard or not ctx.album:
        return None
    matches = find_line_matches(ctx.album, heard)
    chosen = follow_album_order(ctx.album, best_matches(matches))
    chunks = _chunks_from_matches(ctx.album, heard, chosen)
    fills = (
        _fill_chunks(heard, ctx.transcript, chosen, chunks, ctx.sung) if fill else []
    )
    seen: set[int] = set()
    repeats = 0
    for match in chosen:
        repeats += match.album_index in seen
        seen.add(match.album_index)
    out_of_order = sum(
        b.album_index < a.album_index for a, b in zip(chosen, chosen[1:])
    )
    return _finish(
        chunks + fills,
        {
            "candidates": len(matches),
            "matched_lines": len(chosen),
            "distinct_album_lines": len(seen),
            "repeats": repeats,
            "jumps_back": out_of_order,
            "heard_lines": len(fills),
        },
    )


# ---------------------------------------------------------------------------
# The methods
# ---------------------------------------------------------------------------


@method(
    "today",
    "What the pipeline stored. Synthetic songs: the album LRC force-aligned as is.",
    uses_asr=False,
)
def plan_today(ctx: Context) -> Optional[Plan]:
    if ctx.song["today"] is not None:
        return Plan(stored=ctx.song["today"])
    return Plan(
        lrc=ctx.song["album_lrc"], lrc_lines=[_album_line(l) for l in ctx.album]
    )


@method(
    "lrc-as-is",
    "The lyrics LRC force-aligned exactly as written: a reference for lyrics "
    "whose times are already right (version lyrics, synthetic songs).",
    uses_asr=False,
)
def plan_lrc_as_is(ctx: Context) -> Optional[Plan]:
    return Plan(
        lrc=ctx.song["album_lrc"], lrc_lines=[_album_line(l) for l in ctx.album]
    )


@method(
    "anchor-shift",
    "The album LRC moved by one shift: the median of heard time minus LRC time "
    "over lines that occur once in the album lyrics.",
)
def plan_anchor_shift(ctx: Context) -> Optional[Plan]:
    shifted = _shifted_album(ctx)
    if shifted is None:
        return None
    lrc, notes = shifted
    return Plan(
        lrc=lrc, lrc_lines=[_album_line(l) for l in album_lines(lrc)], notes=notes
    )


@method(
    "anchor-shift+fill",
    "anchor-shift for the album lines, plus the transcript's words where there is "
    "singing before or after the shifted album lyrics (a live intro, an outro).",
)
def plan_anchor_shift_fill(ctx: Context) -> Optional[Plan]:
    assert ctx.transcript is not None
    shifted = _shifted_album(ctx)
    if shifted is None:
        return None
    lrc, notes = shifted
    lines = album_lines(lrc)
    # The album part: its first line to its last line's start plus a line's
    # length. Transcript words inside it never become lines.
    span_start = lines[0]["time"] - CHUNK_SLACK_SECONDS
    span_end = lines[-1]["time"] + SPAN_TAIL_SECONDS
    album_part = _Chunk(
        start=span_start,
        end=span_end,
        core_start=span_start,
        core_end=span_end,
        lines=[],
    )
    heard = heard_tokens(ctx.transcript)
    fills = _fill_chunks(heard, ctx.transcript, [], [album_part], ctx.sung)
    filled = _finish(fills, {})
    return Plan(
        lrc=lrc,
        lrc_lines=[_album_line(l) for l in lines],
        chunks=filled.get("chunks", []) if filled else [],
        notes={**notes, "heard_lines": len(fills)},
    )


def _shifted_album(ctx: Context) -> Optional[tuple[str, dict[str, Any]]]:
    """The album LRC moved by one shift, and how it was found; None without enough anchors.

    The shift is the median, over clearly heard lines that occur once in the
    album lyrics, of where the transcript heard the line minus its LRC time.
    """
    assert ctx.transcript is not None
    heard = heard_tokens(ctx.transcript)
    chosen = best_matches(find_line_matches(ctx.album, heard))
    counts: dict[str, int] = {}
    for line in ctx.album:
        key = " ".join(tokens(line["text"]))
        counts[key] = counts.get(key, 0) + 1
    offsets = [
        heard[m.first].start
        - m.lead_missing * WORD_SECONDS
        - ctx.album[m.album_index]["time"]
        for m in chosen
        if counts[" ".join(tokens(ctx.album[m.album_index]["text"]))] == 1
    ]
    if len(offsets) < SHIFT_MIN_ANCHORS:
        return None
    shift = median(offsets)
    lrc = "\n".join(
        f"{_format_timestamp(max(0.0, line['timestamp'] + shift))}{line['text']}"
        for line in parse_lrc_lines(ctx.song["album_lrc"])
    )
    return lrc, {"shift": round(shift, 2), "anchors": len(offsets)}


@method(
    "retime-inorder",
    "Today's re-timer: one in-order pairing of the album lines with the "
    "transcript, each run of lines aligned between two clearly heard ones.",
)
def plan_retime_inorder(ctx: Context) -> Optional[Plan]:
    return _retime_inorder(ctx, gate_on_ratio=True)


@method(
    "retime-inorder-anchors",
    "retime-inorder without the 50%-of-words gate: it runs when at least "
    f"{RETIME_MIN_ANCHORS} lines were clearly heard, however few words matched.",
)
def plan_retime_inorder_anchors(ctx: Context) -> Optional[Plan]:
    return _retime_inorder(ctx, gate_on_ratio=False)


def _retime_inorder(ctx: Context, gate_on_ratio: bool) -> Optional[Plan]:
    assert ctx.transcript is not None
    texts = [line["text"] for line in ctx.album]
    plan = plan_retiming(texts, ctx.transcript["words"])
    notes = {
        "match_ratio": plan["match_ratio"] if plan else 0.0,
        "anchors": plan["anchor_count"] if plan else 0,
    }
    if plan is None:
        return None
    # The app gives up below this ratio (retime_failed) and keeps what it had.
    if gate_on_ratio and plan["match_ratio"] < MIN_RETIME_MATCH_RATIO:
        return None
    if not gate_on_ratio and plan["anchor_count"] < RETIME_MIN_ANCHORS:
        return None
    return Plan(
        chunks=[
            PlanChunk(
                start=chunk["start"],
                end=chunk["end"],
                lines=[
                    _album_line(ctx.album[i])
                    for i in range(chunk["first_line"], chunk["last_line"] + 1)
                ],
            )
            for chunk in plan["chunks"]
        ],
        notes=notes,
    )


@method(
    "line-match",
    "Each album line matched to the transcript on its own (repeats, reorders and "
    "skips allowed); unmatched singing left blank.",
)
def plan_line_match(ctx: Context) -> Optional[Plan]:
    return _line_match_plan(ctx, fill=False)


@method(
    "line-match+fill",
    "line-match, plus the transcript's words where singing matched no album line.",
)
def plan_line_match_fill(ctx: Context) -> Optional[Plan]:
    return _line_match_plan(ctx, fill=True)


@method(
    "dp-jumps+fill",
    "One dynamic-programming pass over (album line, transcript position) that may "
    "jump back (a repeat) or skip ahead, plus heard text. Plan step 3.",
    ready=False,
)
def plan_dp_jumps_fill(ctx: Context) -> Optional[Plan]:
    # Score: clearly heard words paired, minus a cost per jump back and per
    # album line skipped, so the album's order wins unless the audio clearly
    # leaves it. Then fill as in line-match+fill.
    raise NotImplementedError


@method(
    "closest-lrc",
    "The provider LRC whose length is closest to the song's, aligned the usual "
    "way. Needs candidates cached in the test set. Plan step 3.",
    uses_asr=False,
    ready=False,
)
def plan_closest_lrc(ctx: Context) -> Optional[Plan]:
    raise NotImplementedError
