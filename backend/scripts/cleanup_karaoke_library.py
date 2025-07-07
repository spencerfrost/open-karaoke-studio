#!/usr/bin/env python3
"""
Karaoke Library Cleanup Script for Open Karaoke Studio

This script identifies problematic entries (orphaned database entries, orphaned
filesystem directories, and songs missing essential MP3 files) and prompts the
user to delete them with detailed information about each item.

Usage:
    python cleanup_karaoke_library.py [options]

Options:
    --karaoke-lib PATH    Override karaoke library path
    --verbose, -v         Enable verbose output
    --dry-run            Show what would be deleted without making changes
    --auto-confirm       Auto-confirm all deletions (dangerous!)
"""

import argparse
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.config import get_config
from app.db.database import get_db_session
from app.repositories.song_repository import SongRepository
from app.services.file_service import FileService

# File extensions to check for thumbnails
THUMBNAIL_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]


class CleanupItem:
    """Represents an item that can be cleaned up."""

    def __init__(
        self, item_type: str, song_id: str, reason: str, details: Optional[Dict] = None
    ):
        self.item_type = item_type  # 'orphaned_db', 'orphaned_fs', 'missing_files'
        self.song_id = song_id
        self.reason = reason
        self.details = details or {}
        self.db_song = None
        self.fs_exists = False


class KaraokeLibraryCleanup:
    def __init__(self, karaoke_lib_path: Optional[str] = None, dry_run: bool = False):
        self.config = get_config()
        self.karaoke_lib_path = (
            Path(karaoke_lib_path)
            if karaoke_lib_path
            else Path(self.config.LIBRARY_DIR)
        )
        self.file_service = FileService(self.karaoke_lib_path)
        self.dry_run = dry_run

    def get_database_songs_info(self) -> Dict[str, Dict]:
        """Get all song information from the database."""
        try:
            with get_db_session() as session:
                repo = SongRepository(session)
            songs = repo.fetch_all()
            return {
                str(song.id): {
                    "song": song,
                    "title": song.title or "Unknown Title",
                    "artist": song.artist or "Unknown Artist",
                    "album": getattr(song, "album", None) or "Unknown Album",
                    "duration": getattr(song, "duration", None),
                    "file_size": getattr(song, "file_size", None),
                    "created_at": getattr(song, "created_at", None),
                }
                for song in songs
            }
        except Exception as e:
            print(f"Error fetching songs from database: {e}")
            return {}

    def get_filesystem_song_ids(self) -> Set[str]:
        """Get all song directory IDs from the filesystem."""
        if not self.karaoke_lib_path.exists():
            print(f"Karaoke library path does not exist: {self.karaoke_lib_path}")
            return set()

        filesystem_ids = set()
        for item in self.karaoke_lib_path.iterdir():
            if item.is_dir():
                filesystem_ids.add(item.name)

        return filesystem_ids

    def check_required_files(self, song_id: str) -> dict:
        """Check for required files in a song directory."""
        song_dir = self.karaoke_lib_path / song_id

        result = {
            "song_id": song_id,
            "directory_exists": song_dir.exists(),
            "original_mp3": False,
            "vocals_mp3": False,
            "instrumental_mp3": False,
            "thumbnail": False,
            "thumbnail_format": None,
            "metadata_json": False,
            "missing_files": [],
            "extra_files": [],
        }

        if not song_dir.exists():
            return result

        # Check required audio files
        original_path = song_dir / "original.mp3"
        vocals_path = song_dir / "vocals.mp3"
        instrumental_path = song_dir / "instrumental.mp3"
        metadata_path = song_dir / "metadata.json"

        result["original_mp3"] = original_path.exists()
        result["vocals_mp3"] = vocals_path.exists()
        result["instrumental_mp3"] = instrumental_path.exists()
        result["metadata_json"] = metadata_path.exists()

        # Track missing files
        if not result["original_mp3"]:
            result["missing_files"].append("original.mp3")
        if not result["vocals_mp3"]:
            result["missing_files"].append("vocals.mp3")
        if not result["instrumental_mp3"]:
            result["missing_files"].append("instrumental.mp3")

        # Check for thumbnail with any valid extension
        thumbnail_found = False
        for ext in THUMBNAIL_EXTENSIONS:
            thumbnail_path = song_dir / f"thumbnail{ext}"
            if thumbnail_path.exists():
                result["thumbnail"] = True
                result["thumbnail_format"] = ext[1:]  # Remove the dot
                thumbnail_found = True
                break

        if not thumbnail_found:
            result["missing_files"].append("thumbnail")

        # List all files in directory to identify extras
        try:
            all_files = [f.name for f in song_dir.iterdir() if f.is_file()]
            expected_files = {
                "original.mp3",
                "vocals.mp3",
                "instrumental.mp3",
                "metadata.json",
            }

            # Add the found thumbnail to expected files
            if result["thumbnail"]:
                expected_files.add(f"thumbnail.{result['thumbnail_format']}")

            extra_files = set(all_files) - expected_files
            result["extra_files"] = list(extra_files)

        except Exception as e:
            result["extra_files"] = [f"Error listing files: {e}"]

        return result

    def identify_cleanup_items(self) -> List[CleanupItem]:
        """Identify all items that need cleanup."""
        print("🔍 Analyzing karaoke library for cleanup items...")

        # Get data from both sources
        db_songs_info = self.get_database_songs_info()
        fs_song_ids = self.get_filesystem_song_ids()

        db_song_ids = set(db_songs_info.keys())

        print(f"📊 Found {len(db_song_ids)} songs in database")
        print(f"📊 Found {len(fs_song_ids)} directories in filesystem")

        cleanup_items = []

        # 1. Orphaned database entries (in DB but no directory)
        missing_directories = db_song_ids - fs_song_ids
        for song_id in missing_directories:
            song_info = db_songs_info[song_id]
            item = CleanupItem(
                item_type="orphaned_db",
                song_id=song_id,
                reason="Database entry exists but no filesystem directory found",
                details={
                    "title": song_info["title"],
                    "artist": song_info["artist"],
                    "album": song_info["album"],
                    "created_at": song_info["created_at"],
                    "duration": song_info["duration"],
                    "file_size": song_info["file_size"],
                },
            )
            item.db_song = song_info["song"]
            item.fs_exists = False
            cleanup_items.append(item)

        # 2. Orphaned filesystem directories (directory exists but no DB entry)
        orphaned_directories = fs_song_ids - db_song_ids
        for song_id in orphaned_directories:
            # Check what files exist in the directory
            file_check = self.check_required_files(song_id)

            item = CleanupItem(
                item_type="orphaned_fs",
                song_id=song_id,
                reason="Filesystem directory exists but no database entry found",
                details={
                    "directory_path": str(self.karaoke_lib_path / song_id),
                    "has_original": file_check["original_mp3"],
                    "has_vocals": file_check["vocals_mp3"],
                    "has_instrumental": file_check["instrumental_mp3"],
                    "has_thumbnail": file_check["thumbnail"],
                    "missing_files": file_check["missing_files"],
                    "extra_files": file_check["extra_files"],
                },
            )
            item.db_song = None
            item.fs_exists = True
            cleanup_items.append(item)

        # 3. Songs with missing essential MP3 files
        consistent_ids = db_song_ids & fs_song_ids
        for song_id in consistent_ids:
            file_check = self.check_required_files(song_id)

            # Check if any essential MP3 files are missing
            essential_missing = [
                f
                for f in file_check["missing_files"]
                if f in ["original.mp3", "vocals.mp3", "instrumental.mp3"]
            ]

            if essential_missing:
                song_info = db_songs_info[song_id]
                item = CleanupItem(
                    item_type="missing_files",
                    song_id=song_id,
                    reason=f'Missing essential MP3 files: {", ".join(essential_missing)}',
                    details={
                        "title": song_info["title"],
                        "artist": song_info["artist"],
                        "album": song_info["album"],
                        "missing_files": essential_missing,
                        "has_thumbnail": file_check["thumbnail"],
                        "extra_files": file_check["extra_files"],
                        "created_at": song_info["created_at"],
                    },
                )
                item.db_song = song_info["song"]
                item.fs_exists = True
                cleanup_items.append(item)

        print(f"🚨 Found {len(cleanup_items)} items requiring cleanup:")
        print(f"   - {len(missing_directories)} orphaned database entries")
        print(f"   - {len(orphaned_directories)} orphaned filesystem directories")
        print(
            f"   - {len([i for i in cleanup_items if i.item_type == 'missing_files'])} songs with missing MP3 files"
        )

        return cleanup_items

    def format_cleanup_item_info(self, item: CleanupItem) -> str:
        """Format detailed information about a cleanup item."""
        lines = []
        lines.append(f"🎵 Song ID: {item.song_id}")
        lines.append(f"❗ Issue: {item.reason}")
        lines.append(f"📂 Type: {item.item_type.replace('_', ' ').title()}")

        if item.item_type == "orphaned_db":
            lines.append(f"🎤 Title: {item.details['title']}")
            lines.append(f"👤 Artist: {item.details['artist']}")
            lines.append(f"💿 Album: {item.details['album']}")
            if item.details["created_at"]:
                lines.append(f"📅 Created: {item.details['created_at']}")
            if item.details["duration"]:
                lines.append(f"⏱️  Duration: {item.details['duration']}s")
            if item.details["file_size"]:
                lines.append(f"💾 Size: {item.details['file_size']} bytes")
            lines.append("🗂️  Action: Will delete database entry")

        elif item.item_type == "orphaned_fs":
            lines.append(f"📁 Directory: {item.details['directory_path']}")
            lines.append(
                f"🎵 Has original.mp3: {'✅' if item.details['has_original'] else '❌'}"
            )
            lines.append(
                f"🎤 Has vocals.mp3: {'✅' if item.details['has_vocals'] else '❌'}"
            )
            lines.append(
                f"🎼 Has instrumental.mp3: {'✅' if item.details['has_instrumental'] else '❌'}"
            )
            lines.append(
                f"🖼️  Has thumbnail: {'✅' if item.details['has_thumbnail'] else '❌'}"
            )
            if item.details["missing_files"]:
                lines.append(f"❌ Missing: {', '.join(item.details['missing_files'])}")
            if item.details["extra_files"]:
                lines.append(
                    f"📄 Extra files: {', '.join(item.details['extra_files'])}"
                )
            lines.append("🗂️  Action: Will delete entire directory")

        elif item.item_type == "missing_files":
            lines.append(f"🎤 Title: {item.details['title']}")
            lines.append(f"👤 Artist: {item.details['artist']}")
            lines.append(f"💿 Album: {item.details['album']}")
            lines.append(f"❌ Missing MP3s: {', '.join(item.details['missing_files'])}")
            lines.append(
                f"🖼️  Has thumbnail: {'✅' if item.details['has_thumbnail'] else '❌'}"
            )
            if item.details["extra_files"]:
                lines.append(
                    f"📄 Extra files: {', '.join(item.details['extra_files'])}"
                )
            if item.details["created_at"]:
                lines.append(f"📅 Created: {item.details['created_at']}")
            lines.append("🗂️  Action: Will delete both database entry and directory")

        return "\n".join(lines)

    def prompt_user_for_deletion(self, item: CleanupItem) -> object:
        """Prompt user whether to delete this item."""
        print("\n" + "=" * 80)
        print(self.format_cleanup_item_info(item))
        print("=" * 80)

        while True:
            response = (
                input(
                    "\n🗑️  Delete this item? (y/n/s/q) [y=yes, n=no, s=skip all remaining, q=quit]: "
                )
                .lower()
                .strip()
            )

            if response in ["y", "yes"]:
                return True
            elif response in ["n", "no"]:
                return False
            elif response in ["s", "skip"]:
                return "skip_all"
            elif response in ["q", "quit"]:
                return "quit"
            else:
                print(
                    "❓ Please enter 'y' (yes), 'n' (no), 's' (skip all), or 'q' (quit)"
                )

    def delete_cleanup_item(self, item: CleanupItem) -> bool:
        """Delete the specified cleanup item."""
        success = True

        try:
            from app.db.database import get_db_session
            from app.repositories.song_repository import SongRepository

            # ...existing code...
            if item.item_type == "orphaned_db":
                # Delete database entry only
                if self.dry_run:
                    print(
                        f"🔄 [DRY RUN] Would delete database entry for song ID: {item.song_id}"
                    )
                else:
                    with get_db_session() as session:
                        repo = SongRepository(session)
                        if repo.delete(item.song_id):
                            print(
                                f"✅ Deleted database entry for song ID: {item.song_id}"
                            )
                        else:
                            print(
                                f"❌ Failed to delete database entry for {item.song_id}"
                            )
                            success = False

            elif item.item_type == "orphaned_fs":
                # Delete filesystem directory only
                directory_path = self.karaoke_lib_path / item.song_id
                if self.dry_run:
                    print(f"🔄 [DRY RUN] Would delete directory: {directory_path}")
                else:
                    if directory_path.exists():
                        shutil.rmtree(directory_path)
                        print(f"✅ Deleted directory: {directory_path}")
                    else:
                        print(f"⚠️  Directory already deleted: {directory_path}")

            elif item.item_type == "missing_files":
                # Delete both database entry and filesystem directory
                directory_path = self.karaoke_lib_path / item.song_id

                # Delete database entry
                if self.dry_run:
                    print(
                        f"🔄 [DRY RUN] Would delete database entry for song ID: {item.song_id}"
                    )
                    print(f"🔄 [DRY RUN] Would delete directory: {directory_path}")
                else:
                    with get_db_session() as session:
                        repo = SongRepository(session)
                        if repo.delete(item.song_id):
                            print(
                                f"✅ Deleted database entry for song ID: {item.song_id}"
                            )
                        else:
                            print(
                                f"❌ Failed to delete database entry for {item.song_id}"
                            )
                            success = False

                    # Delete filesystem directory
                    if directory_path.exists():
                        shutil.rmtree(directory_path)
                        print(f"✅ Deleted directory: {directory_path}")
                    else:
                        print(f"⚠️  Directory already deleted: {directory_path}")

        except Exception as e:
            print(f"❌ Error deleting item {item.song_id}: {e}")
            success = False

        return success

    def run_cleanup(self, auto_confirm: bool = False) -> None:
        """Run the interactive cleanup process."""
        print("🧹 Starting Karaoke Library Cleanup")
        print(f"📁 Library Path: {self.karaoke_lib_path}")
        if self.dry_run:
            print("🔄 DRY RUN MODE - No changes will be made")
        print()

        # Identify cleanup items
        cleanup_items = self.identify_cleanup_items()

        if not cleanup_items:
            print("🎉 No cleanup items found! Your library is in good shape.")
            return

        print(f"\n🚨 Found {len(cleanup_items)} items that may need cleanup.")

        if auto_confirm:
            print("⚠️  AUTO-CONFIRM MODE - All items will be deleted without prompting!")
            response = input("Continue? (y/N): ").lower().strip()
            if response not in ["y", "yes"]:
                print("Aborted.")
                return

        # Process each item
        deleted_count = 0
        skipped_count = 0

        for i, item in enumerate(cleanup_items, 1):
            print(f"\n📋 Processing item {i}/{len(cleanup_items)}")

            if auto_confirm:
                should_delete = True
            else:
                should_delete = self.prompt_user_for_deletion(item)

            if should_delete == "skip_all":
                print("⏭️  Skipping all remaining items.")
                skipped_count += len(cleanup_items) - i + 1
                break
            elif should_delete == "quit":
                print("🚪 Quitting cleanup.")
                skipped_count += len(cleanup_items) - i + 1
                break
            elif should_delete is True:
                if self.delete_cleanup_item(item):
                    deleted_count += 1
                else:
                    print(f"⚠️  Failed to delete item {item.song_id}")
            else:
                skipped_count += 1
                print(f"⏭️  Skipped item {item.song_id}")

        # Summary
        print("\n" + "=" * 80)
        print("🏁 CLEANUP SUMMARY")
        print("=" * 80)
        print(f"✅ Items deleted: {deleted_count}")
        print(f"⏭️  Items skipped: {skipped_count}")
        print(f"🔍 Total items found: {len(cleanup_items)}")

        if self.dry_run:
            print("\n🔄 This was a DRY RUN - no actual changes were made.")
        elif deleted_count > 0:
            print(
                f"\n🎉 Successfully cleaned up {deleted_count} items from your karaoke library!"
            )

        print(
            "\n💡 Tip: Run the data integrity check script again to verify the cleanup."
        )


def main():
    parser = argparse.ArgumentParser(
        description="Clean up karaoke library by removing orphaned and problematic entries"
    )
    parser.add_argument("--karaoke-lib", help="Override karaoke library path")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without making changes",
    )
    parser.add_argument(
        "--auto-confirm",
        action="store_true",
        help="Auto-confirm all deletions (dangerous!)",
    )

    args = parser.parse_args()

    # Initialize cleanup manager
    cleanup = KaraokeLibraryCleanup(args.karaoke_lib, args.dry_run)

    try:
        cleanup.run_cleanup(args.auto_confirm)
    except KeyboardInterrupt:
        print("\n\n⚠️  Cleanup interrupted by user.")
        return 1
    except Exception as e:
        print(f"\n❌ Error during cleanup: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
