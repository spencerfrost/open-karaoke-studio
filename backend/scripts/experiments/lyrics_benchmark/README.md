# Lyrics model benchmark

Measures how well transcription (ASR) and forced-alignment models handle this
library's separated vocals, scored against the library's own synced lyrics.
It is the baseline for deciding whether to swap models or fine-tune one.

Run everything from `backend/` with the venv active. Nothing here writes to the
database or the library.

```bash
B=scripts/experiments/lyrics_benchmark
python $B/build_testset.py --size 80      # once; freezes results/testset.json
python $B/run_models.py --list
python $B/run_models.py whisper-large-v3  # one model per process; resumable
python $B/score.py                        # results/report.md + per_song_*.csv
```

`results/` is gitignored because the test set contains lyrics.

## Test set

`build_testset.py` takes songs with synced lyrics, a `vocals.mp3`, and no lyrics
reports, at most one per artist. It keeps a song only if at least 90% of its LRC
line starts have singing within -0.5 s to +1.5 s of them. That check uses the
vocals stem's loudness, not a model, so the set doesn't favour today's aligner.
Line-time noise in community LRCs (often a few tenths of a second early) remains;
the report's signed median shows it.

The set is frozen with the lyrics copied in. Results are only comparable on the
same set, so `--force` is needed to rebuild it. Keep its artists (`artist_key`)
out of any fine-tuning data.

Languages come from `songs.language` or the app's Whisper-small detection. The
2026-10-10 set had two wrong detections (Radiohead → `es`, Little Simz → `yo`),
fixed by hand in the file and marked `language_source: "manual"`.

## Tasks

**asr**: vocals in, text out. Production models run through
`transcribe_lyrics_from_vocals`, exactly as the app runs them. Scored by word
error rate after lowercasing and stripping punctuation and apostrophes. "Lead WER"
drops `(...)` spans from the reference because `vocals.mp3` is the lead stem and
parentheses mostly hold backing vocals; "full WER" keeps them. Numbers aren't
normalised ("2" vs "two" is an error).

**align**: vocals + lyrics in, a start time per line out. Every aligner gets the
same blocks of lines and audio windows (`common.build_blocks`, cached in
`results/blocks/`). The song is split, largest quiet stretch first, until each
window is at most 45 s. The quiet stretches come from the vocals stem's loudness,
so window edges fall where nobody is singing even when the LRC is a second or two
off. (The first version cut windows at padded LRC times; a shifted LRC then put
the end of the previous line inside the window, and aligners latched onto it.)
Each side of a cut keeps at least 1.5 s per line. Where the singing never pauses,
the cut falls back to an LRC line time; those blocks are marked
`quiet_edges: false`. Production aligns with one window per LRC line, which is
tighter; these blocks are looser on purpose so that each model's own placement is
what gets measured.

A line's start is its first timed word. There is no word-level ground truth, so
line starts stand in for word-timing quality. Many LRCs are shifted by a constant
amount (the problem `lyrics_offset.sweep_lrc_offset` fixes in the app), so the
report gives raw error and **offset-corrected** error. Offset-corrected removes
the model's own median shift for each song first, so it measures how well the
model places lines relative to each other, which is what an aligner controls. The
report also counts songs where wav2vec2 and MMS agree that the LRC is shifted.

## Models

| Name | Task | What |
|---|---|---|
| `whisper-small` | asr | App default (`LYRICS_ASR_MODEL` unset) |
| `whisper-large-v3`, `whisper-large-v3-turbo` | asr | Same WhisperX path, bigger models |
| `qwen3-asr-1.7b`, `qwen3-asr-0.6b` | asr | The app's `qwen3` provider |
| `wav2vec2` | align | Production aligner (`align_line_chunks`, WhisperX wav2vec2) |
| `mms-fa` | align | Meta MMS forced aligner via torchaudio; latin script only here, CC-BY-NC weights |
| `qwen3-fa` | align | Qwen3-ForcedAligner-0.6B |

Add a model by adding a loader and a `MODELS` entry in `run_models.py`. A loader
returns a function from a test song to `{"text": ...}` (asr) or
`{"line_starts": [...]}` (align), or `{"error": ...}`.

Timing: production entries reload their model for every song, as the app does,
so their sec/song includes the load; `mms-fa` and `qwen3-fa` load once.

GPU memory: the app's WhisperX transcription path doesn't free VRAM when it
returns (the app relies on `gpu_idle_cleanup` after 30 idle minutes). Called in a
loop, whisper-large-v3 fills a 12 GB card within a few songs. The runner runs
`gc.collect()` + `torch.cuda.empty_cache()` after each song for production
entries. The GPU is shared with dev and prod Celery, so run when they're idle and
use `--retry-failed` to rerun songs that hit out-of-memory errors.
