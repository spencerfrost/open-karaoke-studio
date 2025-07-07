#!/usr/bin/env python3
"""
Sync Thumbnails Script

This script updates the database with thumbnail paths for songs that have
thumbnail files on disk but missing thumbnail_path in the database.
"""
import os
import sys
from pathlib import Path

# Add the backend app to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.db import database
from app.services.file_service import FileService
from app.config import get_config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def sync_thumbnails():
    """Sync thumbnail files with database"""

    # Initialize database and services
    database.init_db()
    file_service = FileService()

    logger.info("Starting thumbnail sync...")

    # Get all songs
    songs = with get_db_session() as session:
    repo = SongRepository(session)
    songs = repo.fetch_all()
    logger.info(f"Found {len(songs)} songs in database")

    updated_count = 0
    found_count = 0

    for song in songs:
        # Check if song already has thumbnail_path in database
        if song.thumbnail_path:
            logger.debug(
                f"Song {song.id} already has thumbnail_path: {song.thumbnail_path}"
            )
            continue

        # Check if thumbnail files exist on disk
        song_dir = file_service.get_song_directory(song.id)

        # Check for different thumbnail formats (prioritize webp for better compression)
        thumbnail_formats = ["thumbnail.webp", "thumbnail.jpg", "thumbnail.png"]
        thumbnail_found = None

        for format_name in thumbnail_formats:
            thumb_path = song_dir / format_name
            if thumb_path.exists():
                thumbnail_found = format_name
                found_count += 1
                logger.info(
                    f"Found thumbnail for {song.id} ({song.title}): {format_name}"
                )
                break

        if thumbnail_found:
            # Update database with relative path
            relative_path = f"{song.id}/{thumbnail_found}"
            success = repo.update(song.id, relative_path)

            if success:
                updated_count += 1
                logger.info(f"✅ Updated {song.id}: {relative_path}")
            else:
                logger.error(f"❌ Failed to update {song.id}")
        else:
            logger.debug(f"No thumbnail found for {song.id} ({song.title})")

    logger.info(
        f"""
🎯 Thumbnail Sync Complete!
📁 Songs with thumbnail files: {found_count}
💾 Database records updated: {updated_count}
"""
    )

    return updated_count, found_count


if __name__ == "__main__":
    print("🔄 Syncing thumbnails with database...")
    updated, found = sync_thumbnails()

    if updated > 0:
        print(f"✅ Successfully updated {updated} songs with thumbnail paths!")
        print("🚀 Thumbnails should now appear on the frontend!")
    else:
        print("⚠️  No thumbnail paths were updated. Check the logs above for details.")
