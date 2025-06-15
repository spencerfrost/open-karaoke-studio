#!/usr/bin/env python3
"""
Fix NULL durations in the database by extracting duration from audio files.
"""

import sqlite3
import librosa
from pathlib import Path

def extract_audio_duration(audio_path):
    """Extract duration from audio file using librosa"""
    try:
        duration = librosa.get_duration(path=str(audio_path))
        return float(duration)
    except Exception as e:
        print(f"Failed to extract duration from {audio_path}: {e}")
        return None

def fix_null_durations():
    """Fix songs with NULL duration by extracting from audio files"""
    # Connect to database
    conn = sqlite3.connect('backend/karaoke.db')
    cursor = conn.cursor()
    
    # Get songs with NULL duration
    cursor.execute("SELECT id, title, artist FROM songs WHERE duration IS NULL")
    songs_without_duration = cursor.fetchall()
    
    print(f"Found {len(songs_without_duration)} songs with NULL duration")
    
    updated_count = 0
    for song_id, title, artist in songs_without_duration:
        # Check if original.mp3 exists
        audio_path = Path(f"karaoke_library/{song_id}/original.mp3")
        
        if audio_path.exists():
            print(f"Processing: {artist} - {title}")
            duration = extract_audio_duration(audio_path)
            
            if duration:
                # Update database
                cursor.execute("UPDATE songs SET duration = ? WHERE id = ?", (duration, song_id))
                print(f"  ✅ Updated duration: {duration:.1f}s")
                updated_count += 1
            else:
                print(f"  ❌ Failed to extract duration")
        else:
            print(f"  ❌ Audio file not found: {audio_path}")
    
    # Commit changes
    conn.commit()
    conn.close()
    
    print(f"\n✅ Updated {updated_count} songs with duration")

if __name__ == "__main__":
    fix_null_durations()
