#!/usr/bin/env python3
"""
Batch test multiple songs to understand alignment patterns.
This will help us see if our alignment detection is working across different tracks.
"""

import sys
import json
import sqlite3
import re
from pathlib import Path
from onset_detection import detect_vocal_onsets

def get_songs_with_synced_lyrics(db_path, limit=5):
    """Get songs that have both synced lyrics and vocal files."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, artist, synced_lyrics
        FROM songs
        WHERE synced_lyrics IS NOT NULL
        AND synced_lyrics != ''
        LIMIT ?
    """, (limit,))

    songs = cursor.fetchall()
    conn.close()

    return [{"id": row[0], "title": row[1], "artist": row[2], "synced_lyrics": row[3]} for row in songs]

def parse_first_lyric_time(synced_lyrics):
    """Extract the timestamp of the first lyric line."""
    lines = synced_lyrics.strip().split('\n')

    for line in lines:
        # Match LRC format: [mm:ss.xx] or [mm:ss]
        match = re.match(r'\[(\d{1,2}):(\d{2})(?:\.(\d{2}))?\]\s*(.*)', line.strip())
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            centiseconds = int(match.group(3)) if match.group(3) else 0
            text = match.group(4).strip()

            if text:  # First line with actual lyrics
                timestamp = minutes * 60 + seconds + centiseconds / 100
                return {"time": timestamp, "text": text}

    return None

def analyze_song_alignment(song, library_path):
    """Analyze alignment for a single song."""
    vocal_path = library_path / song["id"] / "vocals.mp3"

    if not vocal_path.exists():
        return {"error": f"Vocal file not found: {vocal_path}"}

    # Get expected timing from synced lyrics
    first_lyric = parse_first_lyric_time(song["synced_lyrics"])
    if not first_lyric:
        return {"error": "Could not parse synced lyrics"}

    # Detect actual vocal onset
    try:
        onset_results = detect_vocal_onsets(str(vocal_path), search_window=60.0)
        detected_time = onset_results["consensus"]["recommended_onset"]
        confidence = onset_results["consensus"]["confidence"]

        if detected_time is None:
            return {"error": "Could not detect vocal onset"}

        # Calculate alignment
        expected_time = first_lyric["time"]
        offset = detected_time - expected_time

        return {
            "song_info": {
                "title": song["title"],
                "artist": song["artist"],
                "id": song["id"]
            },
            "timing": {
                "expected_start": expected_time,
                "detected_start": detected_time,
                "offset_needed": offset,
                "first_lyric_text": first_lyric["text"]
            },
            "detection": {
                "confidence": confidence,
                "methods_agreed": onset_results["consensus"]["methods_agreed"],
                "std_dev": onset_results["consensus"]["onset_std_dev"]
            }
        }

    except Exception as e:
        return {"error": f"Analysis failed: {str(e)}"}

def create_alignment_report(results):
    """Create a human-readable alignment report."""

    report = """# Lyric Alignment Analysis Report

## Summary

This report analyzes how well our synced lyrics align with the actual vocal timing in audio tracks.

| Song | Artist | Expected Start | Detected Start | Offset Needed | Confidence |
|------|--------|----------------|----------------|---------------|------------|
"""

    successful_analyses = []
    failed_analyses = []

    for result in results:
        if "error" in result:
            failed_analyses.append(result)
            continue

        successful_analyses.append(result)

        song = result["song_info"]
        timing = result["timing"]
        detection = result["detection"]

        # Format the table row
        offset_str = f"{timing['offset_needed']:+.2f}s"
        report += f"| {song['title'][:20]} | {song['artist'][:15]} | {timing['expected_start']:.2f}s | {timing['detected_start']:.2f}s | {offset_str} | {detection['confidence']} |\n"

    # Add detailed analysis
    report += f"\n## Detailed Analysis\n\n"
    report += f"**Total songs analyzed:** {len(results)}\n"
    report += f"**Successful analyses:** {len(successful_analyses)}\n"
    report += f"**Failed analyses:** {len(failed_analyses)}\n\n"

    if successful_analyses:
        offsets = [r["timing"]["offset_needed"] for r in successful_analyses]
        avg_offset = sum(offsets) / len(offsets)

        report += f"**Average offset needed:** {avg_offset:.2f}s\n"
        report += f"**Offset range:** {min(offsets):.2f}s to {max(offsets):.2f}s\n\n"

        # Categorize results
        small_offsets = [o for o in offsets if abs(o) <= 2.0]
        medium_offsets = [o for o in offsets if 2.0 < abs(o) <= 5.0]
        large_offsets = [o for o in offsets if abs(o) > 5.0]

        report += f"### Offset Distribution\n"
        report += f"- **Small offsets (≤2s):** {len(small_offsets)} songs\n"
        report += f"- **Medium offsets (2-5s):** {len(medium_offsets)} songs\n"
        report += f"- **Large offsets (>5s):** {len(large_offsets)} songs\n\n"

    # Add individual song details
    report += "## Individual Song Analysis\n\n"

    for i, result in enumerate(successful_analyses, 1):
        song = result["song_info"]
        timing = result["timing"]
        detection = result["detection"]

        report += f"### {i}. {song['title']} - {song['artist']}\n\n"
        report += f"- **Expected vocal start:** {timing['expected_start']:.2f}s\n"
        report += f"- **Detected vocal start:** {timing['detected_start']:.2f}s\n"
        report += f"- **Offset needed:** {timing['offset_needed']:+.2f}s\n"
        report += f"- **First lyric:** \"{timing['first_lyric_text']}\"\n"
        report += f"- **Detection confidence:** {detection['confidence']}\n"
        report += f"- **Methods in agreement:** {detection['methods_agreed']}/4\n\n"

        if timing["offset_needed"] > 0:
            report += f"  📊 **Vocals start {timing['offset_needed']:.2f}s LATER than lyrics expect**\n"
        elif timing["offset_needed"] < 0:
            report += f"  📊 **Vocals start {abs(timing['offset_needed']):.2f}s EARLIER than lyrics expect**\n"
        else:
            report += f"  ✅ **Perfect alignment!**\n"
        report += "\n"

    # Add failed analyses
    if failed_analyses:
        report += "## Failed Analyses\n\n"
        for result in failed_analyses:
            report += f"- **Error:** {result['error']}\n"

    return report

def main():
    print("🎤 Batch Lyric Alignment Analysis")
    print("=" * 50)

    # Paths
    db_path = "/home/spencer/code/open-karaoke-studio/backend/karaoke.db"
    library_path = Path("/home/spencer/code/open-karaoke-studio/karaoke_library")

    # Get songs to test
    num_songs = 5
    if len(sys.argv) > 1:
        num_songs = int(sys.argv[1])

    print(f"📋 Getting {num_songs} songs with synced lyrics...")
    songs = get_songs_with_synced_lyrics(db_path, num_songs)

    if not songs:
        print("❌ No songs found with synced lyrics")
        return 1

    print(f"✅ Found {len(songs)} songs to analyze")

    # Analyze each song
    results = []
    for i, song in enumerate(songs, 1):
        print(f"\n🎵 [{i}/{len(songs)}] Analyzing: {song['title']} - {song['artist']}")

        result = analyze_song_alignment(song, library_path)
        results.append(result)

        if "error" in result:
            print(f"❌ {result['error']}")
        else:
            timing = result["timing"]
            print(f"✅ Expected: {timing['expected_start']:.2f}s, Detected: {timing['detected_start']:.2f}s, Offset: {timing['offset_needed']:+.2f}s")

    # Generate report
    print(f"\n📊 Generating alignment report...")
    report = create_alignment_report(results)

    # Save report
    output_file = "batch_alignment_analysis.md"
    with open(output_file, 'w') as f:
        f.write(report)

    print(f"💾 Report saved to: {output_file}")

    # Save raw data
    json_file = "batch_alignment_data.json"
    with open(json_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"💾 Raw data saved to: {json_file}")
    print(f"\n✅ Analysis complete! Check {output_file} for results.")

    return 0

if __name__ == "__main__":
    sys.exit(main())
