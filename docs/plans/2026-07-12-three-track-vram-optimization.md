# Three-track separation: faster, same output

Goal: make the `three_track` engine faster, and able to run on a budget dedicated server (a used
4–6GB card) instead of the gaming PC (RTX 3080 Ti 12GB), **with no audible change to the output**.

Rewritten 2026-10-10 from measurements on the 3080 Ti, using five songs and each stage on a fixed input
(scripts in [backend/scripts/experiments/three_track_bench/](../../backend/scripts/experiments/three_track_bench/README.md)).
The first version of this plan guessed at an 8GB VRAM floor and proposed VRAM levers. Most of those
turned out to be unnecessary or harmful.

## What we know

**VRAM is not the constraint.** The unmodified engine peaks at 2.6 GB allocated (3.1 GB reserved),
and it ran successfully capped at 3.5 GB, so a 4GB card already works.

| Stage | Peak allocated |
|---|---|
| Demucs `htdemucs_ft` | 0.55 GB (bag models move to the GPU one at a time and back) |
| Roformer karaoke | 1.70 GB (0.88 GB of it weights) |
| Roformer de-noise | 1.70 GB + 0.88 GB, because the karaoke model is never released |

**Autocast is the speed lever.** `use_autocast=True` on the two Roformer passes makes each one
1.5–1.9× faster. Its output is 60–77 dB from today's fp32 output, and no run produced a NaN. For
scale: Demucs `shifts=1` is random per run, so today's pipeline already varies by 21–27 dB between two runs of
the same song. The karaoke model was trained with `use_amp: true`. Autocast does not save VRAM (+0.28 GB).

Whole-engine time per song on the 3080 Ti, both rows measured in the same session (warm worker):

| Configuration | *Wicked Game* (4:47) | *Paranoid Android* (6:27) |
|---|---|---|
| fp32, no compile, full Demucs bag | 58 s | 77 s |
| Changes 1–3 (0.47.0, autocast, compile, models released) | 42 s | 55 s |
| **Changes 1–3 and 6** (Demucs vocals model only) | **26–31 s** | **33–37 s** |

Stages with changes 1–3 and 6: Demucs 7.5 s / 9.5 s, karaoke 5.7 s / 7.2 s, de-noise 5.8 s / 7.2 s, MP3 5.0 s / 6.7 s.
The spread comes from desktop apps sharing the GPU during the runs.
Peak allocated is 1.77 GB, and the real engine passes under a 3.5 GB cap.

Change 7 (MP3 exports off the critical path), measured against the same code with the exports run inline,
alternating in one session (`e2e_timing.py`): *Wicked Game* 26.7–33.1 s → 22.2–24.5 s, *Paranoid Android*
34.0–35.1 s → 28.3–28.6 s. vocals.mp3 (and the vocal range / lyrics alignment dispatch) is ready ~3 s sooner.
Change 8 (Demucs autocast and overlap 0.1) then takes them to **20.2 s / 25.8 s**, and the engine still passes
under a 3.5 GB cap (peak allocated 1.77 GB).

Where a warm run's time goes with all changes (`overhead_breakdown.py`, *Wicked Game* / *Paranoid Android*,
19.4 s / 24.7 s):

| Part | *Wicked Game* | *Paranoid Android* |
|---|---|---|
| Demucs load / decode / inference / WAV writes | 0.71 / 0.33 / 3.88 / 0.56 s | 0.69 / 0.41 / 5.21 / 0.68 s |
| Karaoke load / inference / WAV write | 1.19 / 3.22 / 0.63 s | 1.16 / 4.47 / 0.73 s |
| De-noise load / inference / WAV write | 1.24 / 3.24 / 0.59 s | 1.15 / 4.46 / 0.79 s |
| Releasing GPU memory (3×) | 0.71 s | 0.68 s |
| Backing-vocals MP3 | 2.29 s | 3.29 s |

**Levers that don't work** (measured, don't revisit):
- Demucs `segment`: no VRAM change, 1.8× slower, and output moves more than run-to-run variation.
- Roformer `segment_size`: saves 0.15 GB and breaks the audio on 0.30.2 (gaps between chunks).
- Freeing Demucs before the Roformer loads: frees 0–8 MB.
- Roformer `overlap`: today's setting gives each 8 s chunk one pass with no overlap. Adding overlap
  costs 2–4× Roformer time. It removes small discontinuities at chunk boundaries that could be measured
  but couldn't be heard, even in isolated stems at the worst boundary. Not worth it.

**audio-separator versions** (`version_bench.py`, same inputs). Prod ran 0.44.5, dev 0.30.2. For our two
Roformers both run one pass per 8 s chunk. 0.47.0 reads `overlap` as a window count and defaults to the
model YAML's `num_overlap: 4` (4× the work); with `overlap=1` its fp32 output is sample-identical to
0.30.2. Karaoke + de-noise pass time on 0.47.0:

| Setting | *Wicked Game* | *Paranoid Android* | vs today's output |
|---|---|---|---|
| fp32 (today) | 24.5 s | 35.0 s | identical |
| autocast | 14.0 s | 18.4 s | 59–73 dB on kept stems |
| autocast + `torch.compile` | 8.6 s | 11.1 s | 60–73 dB on kept stems |

Compile costs ~6 s once per worker process; later jobs reuse it even with a freshly loaded model.

## Changes

### 1. Pin audio-separator

`audio-separator[gpu]==0.47.0` in [requirements.txt](../../backend/requirements.txt), with `overlap=1` set in the
factory (change 2) to keep one pass per chunk.

### 2. A shared `Separator` factory with autocast and compile

[roformer_loader.py](../../backend/app/services/separation_engines/roformer_loader.py) builds every audio-separator `Separator` and loads its model.
`three_track.py`, `clean_backing.py`, `roformer_three_track.py`, `hybrid_sequential.py` and
`audio_sep_roformer.py` all use it. `three_track_mel1143.py` and `three_track_duality_v2.py`
wrap `separate_with_three_track`, so they get it for free.

- Config `SEPARATION_USE_AUTOCAST` and `SEPARATION_TORCH_COMPILE` in [base.py](../../backend/app/config/base.py), both default `True`.
  Compile falls back to eager on a build that can't compile (prod's image has Triton 3.4.0).
- Passes `mdxc_params` with `overlap=1`.
- **Catch `SystemExit` from `load_model`.** On any `RuntimeError` during load, CUDA out-of-memory
  included, audio-separator calls `sys.exit(1)`. `SystemExit` gets past the engine's
  `except torch.cuda.OutOfMemoryError` and `except Exception`, so the OOM auto-retry never runs.
  Re-raise it as `torch.cuda.OutOfMemoryError` when CUDA memory is the cause, otherwise as `RuntimeError`.

### 3. Release each model before the next loads

In `separate_with_three_track`, after step 2: `del karaoke_separator`, `gc.collect()`,
`torch.cuda.empty_cache()`. Do the same after Demucs and after step 3. This removes the 0.88 GB
overlap during de-noise, and the cached memory stops blocking the other Celery worker on the shared GPU.

### 4. `THREE_TRACK_DENOISE` toggle (default `True`)

When `False`, skip step 3 and use the raw backing vocals (the existing fallback path). De-noise
changes the backing track only slightly (39–49 dB SNR against its input) but costs a whole Roformer pass. Whether to
turn it off on the budget box is a listening call.

### 5. `htdemucs` (don't use)

`DEMUCS_MODEL=htdemucs` works through the env, but it runs no faster than change 6 and its output is
16–23 dB from `_ft` on all three stems.

### 6. Demucs: run only the vocals model

`htdemucs_ft` is a bag of four models with one-hot weights: each separates all four stems over the whole
song, and the bag keeps one stem from each. `separate_with_three_track` runs only the vocals model
(`_use_vocals_specialist`) and takes instrumental = mix − vocals. A single model such as `htdemucs` runs as
it is. Measured with `demucs_specialist_bench.py` on *Paranoid Android* / *Wicked Game*:

- Demucs inference 30 s / 23 s → 7.9 s / 5.9 s, same 0.55 GB peak.
- Vocals are the bag's vocals (23.5 / 26.3 dB vs a seed-0 run, same as two runs of today).
- Instrumental 20.9 / 20.8 dB from today's, where two runs of today differ by 24.9 / 21.6 dB.
  Listening test (2026-10-10): no noticeable difference.
- The vocals model's own drums + bass + other are 3 dB from today's, so they aren't used.

### 7. Encode each MP3 as soon as its stem is ready

Each export takes 2.4–3.3 s of one CPU core. `separate_with_three_track` submits them to a three-thread pool:
instrumental.mp3 right after Demucs, vocals.mp3 right after the karaoke pass, so both encode while the GPU
stages run. Only backing_vocals.mp3 is left after de-noise. `on_vocals_ready` fires from the encoder thread once
vocals.mp3 is written (the callback opens its own DB session). Leaving the pool waits for running exports, so a stop
or failure never removes the temp dir under one. The MP3s are byte-identical to sequential exports
(`mp3_export_bench.py`), and the encodes don't slow the GPU stages.

### 8. Demucs: fp16 autocast and overlap 0.1

`separate_with_three_track` runs Demucs under `torch.autocast` (fp16, CUDA only, behind `SEPARATION_USE_AUTOCAST`)
with `overlap=0.1` (`DEMUCS_OVERLAP`) instead of the default 0.25 between 7.8 s segments. Measured with
`demucs_variants_bench.py`, inference only, against the same seed:

| Variant | *Wicked Game* | *Paranoid Android* | SNR vs fp32 / 0.25 |
|---|---|---|---|
| fp32, overlap 0.25 | 5.67 s | 7.58 s | — |
| Autocast | 4.83 s | 6.46 s | 60.1–66.5 dB |
| Overlap 0.1 | 4.74 s | 6.48 s | 19.4–25.8 dB |
| **Autocast + overlap 0.1** | **3.97 s** | **5.51 s** | 19.4–25.8 dB |
| Overlap 0 | 4.05 s | 6.02 s | 17.8–24.3 dB |

Two seeds of fp32 / 0.25 differ by 24.0–30.4 dB. Lower overlap concentrates its change at the segment boundaries
(diff spikes 35–40 dB above its median there). Listening test (2026-10-10), A/B on both stems at the worst
boundaries: autocast and overlap 0.1 sound the same as today; overlap 0 is faintly audible, so it isn't used.
Autocast adds 0.07 GB to the Demucs peak (0.62 GB).

## Further optimization to investigate

Measure each lead on its own with the bench scripts, and judge any output change by **listening**, not by SNR
alone. A change that can be measured but can't be heard is fine; one that sounds different needs the user's ear.

**Demucs mix on the GPU.** Given a CPU tensor, Demucs keeps its whole-song output buffer and overlap-add on
the CPU (370% CPU during inference). Moving the mix to the GPU first (`demucs_variants_bench.py` variant
`gpu_mix`, measured at fp32 / overlap 0.25) saves ~0.5 s with 75.7–82.1 dB SNR (float rounding only), but the buffer
grows with song length: the Demucs peak goes from 0.55 GB to 1.23 GB at 4:47 and 1.54 GB at 6:27.

**Per-job overhead** (the table above): model loads are ~3.1 s per song (Demucs bag 0.7 s, each Roformer
1.2 s); the GPU release between stages 0.7 s. The Celery worker is one long-lived process
(`--pool=threads --concurrency=1`), so a cache would persist between jobs.
- Keeping all three models on the GPU saves up to ~3.8 s per song, but holds ~1.9 GB VRAM on the shared GPU
  between jobs. [gpu_idle_cleanup.py](../../backend/app/services/gpu_idle_cleanup.py) has an idle-release pattern.
- Keeping them in CPU RAM instead: a loaded Roformer moves to the GPU in 0.15 s and back in 0.23 s; Demucs
  already moves its model to the GPU and back on every run. That saves ~2.4 s per song for ~2.1 GB of
  worker RAM, with no VRAM held between jobs.

## Verification

Celery does not hot-reload: restart the worker after each change.

1. Unit tests ([test_separation_engines.py](../../backend/tests/unit/test_services/test_separation_engines.py)):
   the factory passes autocast and compile from config and `overlap=1`; load-time `SystemExit` becomes OOM or
   `RuntimeError`; the de-noise toggle; each MP3 comes from its own WAV, `on_vocals_ready` fires once vocals.mp3
   is written, and a failed export fails the engine and removes the temp dir. Outputs can't be byte-compared, because Demucs `shifts=1` is random per run.
2. `version_bench.py` on a couple of songs: SNR vs today's fp32 ≥ 50 dB on every kept stem, and no NaN.
3. `e2e_capped.py` at 3.5 GB passes.
4. On the budget card: one song with autocast on and one with it off, compared (≥ 50 dB, no NaN), with
   the time per song recorded.
