#!/usr/bin/env python3
"""
Script to fix NULL duration values in songs by fetching duration from YouTube
"""

import json
import logging
import sqlite3
import sys
from pathlib import Path

import yt_dlp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_youtube_duration(video_id):
    """Get duration from YouTube for a video ID"""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            return info.get("duration")
    except Exception as e:
        logger.error(f"Error fetching YouTube info for {video_id}: {e}")
        return None

def fix_null_durations():
    """Fix songs with NULL duration by fetching duration from YouTube"""
    
    # Connect to database
    db_path = Path(__file__).parent / "backend" / "karaoke.db"
    if not db_path.exists():
        logger.error(f"Database not found at {db_path}")
        return
        
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Find songs with NULL duration that have video_id
        cursor.execute("SELECT id, title, video_id FROM songs WHERE duration IS NULL AND video_id IS NOT NULL")
        null_duration_songs = cursor.fetchall()
        
        logger.info(f"Found {len(null_duration_songs)} songs with NULL duration and video_id")
        
        fixed_count = 0
        failed_count = 0
        
        for song_id, title, video_id in null_duration_songs:
            try:
                if not video_id:
                    logger.warning(f"Song {title} has no video_id")
                    failed_count += 1
                    continue
                    
                # Get duration from YouTube
                duration = get_youtube_duration(video_id)
                
                if duration is not None:
                    # Update the song with the extracted duration
                    cursor.execute(
                        "UPDATE songs SET duration = ? WHERE id = ?",
                        (float(duration), song_id)
                    )
                    logger.info(f"Fixed duration for '{title}': {duration} seconds")
                    fixed_count += 1
                else:
                    logger.warning(f"Could not get duration for '{title}' (video_id: {video_id})")
                    failed_count += 1
                    
            except Exception as e:
                logger.error(f"Error processing song '{title}': {e}")
                failed_count += 1
        
        # Commit changes
        conn.commit()
        logger.info(f"Successfully fixed {fixed_count} songs, {failed_count} failed")
        
    except Exception as e:
        logger.error(f"Database error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_null_durations()
