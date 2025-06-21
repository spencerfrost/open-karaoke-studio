# ASR Model Experimentation Implementation Guide

This guide provides step-by-step instructions for setting up and testing different Automatic Speech Recognition (ASR) models to find the optimal solution for generating AI lyrics with precise word-level timestamps.

## Overview

We will test and compare several state-of-the-art ASR models:

1. **OpenAI Whisper** - The original model with excellent accuracy
2. **Faster Whisper** - Optimized CT2 implementation for faster inference
3. **Insanely Fast Whisper** - HuggingFace Transformers-based implementation
4. **Additional models** - Other promising ASR solutions

## Phase 1: Environment Setup

### 1.1 Create Virtual Environment

```bash
# Navigate to the ASR experiments directory
cd /home/spencer/code/open-karaoke-studio/backend/scripts/ai_lyrics/asr_experiments

# Create virtual environment
python -m venv venv_asr

# Activate virtual environment
source venv_asr/bin/activate  # Linux/Mac
# or
# venv_asr\Scripts\activate  # Windows
```

### 1.2 Install Core Dependencies

```bash
# Install base requirements
pip install --upgrade pip

# Audio processing
pip install librosa soundfile

# Data analysis and visualization
pip install pandas matplotlib seaborn numpy

# Text processing and evaluation
pip install nltk spacy jiwer

# Download NLTK data (run in Python)
python -c "import nltk; nltk.download('punkt')"
```

### 1.3 Install ASR Models

Install each ASR model separately to test compatibility:

```bash
# 1. Faster Whisper (recommended starting point)
pip install faster-whisper

# 2. Original OpenAI Whisper
pip install openai-whisper

# 3. Insanely Fast Whisper
pip install insanely-fast-whisper

# 4. HuggingFace Transformers (for additional models)
pip install transformers torch torchaudio

# 5. SpeechRecognition (for comparison)
pip install speechrecognition
```

## Phase 2: Basic Model Testing

### 2.1 Test Faster Whisper

Create `test_faster_whisper.py`:

```python
import json
import time
from pathlib import Path
from faster_whisper import WhisperModel

def test_faster_whisper(audio_path, model_size="base"):
    """Test Faster Whisper with word-level timestamps"""
    print(f"Testing Faster Whisper (model: {model_size})")
    print(f"Audio file: {audio_path}")
    
    start_time = time.time()
    
    # Initialize model
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    
    # Transcribe with word-level timestamps
    segments, info = model.transcribe(
        audio_path,
        beam_size=5,
        word_timestamps=True,
        language="en"  # Specify language for better performance
    )
    
    # Process results
    results = {
        "model": f"faster-whisper-{model_size}",
        "detected_language": info.language,
        "language_probability": info.language_probability,
        "duration": info.duration,
        "segments": [],
        "words": []
    }
    
    for segment in segments:
        segment_data = {
            "start": segment.start,
            "end": segment.end,
            "text": segment.text,
            "words": []
        }
        
        if segment.words:
            for word in segment.words:
                word_data = {
                    "word": word.word,
                    "start": word.start,
                    "end": word.end,
                    "probability": word.probability
                }
                segment_data["words"].append(word_data)
                results["words"].append(word_data)
        
        results["segments"].append(segment_data)
    
    processing_time = time.time() - start_time
    results["processing_time"] = processing_time
    
    print(f"Processing time: {processing_time:.2f}s")
    print(f"Audio duration: {info.duration:.2f}s")
    print(f"Real-time factor: {processing_time/info.duration:.2f}x")
    
    return results

def save_results(results, output_path):
    """Save results to JSON file"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python test_faster_whisper.py <audio_file> [model_size]")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    model_size = sys.argv[2] if len(sys.argv) > 2 else "base"
    
    if not Path(audio_file).exists():
        print(f"Error: Audio file '{audio_file}' not found")
        sys.exit(1)
    
    # Test the model
    results = test_faster_whisper(audio_file, model_size)
    
    # Save results
    output_file = f"faster_whisper_{model_size}_results.json"
    save_results(results, output_file)
    
    print(f"\nResults saved to: {output_file}")
    print(f"Total words detected: {len(results['words'])}")
    print(f"Total segments: {len(results['segments'])}")
```

### 2.2 Test Original Whisper

Create `test_whisper.py`:

```python
import json
import time
import whisper
from pathlib import Path

def test_whisper(audio_path, model_size="base"):
    """Test original OpenAI Whisper with word-level timestamps"""
    print(f"Testing OpenAI Whisper (model: {model_size})")
    print(f"Audio file: {audio_path}")
    
    start_time = time.time()
    
    # Load model
    model = whisper.load_model(model_size)
    
    # Transcribe with word-level timestamps
    result = model.transcribe(
        audio_path,
        word_timestamps=True,
        language="en"
    )
    
    # Process results
    results = {
        "model": f"whisper-{model_size}",
        "detected_language": result["language"],
        "text": result["text"],
        "segments": [],
        "words": []
    }
    
    for segment in result["segments"]:
        segment_data = {
            "start": segment["start"],
            "end": segment["end"],
            "text": segment["text"],
            "words": []
        }
        
        if "words" in segment:
            for word in segment["words"]:
                word_data = {
                    "word": word["word"],
                    "start": word["start"],
                    "end": word["end"],
                    "probability": word.get("probability", 0.0)
                }
                segment_data["words"].append(word_data)
                results["words"].append(word_data)
        
        results["segments"].append(segment_data)
    
    processing_time = time.time() - start_time
    results["processing_time"] = processing_time
    
    print(f"Processing time: {processing_time:.2f}s")
    print(f"Real-time factor: {processing_time/30:.2f}x")  # Assume ~30s audio
    
    return results

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python test_whisper.py <audio_file> [model_size]")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    model_size = sys.argv[2] if len(sys.argv) > 2 else "base"
    
    if not Path(audio_file).exists():
        print(f"Error: Audio file '{audio_file}' not found")
        sys.exit(1)
    
    # Test the model
    results = test_whisper(audio_file, model_size)
    
    # Save results
    output_file = f"whisper_{model_size}_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nResults saved to: {output_file}")
    print(f"Total words detected: {len(results['words'])}")
    print(f"Total segments: {len(results['segments'])}")
```

### 2.3 Test Insanely Fast Whisper

Create `test_insanely_fast_whisper.py`:

```python
import json
import time
from pathlib import Path
from insanely_fast_whisper import transcribe_with_word_timestamps

def test_insanely_fast_whisper(audio_path, model_size="openai/whisper-base"):
    """Test Insanely Fast Whisper with word-level timestamps"""
    print(f"Testing Insanely Fast Whisper (model: {model_size})")
    print(f"Audio file: {audio_path}")
    
    start_time = time.time()
    
    try:
        # Transcribe with word-level timestamps
        result = transcribe_with_word_timestamps(
            audio_path,
            model_name=model_size,
            device="cpu",  # Change to "cuda" if GPU available
            language="en"
        )
        
        # Process results
        results = {
            "model": f"insanely-fast-whisper-{model_size.split('/')[-1]}",
            "detected_language": result.get("language", "en"),
            "text": result.get("text", ""),
            "segments": [],
            "words": []
        }
        
        if "chunks" in result:
            for chunk in result["chunks"]:
                segment_data = {
                    "start": chunk["timestamp"][0],
                    "end": chunk["timestamp"][1],
                    "text": chunk["text"],
                    "words": []
                }
                
                if "words" in chunk:
                    for word in chunk["words"]:
                        word_data = {
                            "word": word["word"],
                            "start": word["timestamp"][0],
                            "end": word["timestamp"][1],
                            "probability": word.get("probability", 0.0)
                        }
                        segment_data["words"].append(word_data)
                        results["words"].append(word_data)
                
                results["segments"].append(segment_data)
        
        processing_time = time.time() - start_time
        results["processing_time"] = processing_time
        
        print(f"Processing time: {processing_time:.2f}s")
        print(f"Real-time factor: {processing_time/30:.2f}x")  # Assume ~30s audio
        
        return results
        
    except Exception as e:
        print(f"Error with Insanely Fast Whisper: {e}")
        return None

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python test_insanely_fast_whisper.py <audio_file> [model_size]")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    model_size = sys.argv[2] if len(sys.argv) > 2 else "openai/whisper-base"
    
    if not Path(audio_file).exists():
        print(f"Error: Audio file '{audio_file}' not found")
        sys.exit(1)
    
    # Test the model
    results = test_insanely_fast_whisper(audio_file, model_size)
    
    if results:
        # Save results
        output_file = f"insanely_fast_whisper_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\nResults saved to: {output_file}")
        print(f"Total words detected: {len(results['words'])}")
        print(f"Total segments: {len(results['segments'])}")
    else:
        print("Failed to get results from Insanely Fast Whisper")
```

## Phase 3: Model Comparison

### 3.1 Create Comparison Script

Create `compare_models.py`:

```python
import json
import time
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any

def run_all_models(audio_path: str) -> Dict[str, Any]:
    """Run all available ASR models on the same audio file"""
    results = {}
    
    # Test Faster Whisper
    try:
        from test_faster_whisper import test_faster_whisper
        print("Testing Faster Whisper...")
        results["faster_whisper"] = test_faster_whisper(audio_path, "base")
    except Exception as e:
        print(f"Faster Whisper failed: {e}")
        results["faster_whisper"] = None
    
    # Test Original Whisper
    try:
        from test_whisper import test_whisper
        print("\nTesting Original Whisper...")
        results["whisper"] = test_whisper(audio_path, "base")
    except Exception as e:
        print(f"Original Whisper failed: {e}")
        results["whisper"] = None
    
    # Test Insanely Fast Whisper
    try:
        from test_insanely_fast_whisper import test_insanely_fast_whisper
        print("\nTesting Insanely Fast Whisper...")
        results["insanely_fast_whisper"] = test_insanely_fast_whisper(audio_path)
    except Exception as e:
        print(f"Insanely Fast Whisper failed: {e}")
        results["insanely_fast_whisper"] = None
    
    return results

def analyze_results(results: Dict[str, Any]) -> pd.DataFrame:
    """Analyze and compare results from different models"""
    comparison_data = []
    
    for model_name, result in results.items():
        if result is None:
            continue
        
        comparison_data.append({
            "Model": model_name,
            "Processing Time (s)": result.get("processing_time", 0),
            "Total Words": len(result.get("words", [])),
            "Total Segments": len(result.get("segments", [])),
            "Language": result.get("detected_language", "unknown"),
            "Avg Words per Segment": len(result.get("words", [])) / max(len(result.get("segments", [])), 1)
        })
    
    return pd.DataFrame(comparison_data)

def save_detailed_comparison(results: Dict[str, Any], output_path: str):
    """Save detailed comparison results"""
    comparison = {
        "summary": {},
        "detailed_results": results,
        "word_level_comparison": []
    }
    
    # Create word-level comparison
    all_words = {}
    for model_name, result in results.items():
        if result and "words" in result:
            all_words[model_name] = result["words"]
    
    comparison["word_level_comparison"] = all_words
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python compare_models.py <audio_file>")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    
    if not Path(audio_file).exists():
        print(f"Error: Audio file '{audio_file}' not found")
        sys.exit(1)
    
    print(f"Comparing ASR models on: {audio_file}")
    print("=" * 50)
    
    # Run all models
    results = run_all_models(audio_file)
    
    # Analyze results
    df = analyze_results(results)
    print("\nComparison Summary:")
    print(df.to_string(index=False))
    
    # Save detailed results
    output_file = "model_comparison_results.json"
    save_detailed_comparison(results, output_file)
    
    # Save summary CSV
    df.to_csv("model_comparison_summary.csv", index=False)
    
    print(f"\nDetailed results saved to: {output_file}")
    print(f"Summary saved to: model_comparison_summary.csv")
```

## Phase 4: Testing Instructions

### 4.1 Prepare Test Audio

1. Use a short vocal track (30-60 seconds) for initial testing
2. Ensure the audio is in a supported format (MP3, WAV, FLAC)
3. Use isolated vocals from your AI separation pipeline

### 4.2 Run Initial Tests

```bash
# Test each model individually
python test_faster_whisper.py path/to/test_vocals.mp3
python test_whisper.py path/to/test_vocals.mp3
python test_insanely_fast_whisper.py path/to/test_vocals.mp3

# Compare all models
python compare_models.py path/to/test_vocals.mp3
```

### 4.3 Analyze Results

1. **Check JSON output files** for detailed transcription and timing data
2. **Review CSV summary** for quick performance comparison
3. **Examine word-level timestamps** for accuracy and precision
4. **Compare transcription quality** manually

### 4.4 Key Metrics to Evaluate

- **Processing Speed**: Real-time factor (processing_time / audio_duration)
- **Transcription Accuracy**: Manual review of text quality
- **Timestamp Precision**: Word-level timing accuracy
- **Output Format**: Ease of integration with karaoke system
- **Memory Usage**: Resource requirements
- **Reliability**: Consistency across different audio samples

## Phase 5: Next Steps

After initial testing:

1. **Test with multiple audio samples** to ensure consistency
2. **Benchmark performance** with longer audio files
3. **Implement quality metrics** (WER, BLEU scores if reference text available)
4. **Create format converters** for optimal output formats
5. **Design integration pipeline** for the main karaoke application

## Troubleshooting

### Common Issues

1. **CUDA/GPU Issues**: Start with CPU-only testing, add GPU support later
2. **Memory Errors**: Use smaller model sizes or process in chunks
3. **Audio Format Issues**: Convert audio to WAV format if needed
4. **Import Errors**: Install models one by one to isolate issues

### Audio Preprocessing

If needed, preprocess audio files:

```python
import librosa
import soundfile as sf

def preprocess_audio(input_path, output_path, target_sr=16000):
    """Preprocess audio for better ASR results"""
    # Load audio
    audio, sr = librosa.load(input_path, sr=target_sr)
    
    # Normalize
    audio = librosa.util.normalize(audio)
    
    # Save
    sf.write(output_path, audio, target_sr)
```

This implementation guide provides a solid foundation for experimenting with different ASR models and finding the optimal solution for your karaoke application.
