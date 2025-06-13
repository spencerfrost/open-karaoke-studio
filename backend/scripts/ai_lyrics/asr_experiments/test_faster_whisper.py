#!/usr/bin/env python3
"""
Basic test of faster-whisper with word-level timestamps.
This script demonstrates how to get precise timing for each word in a vocal track.
"""

import sys
import json
import torch
from pathlib import Path
from faster_whisper import WhisperModel

def get_device():
    """Detect the best available device and compute type"""
    if torch.cuda.is_available():
        device = "cuda"
        gpu_name = torch.cuda.get_device_name(0)
        print(f"🚀 CUDA detected: {gpu_name}")
        compute_type = "int8"  # Use int8 for faster inference on GPU
        return device, compute_type
    else:
        print("💻 Using CPU (CUDA not available)")
        return "cpu", "int8"

def test_faster_whisper(audio_path):
    """Test faster-whisper with word timestamps on an audio file."""
    import time
    
    print(f"🎤 Testing faster-whisper on: {audio_path}")
    print("=" * 50)
    
    start_time = time.time()
    
    # Initialize the model (using small model for speed, you can use larger for accuracy)
    # Options: tiny, base, small, medium, large-v1, large-v2, large-v3
    print("Loading Whisper model (small)...")
    device, compute_type = get_device()
    
    try:
        model = WhisperModel("small", device=device, compute_type=compute_type)
        print(f"✅ Model loaded successfully on {device} with {compute_type}")
    except Exception as e:
        print(f"❌ Failed to load model on {device}: {e}")
        if device == "cuda":
            print("🔄 Falling back to CPU...")
            try:
                model = WhisperModel("small", device="cpu", compute_type="int8")
                print("✅ Model loaded successfully on CPU")
            except Exception as e2:
                print(f"❌ Failed to load model on CPU: {e2}")
                raise e2
        else:
            raise e
    
    # Transcribe with word-level timestamps
    print("Transcribing audio...")
    segments, info = model.transcribe(
        audio_path, 
        beam_size=5,
        word_timestamps=True,
        language="en"  # Set to None for auto-detection
    )
    
    print(f"Detected language: {info.language} (confidence: {info.language_probability:.2f})")
    print(f"Audio duration: {info.duration:.2f} seconds")
    print()
    
    # Process segments and extract word-level timing
    all_words = []
    all_segments = []
    first_word_time = None
    full_text = ""
    
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
        full_text += segment.text
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
    
    # Save detailed results to JSON
    output_file = Path(audio_path).stem + "_whisper_results.json"
    results = {
        "audio_file": str(audio_path),
        "detected_language": info.language,
        "language_probability": info.language_probability,
        "duration": info.duration,
        "processing_time": processing_time,
        "text": full_text.strip(),
        "segments": all_segments,
        "words": all_words
    }
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"💾 Detailed results saved to: {output_file}")
    
    return results

def main():
    if len(sys.argv) != 2:
        print("Usage: python test_faster_whisper.py <audio_file>")
        print("Example: python test_faster_whisper.py /path/to/vocals.mp3")
        sys.exit(1)
    
    audio_path = sys.argv[1]
    
    if not Path(audio_path).exists():
        print(f"❌ Error: Audio file not found: {audio_path}")
        sys.exit(1)
    
    try:
        results = test_faster_whisper(audio_path)
        first_word_time = results['words'][0]['start'] if results['words'] else None
        if first_word_time is not None:
            print(f"\n✅ Success! First vocal detected at {first_word_time:.2f}s")
        else:
            print(f"\n✅ Processing completed, but no words detected")
        
    except Exception as e:
        print(f"❌ Error processing audio: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
