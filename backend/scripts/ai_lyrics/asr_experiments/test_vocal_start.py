#!/usr/bin/env python3
"""
Detect the start of vocals in an isolated vocal track.
This script is specifically designed for aligning synced lyrics with vocal timing.
"""

import sys
import json
from pathlib import Path
from faster_whisper import WhisperModel

def detect_vocal_start(audio_path, min_word_length=2, ignore_filler_words=True):
    """
    Detect the start of meaningful vocals in an audio track.
    
    Args:
        audio_path: Path to the audio file
        min_word_length: Minimum length for a word to be considered meaningful
        ignore_filler_words: Skip common filler words like "oh", "ah", "um"

    Returns:
        dict: Results including vocal start time and analysis
    """

    print(f"🔍 Analyzing vocal start in: {audio_path}")
    print("=" * 50)
    
    # Common filler words to potentially ignore
    filler_words = {
        'oh', 'ah', 'uh', 'um', 'mm', 'hmm', 'ooh', 'aah', 'yeah', 'hey'
    }

    # Initialize model
    print("Loading Whisper model...")
    model = WhisperModel("small", device="cpu", compute_type="int8")
    
    # Transcribe
    print("Transcribing and analyzing...")
    segments, info = model.transcribe(
        audio_path, 
        beam_size=5,
        word_timestamps=True,
        language="en"
    )
    
    # Analyze results
    results = {
        "audio_file": str(audio_path),
        "duration": info.duration,
        "language": info.language,
        "analysis": {
            "first_sound_time": None,
            "first_word_time": None,
            "first_meaningful_word_time": None,
            "first_word": None,
            "first_meaningful_word": None,
            "all_early_words": [],
            "recommended_start_time": None
        }
    }
    
    early_words = []  # Words in the first 10 seconds
    
    for segment in segments:
        if hasattr(segment, 'words') and segment.words:
            for word in segment.words:
                word_text = word.word.strip().lower()
                word_clean = word_text.strip('.,!?;:()[]{}"\'-')
                
                # Collect words from first 10 seconds for analysis
                if word.start <= 10.0:
                    word_info = {
                        "word": word.word.strip(),
                        "start": word.start,
                        "end": word.end,
                        "probability": word.probability,
                        "is_filler": word_clean in filler_words,
                        "is_short": len(word_clean) < min_word_length
                    }
                    early_words.append(word_info)

                    # Track first sound
                    if results["analysis"]["first_sound_time"] is None:
                        results["analysis"]["first_sound_time"] = word.start
                        results["analysis"]["first_word"] = word.word.strip()
                        results["analysis"]["first_word_time"] = word.start

                    # Track first meaningful word
                    if (results["analysis"]["first_meaningful_word_time"] is None and
                        len(word_clean) >= min_word_length and
                        (not ignore_filler_words or word_clean not in filler_words)):

                        results["analysis"]["first_meaningful_word_time"] = word.start
                        results["analysis"]["first_meaningful_word"] = word.word.strip()
    
    results["analysis"]["all_early_words"] = early_words

    # Determine recommended start time
    if results["analysis"]["first_meaningful_word_time"] is not None:
        results["analysis"]["recommended_start_time"] = results["analysis"]["first_meaningful_word_time"]
        recommendation_reason = "first meaningful word"
    elif results["analysis"]["first_word_time"] is not None:
        results["analysis"]["recommended_start_time"] = results["analysis"]["first_word_time"]
        recommendation_reason = "first detected word"
    else:
        results["analysis"]["recommended_start_time"] = 0.0
        recommendation_reason = "no words detected"
    
    # Print analysis
    print(f"🎵 Audio duration: {info.duration:.2f} seconds")
    print(f"🗣️  Language detected: {info.language}")
    print()
    
    print("📊 VOCAL START ANALYSIS")
    print("-" * 30)

    if results["analysis"]["first_sound_time"]:
        print(f"First sound detected: {results['analysis']['first_sound_time']:.2f}s")
        print(f"First word: '{results['analysis']['first_word']}'")
        print()

    if early_words:
        print("Early words (first 10 seconds):")
        for i, word in enumerate(early_words[:10]):  # Show first 10 words
            flags = []
            if word["is_filler"]:
                flags.append("filler")
            if word["is_short"]:
                flags.append("short")

            flag_text = f" [{', '.join(flags)}]" if flags else ""
            print(f"  {i+1:2d}. '{word['word']}' at {word['start']:.2f}s{flag_text}")

        if len(early_words) > 10:
            print(f"  ... and {len(early_words) - 10} more words")
        print()

    print("🎯 RECOMMENDATION")
    print("-" * 20)
    print(f"Recommended vocal start: {results['analysis']['recommended_start_time']:.2f}s")
    print(f"Reason: {recommendation_reason}")

    if results["analysis"]["first_meaningful_word"]:
        print(f"Based on word: '{results['analysis']['first_meaningful_word']}'")

    # Save results
    output_file = Path(audio_path).stem + "_vocal_start_analysis.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Analysis saved to: {output_file}")
    
    return results

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_vocal_start.py <audio_file> [options]")
        print("Options:")
        print("  --include-fillers  Include filler words (oh, ah, um) in analysis")
        print("  --min-length N     Minimum word length to consider meaningful (default: 2)")
        print()
        print("Example: python test_vocal_start.py /path/to/vocals.mp3")
        sys.exit(1)
    
    audio_path = sys.argv[1]
    
    # Parse options
    include_fillers = "--include-fillers" in sys.argv
    ignore_fillers = not include_fillers

    min_length = 2
    if "--min-length" in sys.argv:
        idx = sys.argv.index("--min-length")
        if idx + 1 < len(sys.argv):
            min_length = int(sys.argv[idx + 1])

    if not Path(audio_path).exists():
        print(f"❌ Error: Audio file not found: {audio_path}")
        sys.exit(1)
    
    try:
        results = detect_vocal_start(
            audio_path,
            min_word_length=min_length,
            ignore_filler_words=ignore_fillers
        )
        
        recommended_time = results["analysis"]["recommended_start_time"]
        print(f"\n✅ Analysis complete! Recommended vocal start: {recommended_time:.2f}s")

    except Exception as e:
        print(f"❌ Error analyzing audio: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
