# ASR Experiments - Vocal Start Detection

This directory contains experimental scripts for using Automatic Speech Recognition (ASR) to detect the start of vocals in isolated vocal tracks.

## Setup

First, install the required packages:

```bash
# For faster-whisper (recommended)
pip install faster-whisper

# Alternative: extremely-fast-whisper (even faster)
# pip install faster-whisper

# Audio processing utilities
pip install librosa soundfile
```

## Scripts

1. **`test_faster_whisper.py`** - Basic faster-whisper test with word timestamps
2. **`test_vocal_start.py`** - Detect the start of vocals in a track
3. **`compare_models.py`** - Compare different ASR approaches
4. **`compare_whisperx_qwen3.py`** - Run WhisperX and Qwen3-ASR side-by-side across multiple songs

## WhisperX vs Qwen3-ASR

Install dependencies (inside backend virtualenv):

```bash
pip install -r requirements.txt
```

Run both providers on several random songs:

```bash
python scripts/ai_lyrics/asr_experiments/compare_whisperx_qwen3.py \
	--providers whisperx,qwen3 \
	--sample 5 \
	--language en
```

Run by explicit song ids:

```bash
python scripts/ai_lyrics/asr_experiments/compare_whisperx_qwen3.py \
	--providers whisperx,qwen3 \
	--song-id <song_id_1> \
	--song-id <song_id_2>
```

Useful env vars:

- `LYRICS_ASR_PROVIDER=whisperx|qwen3`
- `LYRICS_ASR_MODEL` (WhisperX model, default `small`)
- `LYRICS_QWEN_ASR_MODEL` (default `Qwen/Qwen3-ASR-1.7B`)
- `LYRICS_QWEN_FORCED_ALIGNER` (default `Qwen/Qwen3-ForcedAligner-0.6B`)

Outputs:

- JSON report with per-run metrics and provider summary
- CSV report for spreadsheet comparison (speed/word count/mean score/success rate)

## Usage

```bash
# Test with a sample vocal track
python test_faster_whisper.py path/to/vocals.mp3

# Detect vocal start timing
python test_vocal_start.py path/to/vocals.mp3
```

## Notes

- These scripts work best with clean, isolated vocal tracks (like our vocals.mp3 files)
- faster-whisper provides excellent accuracy and speed for this use case
- Word-level timestamps are crucial for aligning lyrics with audio timing
