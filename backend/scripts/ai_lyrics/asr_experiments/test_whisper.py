#!/usr/bin/env python3
"""
Test OpenAI Whisper with word-level timestamps.
This script tests the original OpenAI Whisper implementation for comparison.
"""

import json
import os
import sys
import time
from pathlib import Path

import torch
import whisper

# Fix for Triton compatibility issue
os.environ["TRITON_CACHE_DIR"] = "/tmp/triton_cache"
os.environ["TORCH_COMPILE_DEBUG"] = "0"
# Disable Triton optimization that causes the error
os.environ["TORCH_TRITON_ENABLE"] = "0"


def get_device():
    """Detect the best available device (CUDA > CPU)"""
    if torch.cuda.is_available():
        device = "cuda"
        gpu_name = torch.cuda.get_device_name(0)
        print(f"🚀 CUDA detected: {gpu_name}")
        return device
    else:
        print("💻 Using CPU (CUDA not available)")
        return "cpu"


def test_whisper(audio_path, model_size="base"):
    """Test original OpenAI Whisper with word-level timestamps"""
    print(f"🎤 Testing OpenAI Whisper (model: {model_size})")
    print(f"Audio file: {audio_path}")
    print("=" * 50)

    start_time = time.time()

    # Load model
    print(f"Loading Whisper model ({model_size})...")
    device = get_device()

    try:
        # Load model with detected device
        model = whisper.load_model(model_size, device=device)
        print(f"✅ Model loaded successfully on {device}")
    except Exception as e:
        print(f"❌ Failed to load model on {device}: {e}")
        if device == "cuda":
            print("🔄 Falling back to CPU...")
            try:
                model = whisper.load_model(model_size, device="cpu")
                print("✅ Model loaded successfully on CPU")
            except Exception as e2:
                print(f"❌ Failed to load model on CPU: {e2}")
                raise e2
        else:
            raise e

    # Transcribe with word-level timestamps
    print("Transcribing audio...")
    try:
        result = model.transcribe(
            audio_path,
            word_timestamps=True,  # Enable word-level timestamps
            language="en",
            verbose=False,  # Reduce verbosity to avoid potential issues
        )
    except Exception as e:
        print(f"Error during transcription with word timestamps: {e}")
        # Fallback: try without word timestamps
        print("Retrying without word timestamps...")
        try:
            result = model.transcribe(
                audio_path, word_timestamps=False, language="en", verbose=False
            )
            print("⚠️  Warning: Word-level timestamps not available")
        except Exception as e2:
            print(f"Error during fallback transcription: {e2}")
            raise e2

    # Process results
    results = {
        "model": f"whisper-{model_size}",
        "detected_language": result["language"],
        "text": result["text"],
        "segments": [],
        "words": [],
    }

    print(f"Detected language: {result['language']}")
    print(f"Full transcription: {result['text']}")
    print()

    for segment in result["segments"]:
        print(
            f"Segment [{segment['start']:.2f}s - {segment['end']:.2f}s]: {segment['text']}"
        )

        segment_data = {
            "start": segment["start"],
            "end": segment["end"],
            "text": segment["text"],
            "words": [],
        }

        # Word-level timestamps may not be available
        if "words" in segment and segment["words"]:
            for word in segment["words"]:
                word_data = {
                    "word": word["word"],
                    "start": word["start"],
                    "end": word["end"],
                    "probability": word.get("probability", 0.0),
                }
                segment_data["words"].append(word_data)
                results["words"].append(word_data)
                print(
                    f"  🗣️  '{word['word']}' [{word['start']:.2f}s - {word['end']:.2f}s]"
                )
        else:
            print(f"  (No word-level timestamps available)")
        print()

        results["segments"].append(segment_data)

    processing_time = time.time() - start_time
    results["processing_time"] = processing_time

    # Summary
    print("=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    print(f"Processing time: {processing_time:.2f}s")
    print(f"Total words detected: {len(results['words'])}")
    print(f"Total segments: {len(results['segments'])}")
    if results["words"]:
        print(f"🎯 First word starts at: {results['words'][0]['start']:.2f} seconds")
        print(f"First word: '{results['words'][0]['word']}'")
    else:
        print("❌ No words detected in the audio")

    return results


def save_results(results, output_path):
    """Save results to JSON file"""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_whisper.py <audio_file> [model_size]")
        print("Example: python test_whisper.py /path/to/vocals.mp3 base")
        print("Model sizes: tiny, base, small, medium, large-v1, large-v2, large-v3")
        sys.exit(1)

    audio_file = sys.argv[1]
    model_size = sys.argv[2] if len(sys.argv) > 2 else "base"

    if not Path(audio_file).exists():
        print(f"❌ Error: Audio file '{audio_file}' not found")
        sys.exit(1)

    try:
        # Test the model
        results = test_whisper(audio_file, model_size)

        # Save results
        output_file = f"whisper_{model_size}_results.json"
        save_results(results, output_file)

        print(f"💾 Detailed results saved to: {output_file}")
        print("✅ Test completed successfully!")

    except Exception as e:
        print(f"❌ Error processing audio: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
