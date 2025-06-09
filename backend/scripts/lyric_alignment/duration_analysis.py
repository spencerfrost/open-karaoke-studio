#!/usr/bin/env python3
"""
Duration-based analysis for lyric alignment.
Compare synced lyrics duration with vocal track duration to determine alignment strategy.
"""

import sys
import json
import re
from pathlib import Path
import librosa

def parse_synced_lyrics_duration(lyrics_content):
    """Parse synced lyrics and calculate total duration."""
    lines = lyrics_content.strip().split('\n')
    timestamps = []

    for line in lines:
        # Match LRC format: [mm:ss.xx] or [mm:ss]
        match = re.match(r'\[(\d{1,2}):(\d{2})(?:\.(\d{2}))?\]\s*(.*)', line.strip())
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            centiseconds = int(match.group(3)) if match.group(3) else 0
            text = match.group(4).strip()

            if text:  # Only count lines with actual lyrics
                timestamp = minutes * 60 + seconds + centiseconds / 100
                timestamps.append({
                    "time": timestamp,
                    "text": text
                })

    if not timestamps:
        return None

    return {
        "start_time": timestamps[0]["time"],
        "end_time": timestamps[-1]["time"],
        "duration": timestamps[-1]["time"] - timestamps[0]["time"],
        "total_lines": len(timestamps),
        "first_line": timestamps[0]["text"],
        "last_line": timestamps[-1]["text"]
    }

def analyze_audio_duration(audio_path):
    """Analyze audio file duration and basic properties."""
    print(f"🎵 Loading audio: {audio_path}")

    # Load audio file
    y, sr = librosa.load(audio_path)
    duration = librosa.get_duration(y=y, sr=sr)

    # Basic audio analysis
    rms_energy = librosa.feature.rms(y=y)[0]
    avg_energy = float(rms_energy.mean())

    # Find segments with significant energy (rough vocal detection)
    energy_threshold = avg_energy * 0.1  # 10% of average energy
    significant_frames = rms_energy > energy_threshold

    # Convert to time
    frame_times = librosa.frames_to_time(range(len(rms_energy)), sr=sr)
    significant_times = frame_times[significant_frames]

    first_significant_time = float(significant_times[0]) if len(significant_times) > 0 else 0.0
    last_significant_time = float(significant_times[-1]) if len(significant_times) > 0 else duration

    return {
        "total_duration": duration,
        "sample_rate": sr,
        "avg_energy": avg_energy,
        "first_significant_sound": first_significant_time,
        "last_significant_sound": last_significant_time,
        "significant_audio_duration": last_significant_time - first_significant_time
    }

def calculate_alignment_strategy(audio_info, lyrics_info):
    """Calculate the best alignment strategy based on duration analysis."""

    if not lyrics_info:
        return {
            "strategy": "onset_detection_only",
            "reason": "No synced lyrics provided",
            "search_window": min(10.0, audio_info["total_duration"] * 0.3)
        }

    audio_duration = audio_info["significant_audio_duration"]
    lyrics_duration = lyrics_info["duration"]
    lyrics_start = lyrics_info["start_time"]

    duration_diff = abs(audio_duration - lyrics_duration)
    duration_ratio = min(audio_duration, lyrics_duration) / max(audio_duration, lyrics_duration)

    print(f"\n📊 DURATION ANALYSIS")
    print(f"Audio duration (significant): {audio_duration:.2f}s")
    print(f"Lyrics duration: {lyrics_duration:.2f}s")
    print(f"Duration difference: {duration_diff:.2f}s")
    print(f"Duration ratio: {duration_ratio:.2f}")
    print(f"Lyrics start time: {lyrics_start:.2f}s")

    # Strategy determination
    if duration_diff <= 2.0 and duration_ratio >= 0.9:
        # Very close durations - high confidence alignment
        search_window = max(3.0, duration_diff + 1.0)
        strategy = "tight_window_onset"
        reason = "Durations match closely - search in narrow window"
        confidence = "high"

    elif duration_diff <= 5.0 and duration_ratio >= 0.8:
        # Reasonable duration match - moderate confidence
        search_window = max(5.0, duration_diff + 2.0)
        strategy = "medium_window_onset"
        reason = "Durations reasonably close - search in medium window"
        confidence = "medium"

    elif lyrics_start <= 3.0 and audio_info["first_significant_sound"] <= 3.0:
        # Both start early - might just be offset
        search_window = 8.0
        strategy = "early_start_alignment"
        reason = "Both audio and lyrics start early - likely just timing offset"
        confidence = "medium"

    else:
        # Large duration mismatch - need broader analysis
        search_window = min(15.0, audio_info["total_duration"] * 0.4)
        strategy = "broad_search"
        reason = "Duration mismatch - need broader search or ASR fallback"
        confidence = "low"

    return {
        "strategy": strategy,
        "reason": reason,
        "confidence": confidence,
        "search_window": search_window,
        "expected_offset_range": {
            "min": -search_window / 2,
            "max": search_window / 2
        },
        "duration_analysis": {
            "audio_duration": audio_duration,
            "lyrics_duration": lyrics_duration,
            "duration_diff": duration_diff,
            "duration_ratio": duration_ratio
        }
    }

def main():
    if len(sys.argv) < 2:
        print("Usage: python duration_analysis.py <audio_file> [lyrics_file]")
        print()
        print("Examples:")
        print("  python duration_analysis.py vocals.mp3 synced_lyrics.lrc")
        print("  python duration_analysis.py vocals.mp3")
        sys.exit(1)

    audio_path = sys.argv[1]
    lyrics_path = sys.argv[2] if len(sys.argv) > 2 else None

    if not Path(audio_path).exists():
        print(f"❌ Error: Audio file not found: {audio_path}")
        sys.exit(1)

    print(f"🔍 Duration Analysis for Lyric Alignment")
    print("=" * 50)

    try:
        # Analyze audio
        audio_info = analyze_audio_duration(audio_path)

        # Load and analyze lyrics if provided
        lyrics_info = None
        if lyrics_path:
            if not Path(lyrics_path).exists():
                print(f"❌ Warning: Lyrics file not found: {lyrics_path}")
            else:
                with open(lyrics_path, 'r', encoding='utf-8') as f:
                    lyrics_content = f.read()
                lyrics_info = parse_synced_lyrics_duration(lyrics_content)

                if lyrics_info:
                    print(f"\n📝 LYRICS ANALYSIS")
                    print(f"First line: '{lyrics_info['first_line']}'")
                    print(f"Lyrics start: {lyrics_info['start_time']:.2f}s")
                    print(f"Lyrics end: {lyrics_info['end_time']:.2f}s")
                    print(f"Total lines: {lyrics_info['total_lines']}")

        # Calculate alignment strategy
        strategy = calculate_alignment_strategy(audio_info, lyrics_info)

        print(f"\n🎯 RECOMMENDED STRATEGY")
        print(f"Strategy: {strategy['strategy']}")
        print(f"Confidence: {strategy['confidence']}")
        print(f"Search window: {strategy['search_window']:.1f}s")
        print(f"Reason: {strategy['reason']}")

        # Save results
        results = {
            "audio_file": str(audio_path),
            "lyrics_file": str(lyrics_path) if lyrics_path else None,
            "audio_info": audio_info,
            "lyrics_info": lyrics_info,
            "alignment_strategy": strategy
        }

        output_file = Path(audio_path).stem + "_duration_analysis.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\n💾 Analysis saved to: {output_file}")

    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
