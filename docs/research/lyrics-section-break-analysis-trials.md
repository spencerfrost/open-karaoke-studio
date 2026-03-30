# Lyrics Section Break Analysis — Trials Log

Tracking what we've tried, what works, and what doesn't as we iterate on the section break detection system.

See [lyrics-analysis-system.md](../lyrics-analysis-system.md) for the full design document.

---

## Implementation

**Service**: `backend/app/services/lyrics_analysis.py`
**CLI**: `backend/scripts/analyze_section_breaks.py --song-id <id>`
**API**: `GET /api/lyrics/songs/{id}/analyze`

---

## Trial 1 — Text Repetition + Timing Gap Baseline

**Date**: 2026-03-30
**Commit**: (first implementation)

### Methods

- **Timing gap**: flags gaps > `median * 2.0`; confidence = `min(1.0, gap / (median * 4.0))`
- **Text repetition**: sliding window group sizes 2–6, `min_repetitions=2`; confidence = `min(1.0, (group_size / 4.0) * (repetition_count / 3.0))`
- **Fusion**: candidates at the same line index from different methods are merged with a +0.25 confidence boost

### Test song: "There's a Fire" — OK Go

Song structure: 3 verses, 3 chorus repeats, a hook ("There's a fire"), and an 8-line identical-line outro chant.

**Results**:

- 8 real section boundaries in the song
- 8/8 correctly detected ✅
- 18 false positives ❌
- `modified_lrc` unusable — too many spurious breaks

**What worked**:
- Timing gap: 3/3 correct, 0 false positives. Very reliable.
- Multi-method fusion: all 3 fused (timing+repetition) candidates were correct.
- Text repetition correctly identified all chorus boundaries.

**What didn't work**:

1. **Sub-group interior noise** — when a 4-line group is the real repeated unit, the algorithm also matches 3-line, 2-line sub-sequences within it, generating candidates at every *interior* line of the repeated block. Only the outermost boundary matters.

2. **Consecutive identical line runs** — "There's a fire, there's a fire" repeating 9 times is one outro section, but every adjacent pair matches as a "repeated 2-line group (9x)", flooding the output with candidates inside the run.

### Issues to Address

| Issue | Description | Priority |
|-------|-------------|----------|
| Sub-group suppression | When a larger repeated group is found, suppress interior boundaries that fall within it | High |
| Identical-line run detection | Detect runs of the same line and treat as a single section, not many candidates | High |
| `modified_lrc` confidence floor | 0.3 too low for current noise level; multi-method-only filter would be 3/3 with 0 FP for this song | Medium |

---

---

## Trial 2 — Sub-group Suppression + Identical-line Run Collapsing

**Date**: 2026-03-30
**Commit**: (current)

### Changes

**Fix 1 — Sub-group suppression**: Added `pos_max_interior_size` map in `analyze_text_repetition`. For each repeated span `[s, e]`, positions `s..e-1` are "interior." When generating a candidate at position `p`, it is suppressed if a strictly larger repeated group claims `p` as interior. This eliminates candidates placed inside a repeated block rather than at its edges.

**Fix 2 — Identical-line run collapsing**: Added `_group_consecutive_starts` helper. For a given repeated key, consecutive start indices (e.g. `[24, 25, 26, ..., 31]` from 9 identical adjacent lines) are collapsed into a single run `(first=24, last=31)`, emitting candidates only at the outermost boundaries (`p=23` and `p=32`). This replaces the O(n) interior candidates with exactly 2.

### Test song: "There's a Fire" — OK Go

**Results**:

- 8 real section boundaries in the song
- 8 candidates total (down from 26)
- 7 clearly correct ✅
- 1 ambiguous ⚠️ — no confirmed false positives ✅

**Candidate breakdown**:

| Line | Confidence | Methods | Assessment |
|------|-----------|---------|------------|
| 3  | 1.00 | text_repetition | ✅ Before chorus 1 |
| 7  | 1.00 | timing_gap+text_repetition | ✅ After chorus 1 |
| 11 | 1.00 | text_repetition | ✅ Before chorus 2 |
| 16 | 1.00 | timing_gap+text_repetition | ✅ Before "there's a fire" section |
| 20 | 1.00 | text_repetition | ✅ Before chorus 3 |
| 24 | 1.00 | text_repetition | ✅ Start of identical-line outro |
| 25 | 1.00 | timing_gap | ⚠️ 18.9s gap inside "there's a fire" run — may be a real large pause or FP |
| 34 | 1.00 | text_repetition | ✅ End of outro run |

**What worked**:
- All 18 false positives eliminated: interior sub-group noise gone, identical-line run noise gone.
- The `modified_lrc` is now usable — 7–8 breaks in the right places.
- Timing gap correctly detected the large pause inside the outro run (Line 25), which may be a genuine structural pause rather than a false positive.

**Remaining open questions**:
- Line 25: is an 18.9s gap mid-run a real section boundary or a long instrumental interlude within the outro? Needs manual verification against the actual audio.
- The song has an "existing break" (1 already in LRC) — we don't yet detect or avoid duplicating it.

### Issues to Address

| Issue | Description | Priority |
|-------|-------------|----------|
| Existing break duplication | Song already has 1 break in LRC; analysis doesn't check for it | Low |
| Mid-run timing gaps | Large timing gap inside an identical-line run (Line 25) may be real or noise; unclear | Low |

### Key Finding — Global LRC Offset

Investigating the Line 25 discrepancy (reported 18.9s gap vs. ~12s measured by ear) revealed a fundamental limitation: LRC timestamps mark when a line *starts displaying*, not when the previous line's vocals *end*. So every gap measurement includes the singing duration of the preceding line, not just the silence.

This led to a broader insight: LRC files from external sources are frequently off by a **global constant offset** — every timestamp wrong by the same amount. This is likely the most common alignment problem in the library and has a clean fix:

1. Use high-confidence section boundaries (already detected) as anchor points — these follow clear silences where vocal onsets are unambiguous
2. Load `vocals.mp3` with librosa, compute RMS energy, detect actual vocal onset at each anchor
3. Compute `offset = lrc_timestamp − rms_onset` per anchor, take the median
4. If anchors agree within tolerance, shift every timestamp in the file by that amount

The section break candidates we're already generating are exactly the anchor points needed for offset estimation — the two features compose naturally into a single analysis pass.

See [lyrics-analysis-system.md](../lyrics-analysis-system.md#lrc-timestamp-correction--global-offset-detection) for the full write-up.

---

*Add new trials below as we iterate.*
