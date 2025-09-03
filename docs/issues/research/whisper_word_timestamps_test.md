# Quick Test: Word-Level Timestamps with Faster Whisper

## 1. Install Faster Whisper

```zsh
pip install faster-whisper
```

If you have a GPU and want maximum speed, also install the required dependencies for GPU support (see the Faster Whisper docs for CUDA/ROCm specifics).

## 2. Example Python Script

```python
from faster_whisper import WhisperModel

# Path to your audio file (must be WAV, MP3, M4A, etc.)
audio_path = "vocals.mp3"  # Change this to your file

# Load the model ("base", "small", "medium", "large-v2", etc.)
# Set device="cuda" for GPU, or device="cpu" for CPU
model = WhisperModel("small", device="cpu", compute_type="int8")

# Transcribe with word-level timestamps
def main():
    segments, info = model.transcribe(audio_path, word_timestamps=True)
    print(f"Detected language: {info.language}")
    for segment in segments:
        print(f"[Segment {segment.start:.2f}-{segment.end:.2f}s]: {segment.text}")
        if segment.words:
            for word in segment.words:
                print(f"  Word: '{word.word}' [{word.start:.2f}-{word.end:.2f}s]")

if __name__ == "__main__":
    main()
```

## 3. Usage

1. Save this script as `whisper_word_timestamps.py`.
2. Place your test audio file (e.g., `vocals.mp3`) in the same directory or update the path in the script.
3. Run:

```zsh
python whisper_word_timestamps.py
```

---

This script will print the detected language, the transcription, and the start/end time for each word. You can use this to explore how well Faster Whisper detects the start of vocals and aligns with your lyrics.
