# Three-Track Engine VRAM & Compute Optimization

## Context

Goal: run the `three_track` separation engine on a budget dedicated server instead of Spencer's gaming PC (RTX 3080 Ti 12GB). Target hardware is a used 6GB-class card (GTX 1660 / RTX 2060 tier, roughly CA$100–150 used), with 4GB cards as a stretch goal.

Today the engine ([three_track.py](../../backend/app/services/separation_engines/three_track.py)) calls both underlying libraries with pure defaults, which puts the practical VRAM floor at ~8GB:

- **Demucs `htdemucs_ft`** (step 1) — fp32, default segment length, and it's a *bag of four models*, so every song runs through Demucs 4×.
- **Mel-Band Roformer karaoke + de-noise** (steps 2–3, via `audio-separator` 0.30.2) — fp32 (`use_autocast` defaults to `False`), `mdxc_params` overlap of 8. The Roformer pass is what sets the 8GB floor.
- The Demucs model weights stay resident on the GPU while the Roformer loads — peak VRAM is stages *overlapping*, not the max of any single stage.

Hardware notes that shaped the plan:

- Autocast's VRAM savings don't require tensor cores — even the GTX 16-series (no tensor cores, but double-rate FP16 units) gets the full halving and a real speedup. Any Turing-or-newer card qualifies.
- Turing and newer are still on NVIDIA's current driver branch; CUDA + torch 2.8 work fine. Pascal and older (GTX 10-series) are on legacy drivers — avoid.
- All changes must default to current behavior — the gaming PC's output must not change until we opt in via env vars on the new box.

Expected outcome per configuration:

| Configuration | VRAM floor | Card class |
|---|---|---|
| Today (all defaults) | ~8GB | Any 8GB+ card |
| + autocast + memory cleanup (changes 1–2) | ~5–6GB | Any 6GB card (GTX 1660 / RTX 2060 / RTX 3050 6GB tier) |
| + Demucs segment tuning (change 3) | ~4GB | 4GB cards (marginal — stretch goal) |

## Changes

All new settings go in [base.py](../../backend/app/config/base.py) alongside `DEMUCS_MODEL`, read from env vars, defaulting to today's behavior.

### 1. fp16 autocast on the Roformer passes — biggest single win

Pass `use_autocast=config.SEPARATION_USE_AUTOCAST` to both `Separator(...)` constructions in [three_track.py](../../backend/app/services/separation_engines/three_track.py) (karaoke separator at ~line 178, de-noise separator at ~line 257).

- New config: `SEPARATION_USE_AUTOCAST` (bool, default `False`).
- Effect: ~halves VRAM on the passes that set the floor; faster on any card with FP16 throughput.
- The other engines in `separation_engines/` (`roformer_three_track.py`, `three_track_mel1143.py`, `three_track_duality_v2.py`, `audio_sep_roformer.py`, `clean_backing.py`) construct `Separator` the same way — apply the same flag wherever `Separator(...)` is built, or extract a small shared factory helper so the config is honored everywhere.

### 2. Release Demucs GPU memory before the Roformer loads

In `separate_with_three_track`, after the Demucs vocals/instrumental WAVs are written to the temp dir (after the `demucs_end` timestamp, ~line 166): `del demucs_separator` (and the `origin_wave`/`separated` tensors), then `gc.collect()` and `torch.cuda.empty_cache()`.

- No config needed — this is unconditionally correct.
- Effect: peak VRAM becomes the max of any single stage instead of Demucs weights + Roformer overlapping. This is what makes 6GB *comfortable* rather than marginal.

### 3. Expose Demucs `segment`

`demucs.api.Separator` accepts a `segment` argument (seconds of audio processed per chunk) — the official lever for small-VRAM cards. Wire it into the `DemucsSeparator(...)` call (~line 119).

- New config: `DEMUCS_SEGMENT` (int seconds, default unset → library default).
- Effect: lets `htdemucs_ft` run in ~2–3GB with short segments. Only needed on 4GB-class cards; leave unset elsewhere. Quality impact is minor but nonzero at very short segments — that's why it's opt-in.

### 4. Document the `htdemucs` swap (no code change)

`DEMUCS_MODEL=htdemucs` already works via env ([base.py:49](../../backend/app/config/base.py)). Plain `htdemucs` is one model instead of the 4-model `_ft` bag: ~4× faster in step 1, same VRAM, modestly lower quality. **This is the only change with a real quality tradeoff** — the instrumental track comes straight from Demucs. A/B a few songs before committing to it on the server. The existing [compare_three_track_engines.py](../../backend/scripts/experiments/compare_three_track_engines.py) script may help here.

### 5. Make the de-noise pass skippable

Step 3 loads a whole third model just to clean the backing-vocals stem — the least important of the three tracks — and the code already falls back gracefully when the model is unavailable. `roformer_three_track.py` already hard-disables it (`DENOISE_MODEL = "DISABLED"`).

- New config: `THREE_TRACK_DENOISE` (bool, default `True`).
- When `False`, skip step 3 entirely and use the raw backing vocals (same path as the existing failure fallback).
- Effect: ~25% less total processing time and one fewer model download/load on the budget box.

### 6. Tunable Roformer overlap

The `mdxc_params` default is `overlap: 8`. Pass `mdxc_params={..., "overlap": config.ROFORMER_OVERLAP}` (defaults preserved otherwise) in the same `Separator` constructions as change 1.

- New config: `ROFORMER_OVERLAP` (int, default `8`).
- Effect: `2`–`4` cuts Roformer inference time substantially with minor quality cost. Mostly a speed lever for slow cards, not a VRAM lever.

## Out of scope (noted for later)

- **Non-NVIDIA support.** AMD/ROCm needs zero code changes (ROCm torch masquerades as CUDA). Apple Silicon needs `select_device_and_log` ([audio.py:71](../../backend/app/services/audio.py)) to detect MPS plus `PYTORCH_ENABLE_MPS_FALLBACK=1`; `audio-separator` already auto-detects MPS. Not needed for the budget NVIDIA build.
- Rewriting the pipeline around a single Roformer pass (the `roformer_three_track.py` experiment) — separate quality evaluation, not a resource optimization.

## Verification

Celery does **not** hot-reload — restart the worker after each change before testing.

1. Baseline: process a reference song with defaults; record peak VRAM (`nvidia-smi --query-gpu=memory.used --format=csv -l 1` piped to a file) and wall time from the `timing_sink` keys already emitted by the engine.
2. Enable each change (env vars) and re-run the same song; confirm VRAM drop and unchanged-or-acceptable output by ear (vocals.mp3, backing_vocals.mp3, instrumental.mp3).
3. Regression check with everything off: outputs byte-comparable behavior to baseline (same pipeline path, no autocast, denoise on).
4. Final check on the 3080 Ti: cap usable VRAM to simulate the 6GB card (`torch.cuda.set_per_process_memory_fraction(0.5)` in a scratch harness, or just watch that peak stays under 5GB with changes 1–2 enabled).
