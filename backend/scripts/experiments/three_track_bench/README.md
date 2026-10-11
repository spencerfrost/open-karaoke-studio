# Three-track separation benchmark

Measures VRAM, speed and output drift for each stage of the `three_track` engine. Background is in
[docs/plans/2026-07-12-three-track-vram-optimization.md](../../../../docs/plans/2026-07-12-three-track-vram-optimization.md).
Reads songs from `karaoke_library/` and writes only to the output dir you pass in.

Run from `backend/` with the venv active. Stop GPU-heavy jobs first: another process filling
the GPU makes these runs fail with OOM. If a Roformer model load hits OOM, audio-separator calls
`sys.exit(1)` and the run ends without a traceback.

```bash
OUT=../three_track_compare_bench   # gitignored via three_track_compare*/

# 1. Per-stage VRAM / speed / SNR vs today's fp32 output (about 5 min per song)
python scripts/experiments/three_track_bench/vram_quality_bench.py $OUT <song_id>,<song_id>,...

# 2. Seam statistics at 8 s chunk boundaries, plus autocast at the corrected overlap
python scripts/experiments/three_track_bench/seam_and_proposed.py $OUT

# 3. Another audio-separator version on the same inputs, without touching the venv:
pip download audio-separator==0.47.0 --no-deps -d /tmp/as && unzip -q /tmp/as/*.whl -d /tmp/as047
PYTHONPATH=/tmp/as047 python scripts/experiments/three_track_bench/bench047.py $OUT

# 4. The real engine under a VRAM cap (GB)
python scripts/experiments/three_track_bench/e2e_capped.py $OUT <song_id> 3.5

# 5. audio-separator versions on the Roformer passes: today's reference first (needs 0.30.2), then each
#    version from an unpacked wheel, e.g. /tmp/as047 from step 3
python scripts/experiments/three_track_bench/version_bench.py prepare $OUT <song_id>,<song_id>
PYTHONPATH=/tmp/as047 python scripts/experiments/three_track_bench/version_bench.py run $OUT

# 6. htdemucs_ft bag vs its vocals model alone; writes instrumentals + diffs as WAV for listening
python scripts/experiments/three_track_bench/demucs_specialist_bench.py $OUT <song_id>,<song_id>

# 7. The engine's Demucs step under inference variants (autocast, overlap_<x>, gpu_mix, joined with +),
#    each at the baseline's seed; writes vocals, instrumental and diffs as WAV for listening
python scripts/experiments/three_track_bench/demucs_variants_bench.py $OUT <song_id>,<song_id> autocast,overlap_0.1

# 8. The three WAV -> MP3 exports: pydub vs ffmpeg, sequential vs parallel, at "320" and "320k"
python scripts/experiments/three_track_bench/mp3_export_bench.py $OUT <song_id>,<song_id>

# 9. Whole engine, current code vs MP3 exports run inline, alternating in one process
python scripts/experiments/three_track_bench/e2e_timing.py $OUT <song_id>,<song_id> --runs 2

# 10. Where a warm engine run's time goes: model loads, decode, inference, WAV writes, GPU release
python scripts/experiments/three_track_bench/overhead_breakdown.py $OUT <song_id>,<song_id>
```

The app pins audio-separator 0.47.0. `vram_quality_bench.py`, `seam_and_proposed.py` and
`version_bench.py prepare` use 0.30.2 overlap semantics (`overlap=2` means a 2 s step; on 0.47.0 it is a
window count), so run them with 0.30.2 unpacked on `PYTHONPATH`
(`pip download audio-separator==0.30.2 --no-deps`, unzip as in step 3).
