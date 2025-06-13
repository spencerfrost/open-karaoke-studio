# Lyric Alignment - Logic-First Approach

This directory contains scripts for aligning existing synced lyrics with vocal tracks using **audio analysis and logic** rather than heavy AI models.

## Philosophy

1. **Logic First** - Use audio analysis, duration comparison, and onset detection
2. **Lightweight** - Fast, minimal dependencies, no heavy AI models
3. **Fallback Only** - Use lightweight ASR only if logic approaches fail

## Approach Priority

### 1. Duration + Window Analysis (Primary)
- Compare synced lyrics total duration vs vocal track duration
- If durations are close (within 2-3 seconds), use a search window
- Detect first significant onset within that window

### 2. Onset Detection (Secondary)
- Use librosa to detect first significant vocal onset
- Energy-based analysis to find where singing actually starts
- Filter out background noise and breath sounds

### 3. Lightweight ASR (Fallback)
- Only if logic approaches have low success rate
- Use smaller, faster models (Vosk, etc.)
- Minimal processing, just first few words

## Scripts

- `duration_analysis.py` - Compare durations and calculate search windows
- `onset_detection.py` - Audio onset detection using librosa
- `logic_alignment.py` - Combined logic-first alignment approach
- `test_alignment.py` - Test alignment accuracy on sample tracks

## Dependencies

```bash
# Lightweight audio analysis
pip install librosa soundfile numpy

# Optional lightweight ASR fallback
pip install vosk  # Much smaller than Whisper
```

## Usage

```bash
# Test duration-based alignment
python duration_analysis.py vocals.mp3 synced_lyrics.lrc

# Test onset detection
python onset_detection.py vocals.mp3

# Full logic-first alignment
python logic_alignment.py vocals.mp3 synced_lyrics.lrc
```
