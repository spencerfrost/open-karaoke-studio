"""
Repair aligned word timing where the singing map says nobody is singing.

The aligner can hold a word through an instrumental ("mine" held 2:47–3:06 in
A Perfect Circle "The Package", score 0.97) or place one inside it. A word's
score says the word is there at its start, not that it lasts as long as it's
timed for, so the map decides: a stretch with no sound on either the lead or
the backing stem is silence.

Three repairs, each a `WordChange`:

- `cut`: a word that starts in sound and runs 2 s or more into silence ends
  where the silence starts.
- `start_moved`: a word that starts with 2 s or more of silence and has
  sound later on starts where the sound does (and is also cut, if it then
  runs into another such silence).
- `moved`: a word with no sound at all, inside a silence of 2 s or more,
  moves to where singing starts again, keeping its length, as long as the
  next word starts after that. Words that share one silence are left where
  they are: moving them would pile them up, and a cluster like that more
  likely means the map missed quiet singing.

Nothing here reads or writes the database; `repair_words` works on a copy.
See docs/plans/2026-11-04-lyrics-from-all-the-evidence.md.
"""

from dataclasses import dataclass
from typing import Any, Literal, Optional

from app.services.singing_map import Interval, intersect, subtract, union

# Silence on both stems inside a word that makes it held. Same as
# HELD_SILENCE_SEC in scripts/experiments/crammed_lines.py, which counts them.
HELD_SILENCE_SECONDS = 2.0

ChangeKind = Literal["cut", "start_moved", "moved"]


@dataclass(frozen=True)
class WordChange:
    index: int
    kind: ChangeKind
    before: Interval
    after: Interval


def sound_of(singing_map: dict[str, Any]) -> list[Interval]:
    """Where either stem has sound."""
    lead = [(float(a), float(b)) for a, b in singing_map.get("lead") or []]
    backing = [(float(a), float(b)) for a, b in singing_map.get("backing") or []]
    return union(lead, backing)


def _long_silences(sound: list[Interval], start: float, end: float) -> list[Interval]:
    return [
        gap
        for gap in subtract([(start, end)], sound)
        if gap[1] - gap[0] >= HELD_SILENCE_SECONDS
    ]


def _silence_around(sound: list[Interval], word: Interval) -> Optional[Interval]:
    """The silence a soundless word sits in, if it's long enough to matter
    and singing starts again after it."""
    before = max((b for _, b in sound if b <= word[0]), default=0.0)
    after = min((a for a, _ in sound if a >= word[1]), default=None)
    if after is None or after - before < HELD_SILENCE_SECONDS:
        return None
    return (before, after)


def _repair_one(
    sound: list[Interval],
    word: Interval,
    prev_start: Optional[float],
    next_start: Optional[float],
) -> Optional[tuple[ChangeKind, Interval]]:
    start, end = word
    if end <= start:
        return None

    if not intersect([word], sound):
        silence = _silence_around(sound, word)
        if silence is None:
            return None
        resume = silence[1]
        if (prev_start is not None and prev_start >= silence[0]) or (
            next_start is not None and next_start < resume
        ):
            return None  # another word is in this silence too: a cluster
        length = end - start
        new_end = resume + length
        if next_start is not None:
            new_end = min(new_end, next_start)
        if new_end <= resume:
            return None  # the next word starts right where singing resumes
        return "moved", (resume, new_end)

    silences = _long_silences(sound, start, end)
    if not silences:
        return None
    kind: ChangeKind = "cut"
    if silences[0][0] <= start:
        kind = "start_moved"
        start = silences[0][1]
        silences = silences[1:]
    if silences:
        end = silences[0][0]
    return kind, (start, end)


def repair_words(
    words: list[dict[str, Any]], singing_map: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[WordChange]]:
    """Repaired copies of `words` (same shape, same order) and what changed.

    Neighbours are judged from the aligner's timing, not from repairs made
    earlier in the list, so the result doesn't depend on the order repairs
    are made in.
    """
    sound = sound_of(singing_map)
    repaired = [dict(word) for word in words]
    changes: list[WordChange] = []
    if not sound:
        return repaired, changes  # no vocals measured: nothing to judge by

    for index, word in enumerate(words):
        before = (float(word["start"]), float(word["end"]))
        prev_start = float(words[index - 1]["start"]) if index > 0 else None
        next_start = (
            float(words[index + 1]["start"]) if index + 1 < len(words) else None
        )
        result = _repair_one(sound, before, prev_start, next_start)
        if result is None:
            continue
        kind, after = result
        after = (round(after[0], 3), round(after[1], 3))
        repaired[index]["start"], repaired[index]["end"] = after
        changes.append(WordChange(index, kind, before, after))
    return repaired, changes
