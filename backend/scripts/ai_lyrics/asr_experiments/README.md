# AI Lyrics Generation Experiments

This directory contains experimental scripts for generating AI-powered lyrics from isolated vocal tracks using state-of-the-art Automatic Speech Recognition (ASR) models. The primary focus is experimenting with and comparing different ASR models to determine which provides the best transcription quality and timestamp accuracy for karaoke applications.

## Project Goals

This project aims to experiment with and evaluate ASR models for generating AI lyrics in the Open Karaoke Studio:

1. **ASR Model Comparison**: Test and compare multiple state-of-the-art ASR models (Whisper, Faster Whisper, Insanely Fast Whisper, etc.)
2. **Timestamp Accuracy**: Evaluate word-level and phrase-level timestamp precision across different models
3. **Transcription Quality**: Assess transcription accuracy on isolated vocal tracks with minimal background noise
4. **Performance Analysis**: Compare processing speed, memory usage, and computational requirements
5. **Output Format Evaluation**: Analyze the native output formats and determine optimal data structures
6. **Integration Preparation**: Identify the best model(s) for seamless integration with the main karaoke application

The input will be high-quality isolated vocal tracks from our existing AI separation pipeline. The goal is to find the optimal ASR model that provides both accurate transcriptions and precise word-level timestamps for synchronized and bouncing ball style karaoke lyrics.

## Setup

Install the required packages for ASR model testing and comparison:

```bash
# Primary ASR models to test
pip install faster-whisper           # Faster Whisper (CT2-optimized)
pip install openai-whisper          # Original OpenAI Whisper
pip install insanely-fast-whisper   # Insanely Fast Whisper (HF Transformers)

# Alternative/additional models
pip install transformers torch       # For Hugging Face models
pip install speechrecognition       # For comparison with other ASR engines

# Audio processing utilities
pip install librosa soundfile

# Analysis and comparison tools
pip install pandas matplotlib seaborn
pip install nltk spacy              # For text analysis
pip install jiwer                   # For WER (Word Error Rate) calculation
```

## Experimental Scripts

1. **`test_faster_whisper.py`** - Basic faster-whisper test with word-level timestamps
2. **`test_whisper.py`** - Original OpenAI Whisper implementation test
3. **`test_insanely_fast_whisper.py`** - Insanely Fast Whisper implementation test
4. **`compare_models.py`** - Compare all ASR models side-by-side with metrics
5. **`benchmark_performance.py`** - Performance benchmarking (speed, memory, accuracy)
6. **`analyze_timestamps.py`** - Deep analysis of timestamp accuracy and precision
7. **`generate_lyrics.py`** - Full lyrics generation pipeline using best model
8. **`format_converter.py`** - Convert between different output formats (LRC, JSON, etc.)

## Quick Start

```bash
# Test individual ASR models
python test_faster_whisper.py path/to/vocals.mp3
python test_whisper.py path/to/vocals.mp3
python test_insanely_fast_whisper.py path/to/vocals.mp3

# Compare all models side-by-side
python compare_models.py path/to/vocals.mp3

# Benchmark performance across models
python benchmark_performance.py path/to/vocals.mp3

# Analyze timestamp accuracy in detail
python analyze_timestamps.py path/to/vocals.mp3

# Generate final lyrics using best model
python generate_lyrics.py path/to/vocals.mp3 --output lyrics.lrc
```

## Key Features

- **High-Quality Transcription**: Leverages faster-whisper for accurate speech-to-text conversion
- **Precise Timing**: Word-level and line-level timestamp generation for karaoke synchronization
- **Isolated Vocal Processing**: Optimized for AI-separated vocal tracks with minimal background noise
- **Multiple Output Formats**: Support for LRC, JSON, and custom timing formats
- **Quality Assessment**: Built-in tools to evaluate and improve transcription accuracy
- **Integration Ready**: Designed for seamless integration with the Open Karaoke Studio pipeline

## Output Formats

- **LRC Files**: Standard lyric files with line-level timing `[mm:ss.xx]`
- **Word Timing JSON**: Detailed word-by-word timing for bouncing ball effects
- **Synchronized Text**: Plain text with embedded timing markers
- **Karaoke Studio Format**: Custom format optimized for the main application

For detailed implementation instructions, see `IMPLEMENTATION_GUIDE.md`.
