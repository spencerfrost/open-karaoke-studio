#!/usr/bin/env python3
"""
Test Insanely Fast Whisper with word-level timestamps.
This script tests the HuggingFace Transformers-based implementation.
"""

import json
import time
import torch
from pathlib import Path
import sys

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

def test_insanely_fast_whisper(audio_path, model_size="openai/whisper-base"):
    """Test Insanely Fast Whisper with word-level timestamps"""
    print(f"🎤 Testing Insanely Fast Whisper (model: {model_size})")
    print(f"Audio file: {audio_path}")
    print("=" * 50)

    start_time = time.time()

    try:
        # Import here to catch import errors
        from transformers import AutomaticSpeechRecognitionPipeline, WhisperProcessor, WhisperForConditionalGeneration
        import torch

        print(f"Loading model ({model_size})...")
        device = get_device()

        # Load model and processor
        processor = WhisperProcessor.from_pretrained(model_size)
        model = WhisperForConditionalGeneration.from_pretrained(model_size)

        # Move model to appropriate device
        model = model.to(device)
        print(f"✅ Model loaded and moved to {device}")

        # Create pipeline with detected device
        pipe = AutomaticSpeechRecognitionPipeline(
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor,
            torch_dtype=torch.float32,
            device=device
        )

        print("Transcribing audio...")

        # Transcribe with word-level timestamps
        result = pipe(
            audio_path,
            return_timestamps="word",
            generate_kwargs={"language": "en"}
        )

        # Process results
        results = {
            "model": f"insanely-fast-whisper-{model_size.split('/')[-1]}",
            "text": result.get("text", ""),
            "segments": [],
            "words": []
        }

        print(f"Full transcription: {result.get('text', '')}")
        print()

        # Handle word-level timestamps
        if "chunks" in result:
            for chunk in result["chunks"]:
                if chunk.get("timestamp"):
                    start_time_chunk = chunk["timestamp"][0] if chunk["timestamp"][0] is not None else 0.0
                    end_time_chunk = chunk["timestamp"][1] if chunk["timestamp"][1] is not None else 0.0

                    word_data = {
                        "word": chunk["text"],
                        "start": start_time_chunk,
                        "end": end_time_chunk,
                        "probability": 1.0  # Not available in this implementation
                    }
                    results["words"].append(word_data)
                    print(f"🗣️  '{chunk['text']}' [{start_time_chunk:.2f}s - {end_time_chunk:.2f}s]")

        # Group words into segments (approximate)
        if results["words"]:
            segment_words = []
            segment_start = results["words"][0]["start"]

            for word in results["words"]:
                segment_words.append(word)

                # Create new segment every 5 seconds or at sentence boundaries
                if (word["end"] - segment_start > 5.0) or word["word"].strip().endswith(('.', '!', '?')):
                    segment_data = {
                        "start": segment_start,
                        "end": word["end"],
                        "text": " ".join([w["word"] for w in segment_words]),
                        "words": segment_words.copy()
                    }
                    results["segments"].append(segment_data)
                    segment_words = []
                    if results["words"].index(word) + 1 < len(results["words"]):
                        segment_start = results["words"][results["words"].index(word) + 1]["start"]

            # Add remaining words as final segment
            if segment_words:
                segment_data = {
                    "start": segment_start,
                    "end": segment_words[-1]["end"],
                    "text": " ".join([w["word"] for w in segment_words]),
                    "words": segment_words
                }
                results["segments"].append(segment_data)

        processing_time = time.time() - start_time
        results["processing_time"] = processing_time

        # Summary
        print()
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

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you have transformers and torch installed:")
        print("pip install transformers torch")
        return None
    except Exception as e:
        print(f"❌ Error with Insanely Fast Whisper: {e}")
        import traceback
        traceback.print_exc()
        return None

def save_results(results, output_path):
    """Save results to JSON file"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_insanely_fast_whisper.py <audio_file> [model_size]")
        print("Example: python test_insanely_fast_whisper.py /path/to/vocals.mp3")
        print("Model sizes: openai/whisper-tiny, openai/whisper-base, openai/whisper-small, etc.")
        sys.exit(1)

    audio_file = sys.argv[1]
    model_size = sys.argv[2] if len(sys.argv) > 2 else "openai/whisper-base"

    if not Path(audio_file).exists():
        print(f"❌ Error: Audio file '{audio_file}' not found")
        sys.exit(1)

    # Test the model
    results = test_insanely_fast_whisper(audio_file, model_size)

    if results:
        # Save results
        output_file = f"insanely_fast_whisper_results.json"
        save_results(results, output_file)

        print(f"💾 Detailed results saved to: {output_file}")
        print("✅ Test completed successfully!")
    else:
        print("❌ Failed to get results from Insanely Fast Whisper")
        sys.exit(1)

if __name__ == "__main__":
    main()
