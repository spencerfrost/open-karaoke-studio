#!/usr/bin/env python3
"""
Batch test multiple songs to understand alignment patterns.
This will help us see if our alignment detection is working across different tracks.
"""

import os
import sys
from pathlib import Path

# from onset_detection import detect_vocal_onsets


def get_songs_with_synced_lyrics(db_path=None, limit=5):
    """Fetch songs with synced lyrics using SongRepository."""
    from app.db.database import get_db_session
    from app.repositories.song_repository import SongRepository

    with get_db_session() as session:
        repo = SongRepository(session)
        all_songs = repo.fetch_all()
        songs = [s for s in all_songs if s.synced_lyrics]
        if limit:
            songs = songs[:limit]
    return songs


def main():
    db_path = None  # Not used with SongRepository, but kept for compatibility
    num_songs = 5
    songs = get_songs_with_synced_lyrics(db_path, num_songs)

    if not songs:
        print("❌ No songs found with synced lyrics")
        return 1

    print(f"✅ Found {len(songs)} songs to analyze")

    # TODO: Analysis and reporting logic is temporarily disabled.
    print("[INFO] Song analysis and report generation is currently disabled.\n")
    print(
        "[TODO] Implement analyze_song_alignment and create_alignment_report or restore this logic when ready."
    )
    # Uncomment and implement the following when ready:
    # results = []
    # for i, song in enumerate(songs, 1):
    #     print(f"\n🎵 [{i}/{len(songs)}] Analyzing: {song['title']} - {song['artist']}")
    #     result = analyze_song_alignment(song, library_path)
    #     results.append(result)
    #     if "error" in result:
    #         print(f"❌ {result['error']}")
    #     else:
    #         timing = result["timing"]
    #         print(
    #             f"✅ Expected: {timing['expected_start']:.2f}s, Detected: {timing['detected_start']:.2f}s, Offset: {timing['offset_needed']:+.2f}s"
    #         )
    # print(f"\n📊 Generating alignment report...")
    # report = create_alignment_report(results)
    # output_file = "batch_alignment_analysis.md"
    # with open(output_file, "w") as f:
    #     f.write(report)
    # print(f"💾 Report saved to: {output_file}")
    # json_file = "batch_alignment_data.json"
    # with open(json_file, "w") as f:
    #     json.dump(results, f, indent=2)
    # print(f"💾 Raw data saved to: {json_file}")
    # print(f"\n✅ Analysis complete! Check {output_file} for results.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
