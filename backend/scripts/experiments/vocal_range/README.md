# Vocal range benchmark

Measures how well a vocal range method finds the lowest and highest note a lead
sings, so changes to the method can be shown to be better. The plan is
`docs/plans/2026-11-09-vocal-range.md`.

Run everything from `backend/` with the venv active. Nothing here writes to the
database or the library.

```bash
B=scripts/experiments/vocal_range
python $B/build_testset.py           # once; freezes results/testset.json
python $B/extract.py --jobs 10       # pyin contour per song; resumable
python $B/verify_baseline.py         # harness baseline == production child
python $B/score.py                   # results/runs/<method>.json + results/report.md
```

`results/` is gitignored. `reference.json` is committed.

## Test set

The plan's nine named test songs, plus 12 songs from each of four buckets of the
range the app stores today: narrow (≤ 10 semitones), typical, wide (≥ 24) and
not measured. At most one song per artist. Each song carries its singing-map
lead intervals and its synced-lyrics line times (no lyric text), so methods can
gate on "lead singing" or "a line on screen".

## Contours

`extract.py` runs a pitch tracker once per song per setting and caches the
result in `results/contours/<setting>/<song_id>.npz` (frame times, f0,
voiced flag, voiced probability). Methods read the cache, so trying a new rule
costs seconds, not a pyin run. The `pyin` setting is exactly what
`app/services/vocal_range_child.py` runs; `verify_baseline.py` checks that the
`baseline` method gives the child's answer.

## Methods

`methods.py` registers each method with the contour setting it reads. A method
returns the two notes, the moments that set each end (start and length of the
longest runs at that note, for the ear-check page) and an optional label
("rapped", ...) when a song has no sung range.

## Reference set and scoring

`reference.json` holds published sheet-music ranges (original key) and song
kinds (rapped, mixed, instrumental). Sheet music can't settle octaves: male
vocals are usually written an octave above how they sound, and listings mix
conventions (Glycerine: Musicnotes C4–F5, Singing Carrots C3–F4). Arrangements
of one song also disagree. So `score.py`:

- scores each end **modulo the octave** (−6..+5 semitones),
- scores the **width** as-is: an end an octave out shows as a width about 12 off,
- counts rapped and instrumental songs given no sung range,
- reports sanity numbers that need no reference: width spread, widths ≥ 30,
  tops at C6 or above.

Whether an end is in the right octave is decided by ear on the ear-check page.
