# Lyrics alignment — fix `line_index`, unify instrumental detection

Standalone. Independent of the [stage/session/rotation chain](2026-08-29-sequencing.md).
Backend work touches Celery's import path, so the worker needs a restart before results change.

## Context

The trigger was a visible bug: during the instrumental break in *Hold On* (Wilson Phillips),
the progress bar rendered **after** "You could sustain (You could sustain)" instead of before
it. Chasing it turned up a data defect that affects a fifth of the aligned library.

### Already shipped (frontend, this session)

Two frontend fixes landed and the reported bug is gone. Both are compensations for bad
backend data — they are worth keeping regardless, but they are not the cure.

| Fix | File |
|---|---|
| Aligned word timings are authoritative; the LRC timestamp is only the fallback for lines alignment did not cover. Was blending the two with `min`/`max`, which lit lines up mid-break | [activeLineTiming.ts:3-40](../../frontend/src/features/lyrics/components/activeLineTiming.ts#L3-L40) |
| Blank LRC lines are spacers and can never own words. Timestamp grouping used to hand a line's words to the blank spacer after it, which then anchored the progress bar one slot too late | [lrcParser.ts:250-283](../../frontend/src/utils/lrcParser.ts#L250-L283) |

Measured on *Hold On*, before → after: blank lines holding words **4 → 0**; content lines
with no words **2 → 0** (all 57 now aligned); instrumental intervals resolving to a blank
line **2 of 2 → 0 of 2**. The intro bar was misplaced too.

### The root cause

All four alignment entry points assume `whisperx.align()` returns one output segment per
input line:

```python
for seg_idx, seg in enumerate(result.get("segments", [])):
    orig_line_idx = line_index_map.get(seg_idx, seg_idx)
```

It does not. WhisperX splits each input segment into **sentences** and appends them all
(`whisperx/alignment.py:377-410` in the venv), then merges subsegments sharing a
`(start, end)` via `groupby`. One split anywhere poisons
every line index after it, cumulatively. Extra keys on input segments are dropped, so
tagging segments with their line index and reading it back is not an option.

`_build_line_index_map` ([lyrics_alignment.py:141](../../backend/app/services/lyrics_alignment.py#L141))
maps *content-line index* → *source-line index*. It is being fed a **segment position**.

Traced on *Hold On* — WhisperX split `"...(These chains)"` into two segments at seg 2, and
nothing after it recovers:

```
seg#  assigned_li   words                                  expected content text
   1            2   'Why do you lock yourself up in the'   'Why do you lock yourself up in the'
   2            3   '(These chains)'                       'No one can change your life except'   <-- split
   3            4   'No one can change your life except'   "Don't ever let anyone step all ove"
   4            5   "Don't ever let anyone step all ove"   'Just open your heart and your mind'
```

By the break, alignment `line_index=22` names LRC source line 18. The interval's
`next_line_index: 22` therefore pointed at "You got yourself into your own mess", four lines
past the truth.

### Blast radius (measured across the whole library, 2026-08-30)

| | |
|---|---|
| Songs with stored alignment | 566 |
| …with drifted `line_index` | **107 (19%)** |
| Lines carrying a wrong index | 4,025 of 25,986 (**15%**) |
| Stored instrumental intervals | 497 |
| …naming the wrong LRC line | **43 (9%)**, across 22 songs |
| …pointing at a blank LRC line | 10 |

Affected songs include *Hold On*, *Kiss Off*, *Get Over It*, *Play That Funky Music*,
*Oh Mama*, *Feline*, *No Problem*.

### Why the frontend can't be the whole answer

`attachWordTimestamps` and `getInstrumentalTargetLineIndex` already distrust `line_index` and
lead with time-based matching — that is why 91% of intervals still land correctly. But the
fallbacks exist only to paper over this defect, and each new failure mode has produced
another heuristic. This is the "different issue every time I turn around" pattern; it stops
when the data is right.

## The fix: re-associate by token position

Forced alignment aligns **known** text, so the output word sequence is a positional 1:1 match
with the input tokens. Verified on *Hold On*: **444 input tokens, 444 output words, 444/444
exact positional match, zero divergences.** That makes the mapping deterministic — no
heuristics, no text fuzzy-matching, no per-segment `align()` calls.

Walk the flattened output words alongside the flattened input words (each tagged with its
source-line index) and assign as you go.

## Settled decisions

| Decision | Choice |
|---|---|
| Re-association strategy | Token-position walk. Rejected: per-line `align()` calls (far slower), text matching (strictly weaker) |
| Mismatch handling | Assert token equality while walking; on divergence log and fall back to today's behaviour rather than storing worse data |
| Intro vs mid-song | **One rule.** An intro is a gap before line 0, not a special case |
| Existing 566 songs | Re-align in a backfill; do not leave two data generations in the DB |
| Frontend heuristics | Keep. LRC timestamps are independently unreliable (*Hold On*'s were ~5s off), so time-first matching stays correct |

## 1 · One `line_index` assignment, not four

`backend/app/services/lyrics_alignment.py`

Add a single helper and route every path through it:

```python
def _assign_line_indices(
    result_segments: list[dict],
    input_tokens: list[tuple[int, str]],   # (source_line_index, word)
) -> list[AlignedWord]
```

It flattens `seg["words"]` in order, pairs each with `input_tokens[k]`, and takes the line
index from the input side. Compare the token strings as it walks; on the first mismatch, log
a warning with the position and both tokens, and fall back to the current positional-segment
behaviour for that song so a regression cannot silently store worse data than today.

Replace all four duplicated sites:

- `align_lyrics_to_vocals` — [:365-379](../../backend/app/services/lyrics_alignment.py#L365-L379)
- `align_plain_lyrics_to_vocals` — [:620-632](../../backend/app/services/lyrics_alignment.py#L620-L632) (uses raw `seg_idx`, no map at all)
- `align_lyrics_to_vocals_with_model` — [:736-749](../../backend/app/services/lyrics_alignment.py#L736-L749)
- `align_plain_lyrics_to_vocals_with_model` — [:805-817](../../backend/app/services/lyrics_alignment.py#L805-L817) (same)

The LRC paths pass source-line indices; the plain-text paths pass the indices
`_plain_lines_to_segments` ([:497](../../backend/app/services/lyrics_alignment.py#L497)) kept
after stripping blanks and `[Chorus]`-style headers. `_build_line_index_map` becomes
unnecessary for the LRC paths — the token list already carries source indices.

## 2 · Drop the double remap in `synced_stripped_plain`

[align_synced_lyrics_to_vocals:440-467](../../backend/app/services/lyrics_alignment.py#L440-L467)
remaps words *and* intervals through `line_index_map` on top of indices
`align_plain_lyrics_to_vocals` already assigned from `seg_idx` — compounding the error. Once
unit 1 lands, the inner call returns correct source-line indices and this whole remap block
deletes.

## 3 · One instrumental rule, no intro special case

[`_build_instrumental_intervals`:173-239](../../backend/app/services/lyrics_alignment.py#L173-L239)
runs the intro through a separate pre-loop block at a **2.5s** threshold while every other gap
needs **8s** ([:29-31](../../backend/app/services/lyrics_alignment.py#L29-L31)). A 3-second gap
at the top of a song is flagged; the identical gap between verses is not.

Collapse to one loop by seeding it with a virtual word ending at `0.0`, so the intro is just
the gap before the first word. Delete `_INSTR_INTRO_MIN_GAP_SECONDS` and the pre-loop block.

**Threshold needs a call.** Today's distribution across 497 stored intervals:

| | |
|---|---|
| Intro intervals | 222 |
| Mid-song intervals | 275 — min 8.0s, median 15.4s, max 167.5s |
| Intro intervals in the 2.5–8s band | **37** — median 6.0s |

Unifying at 8s drops those 37 short intros. Unifying lower re-admits mid-song false positives
from ad-libs and missed low-register words, which is what the 8s figure was defending against.
The mid-song median of 15.4s suggests real breaks sit well clear of 8s, so a unified threshold
somewhere in **5–6s** would keep most short intros without reaching far into ad-lib territory —
but this is a judgement call on feel, worth eyeballing against a few songs before committing.

## 4 · Backfill the 566 aligned songs

Re-running alignment is GPU work. Existing precedent for this shape of job:
`backend/scripts/backfill_bpm_for_existing_songs.py`.

Two options — the second is strongly preferred:

- **Re-align from audio.** Correct for every path, but 566 songs of GPU time.
- **Recompute indices from stored data.** The stored `words` array is already in correct
  positional order (unit 1 changes *labels*, not timings), so the same token walk can run
  offline against the stored LRC without touching audio or the GPU. Re-derive
  `instrumental_intervals` from the relabelled words afterwards.

Take the offline path. Gate the script behind `--dry-run` reporting how many songs and lines
would change, and skip any song where the token walk diverges.

> Watch for the enrichment worker: it crashed once without auto-restart. Check
> `celery inspect ping` before concluding a dispatched job did nothing.

## 5 · Tests

`backend/tests/services/` — there is currently no unit coverage for `_build_instrumental_intervals`
or for line-index assignment.

- **Split-segment regression** — feed a fake `whisperx.align()` result where one input line
  came back as two subsegments; assert every word keeps its true source-line index. This is
  the *Hold On* `(These chains)` case and the acceptance test for the whole plan.
- Merged subsegments (the `groupby` path) keep correct indices.
- Blank LRC lines never receive words.
- Token-mismatch safety net logs and falls back rather than storing garbage.
- `_build_instrumental_intervals`: an intro gap and an identical mid-song gap of the same
  duration produce the same decision.
- Interval `next_line_index` always names a non-blank line whose first word starts at the
  interval's `end`.

Frontend regressions already committed: [lrcParser.test.ts:92](../../frontend/src/utils/lrcParser.test.ts#L92)
(blank spacer never takes words) and [activeLineTiming.test.ts:30](../../frontend/src/features/lyrics/components/activeLineTiming.test.ts#L30)
(no active line during a break). Both verified to fail without their fixes.

## Verification

```bash
cd backend && source venv/bin/activate
pytest tests/services/ -v
pytest                                    # full suite
```

**Celery does not hot-reload — ask for a worker restart before testing any re-alignment.**

Re-run the library audit that produced the blast-radius table and expect zeros:

```bash
curl -s http://0.0.0.0:5123/api/songs > /tmp/songs.json
# for each song: compare alignment line_index -> synced LRC source line text
# expect: 0 songs with drift, 0 intervals naming a wrong or blank line
```

Then in the app, on *Hold On* (`b8f9d4c4-4a4c-493b-a675-62ecab88dda6`), seek to ~76s: the
progress bar sits **above** "You could sustain (You could sustain)", fills across the break,
and no lyric line is highlighted until 86.5s. Spot-check *Kiss Off* and *Play That Funky
Music* from the affected list.

```bash
tmux capture-pane -t open-karaoke:0.2 -p | tail -30   # Celery
```

## Not in scope

The three-layer plain/synced/word-synced duplication in the lyrics system is real and
untouched here. This plan fixes the timing data those layers share; the layering itself is a
separate piece of work.
