#!/usr/bin/env python3
"""
Enhanced Whisper test with more sensitive parameters for catching early/quiet vocals.
"""

import sys
import json
import torch
from pathlib import Path
from faster_whisper import WhisperModel

def test_sensitive_whisper(audio_path):
    """Test faster-whisper with more sensitive parameters."""
    import time

    print(f"🎤 Testing SENSITIVE faster-whisper on: {audio_path}")
    print("=" * 50)

    start_time = time.time()

    # Initialize with larger model for better accuracy
    print("Loading Whisper model (medium for better accuracy)...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "int8" if device == "cuda" else "int8"

    try:
        model = WhisperModel("medium", device=device, compute_type=compute_type)
        print(f"✅ Model loaded successfully on {device}")
    except Exception as e:
        print(f"❌ Failed to load medium model: {e}")
        print("🔄 Falling back to small model...")
        model = WhisperModel("small", device=device, compute_type=compute_type)
        print(f"✅ Small model loaded on {device}")

    # More sensitive transcription parameters
    print("Transcribing with SENSITIVE parameters...")
    segments, info = model.transcribe(
        audio_path,
        beam_size=5,
        word_timestamps=True,
        language="en",
        initial_prompt="Cryptic mystic fortune teller picnic",  # Help it with expected words
        temperature=0.0,  # More deterministic
        compression_ratio_threshold=2.4,  # More permissive
        log_prob_threshold=-1.0,  # More permissive
        no_speech_threshold=0.3,  # Lower threshold (default 0.6)
        condition_on_previous_text=True,  # Use context
        vad_filter=False,  # Disable voice activity detection to catch quiet speech
        vad_parameters=dict(
            threshold=0.3,  # Lower threshold
            min_speech_duration_ms=100,  # Catch shorter speech
            min_silence_duration_ms=500,  # Shorter silence gaps
        )
    )

    print(f"Detected language: {info.language} (confidence: {info.language_probability:.2f})")
    print(f"Audio duration: {info.duration:.2f} seconds")
    print()

    # Process segments and extract word-level timing
    all_words = []
    all_segments = []
    first_word_time = None

    for segment in segments:
        print(f"Segment [{segment.start:.2f}s - {segment.end:.2f}s]: {segment.text}")

        # Store segment data
        segment_data = {
            "start": segment.start,
            "end": segment.end,
            "text": segment.text,
            "words": []
        }

        # Extract word-level timestamps
        if hasattr(segment, 'words') and segment.words:
            for word in segment.words:
                word_data = {
                    "word": word.word.strip(),
                    "start": word.start,
                    "end": word.end,
                    "probability": word.probability
                }
                all_words.append(word_data)
                segment_data["words"].append(word_data)

                # Track the first word
                if first_word_time is None:
                    first_word_time = word.start

                print(f"  🗣️  '{word.word}' [{word.start:.2f}s - {word.end:.2f}s] (confidence: {word.probability:.2f})")

        all_segments.append(segment_data)
        print()

    processing_time = time.time() - start_time

    # Summary
    print("=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    print(f"Processing time: {processing_time:.2f}s")
    print(f"Total words detected: {len(all_words)}")
    if first_word_time is not None:
        print(f"🎯 First word starts at: {first_word_time:.2f} seconds")
        print(f"First word: '{all_words[0]['word']}'" if all_words else "No words detected")
    else:
        print("❌ No words detected in the audio")

    # Save results
    output_file = "vocals_whisper_sensitive_results.json"
    results = {
        "segments": all_segments,
        "words": all_words,
        "info": {
            "language": info.language,
            "language_probability": info.language_probability,
            "duration": info.duration,
            "processing_time": processing_time
        }
    }

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"💾 Detailed results saved to: {output_file}")

    if first_word_time is not None:
        print(f"✅ Success! First vocal detected at {first_word_time:.2f}s")
        return True
    else:
        print("❌ No vocals detected")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_sensitive_whisper.py <audio_file>")
        sys.exit(1)

    audio_file = sys.argv[1]
    if not Path(audio_file).exists():
        print(f"❌ Audio file not found: {audio_file}")
        sys.exit(1)

    success = test_sensitive_whisper(audio_file)
    sys.exit(0 if success else 1)
