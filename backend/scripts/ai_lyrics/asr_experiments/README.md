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
