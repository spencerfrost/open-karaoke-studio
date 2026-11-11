# Song versions benchmark

Measures ways of fitting album lyrics onto another version of a song (live, extended, edit,
remix), so the pipeline's version path is picked by measurement and then by ear. The plan is
`docs/plans/2026-11-10-song-versions.md`.

Run everything from `backend/` with the venv active. Nothing here writes to the database or
the library.

```bash
V=scripts/experiments/song_versions
python $V/build_testset.py            # once; freezes results/testset.json (reads the DB)
python $V/synth.py                    # adds synthetic versions with a known answer
python $V/transcribe.py               # GPU; cached per ASR model; resumable
python $V/transcribe.py --asr whisper-large-v3-turbo
python $V/run.py --list
python $V/run.py today retime-inorder line-match line-match+fill anchor-shift   # GPU
python $V/score.py                    # results/report.md + results/per_song.csv
```

`results/` is gitignored: the test set holds lyrics. Start with one song: every script takes
`--song <id>` (`build_testset.py` takes `--add <id>`).

## Test set

- **real**: other versions in the library. `pair` = same artist + title as another song,
  lengths more than 20 s apart; `untimed singing` = most lead singing (singing map) outside
  today's timed words, at most two per artist; `added` = `--add`. Album lyrics are the song's
  own synced lyrics, else its shortest pair's. No ground truth.
- **control**: songs from `../lyrics_benchmark`'s test set, already right today. Every method
  should leave them where they are.
- **synthetic**: controls cut into versions by `synth.py` (new intro, extra chorus, cut verse,
  long outro, intro + outro), with truth lines moved by the edit.

The language comes from the song's pair when they agree, then the song, then `en`; never
detected on the version. `--language <id>=<code>` overrides.

## Methods

`methods.py` registers each. A method only plans: which lines are shown and the stretch of
audio each is aligned in (`Plan`: today's stored timing, an LRC, or chunks of lines).
`run.py` force-aligns every plan the same way, with the app's aligners. A line's
`source` is `album` or `heard` (transcript words), and `album_index` says which album line it
is, so repeats can be counted.

Add a method with `@method(...)` in `methods.py`; `run.py <name>` runs it and `score.py` picks
it up.

## Scores

See `score.py`'s docstring. In short: how much singing has a line on screen (`covered`), how
much line time has no singing (`ghost`), how much is transcript text (`heard`), repeats, and the
singing left after the last line (`tail`); controls by how far lines moved from today;
synthetic songs by truth lines found within 0.5 s. A detection table checks candidate "this
is another version" rules against each kind.
