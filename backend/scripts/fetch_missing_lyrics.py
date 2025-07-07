#!/usr/bin/env python3
"""
Fetch Missing Lyrics Script for Open Karaoke Studio

This script finds all songs missing lyrics in the database and attempts to fetch them
using the backend lyrics search endpoint, then saves them if found.

Usage:
    python fetch_missing_lyrics.py
"""
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import requests

from app.db.database import get_db_session
from app.db.models.song import DbSong
from app.repositories.song_repository import SongRepository
from app.services.lyrics_service import LyricsService

# Configuration
API_URL = (
    "http://localhost:5123/api/lyrics/search"  # Adjust if your backend runs elsewhere
)
SONG_PATCH_URL = (
    "http://localhost:5123/api/songs/{song_id}"  # PATCH endpoint to update song fields
)


def find_best_lyrics_result(results, target_durationMs):
    """
    Given a list of results and a target duration (ms), return the result with the closest duration.
    Assumes result['duration'] is in milliseconds or seconds (try both).
    """
    if not results:
        return None
    best = None
    best_diff = float("inf")
    for r in results:
        dur = r.get("duration")
        if dur is None:
            continue
        # Try both ms and s
        diff_ms = abs(dur - target_durationMs)
        diff_s = abs(dur * 1000 - target_durationMs)
        if diff_ms < best_diff:
            best = r
            best_diff = diff_ms
        if diff_s < best_diff:
            best = r
            best_diff = diff_s
    return best


def fetch_and_save_lyrics():
    with get_db_session() as session:
        repo = SongRepository(session)
        songs = repo.fetch_all()
    total = len(songs)
    missing = [s for s in songs if not s.synced_lyrics or not s.synced_lyrics.strip()]
    print(f"Found {len(missing)} songs missing lyrics out of {total} total.")

    for song in missing:
        params = {
            "track_name": song.title,
            "artist_name": song.artist,
            "album_name": song.album if song.album else None,
        }
        print(f"Searching lyrics for: {song.artist} - {song.title} (ID: {song.id})")
        try:
            resp = requests.get(API_URL, params=params, timeout=10)
            if resp.status_code == 200:
                results = resp.json()
                if results:
                    # Pick the result with the closest duration to our song
                    best_result = find_best_lyrics_result(results, song.durationMs)
                    if best_result:
                        plain_lyrics = (
                            best_result.get("plainLyrics")
                            or best_result.get("plain_lyrics")
                            or best_result.get("lyrics")
                            or best_result.get("text")
                        )
                        synced_lyrics = (
                            best_result.get("syncedLyrics")
                            or best_result.get("synced_lyrics")
                            or best_result.get("lrc")
                            or best_result.get("body")
                            or best_result.get("content")
                        )
                        if (plain_lyrics and str(plain_lyrics).strip()) or (
                            synced_lyrics and str(synced_lyrics).strip()
                        ):
                            print(f"  Found lyrics (closest duration), saving...")
                            payload = {}
                        if plain_lyrics and str(plain_lyrics).strip():
                            payload["lyrics"] = plain_lyrics
                        if synced_lyrics and str(synced_lyrics).strip():
                            payload["synced_lyrics"] = synced_lyrics
                            save_resp = requests.patch(
                                SONG_PATCH_URL.format(song_id=song.id),
                                json=payload,
                                timeout=10,
                            )
                            if save_resp.status_code == 200:
                                print(f"  Lyrics saved for {song.id}")
                            else:
                                print(
                                    f"  Failed to save lyrics: {save_resp.status_code} {save_resp.text}"
                                )
                        else:
                            print("  No usable lyrics in result.")
                    else:
                        print("  No usable lyrics in result.")
                else:
                    print("  No lyrics found.")
            else:
                print(f"  Search failed: {resp.status_code} {resp.text}")
        except Exception as e:
            print(f"  Error searching/saving lyrics: {e}")


if __name__ == "__main__":
    fetch_and_save_lyrics()
