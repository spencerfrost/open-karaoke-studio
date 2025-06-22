#!/usr/bin/env python3
"""
Duplicate Song Management Script for Open Karaoke Studio

This script identifies potential duplicate songs based on title similarity,
displays detailed information about each song's file integrity, and allows
interactive management of duplicates.

Usage:
    python manage_duplicates.py [options]

Options:
    --similarity-threshold FLOAT    Minimum similarity threshold (0.0-1.0, default: 0.8)
    --dry-run                      Show what would be deleted without actually deleting
    --auto-mode                    Automatically keep the most complete version
    --export-report FILE           Export duplicate groups to a file before processing
"""

import argparse
import json
import os
import shutil
import sys
from collections import defaultdict
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.config import get_config
from app.db.song_operations import delete_song, get_all_songs
from app.services.file_service import FileService

# Import the data integrity checker class
from check_data_integrity import DataIntegrityChecker


class DuplicateManager:
    def __init__(self, similarity_threshold: float = 0.8):
        self.config = get_config()
        self.karaoke_lib_path = Path(self.config.LIBRARY_DIR)
        self.file_service = FileService(str(self.karaoke_lib_path))
        self.integrity_checker = DataIntegrityChecker()
        self.similarity_threshold = similarity_threshold

    def normalize_title(self, title: str) -> str:
        """Normalize title for better comparison."""
        if not title:
            return ""

        # Convert to lowercase and remove common variations
        normalized = title.lower().strip()

        # Remove common prefixes/suffixes that might cause false differences
        remove_patterns = [
            " (official)",
            " (official video)",
            " (official music video)",
            " (lyrics)",
            " (lyric video)",
            " (audio)",
            " (hd)",
            " (hq)",
            " - official",
            " - lyrics",
            " - audio",
            " - video",
            " [official]",
            " [lyrics]",
            " [audio]",
            " [video]",
            " ft.",
            " feat.",
            " featuring",
        ]

        for pattern in remove_patterns:
            normalized = normalized.replace(pattern, "")

        # Replace multiple spaces with single space
        normalized = " ".join(normalized.split())

        return normalized.strip()

    def calculate_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles using sequence matching."""
        norm1 = self.normalize_title(title1)
        norm2 = self.normalize_title(title2)

        if not norm1 or not norm2:
            return 0.0

        return SequenceMatcher(None, norm1, norm2).ratio()

    def is_exact_duplicate(self, song1: Dict, song2: Dict) -> bool:
        """Check if two songs are exact duplicates (same normalized title and artist)."""
        norm_title1 = self.normalize_title(song1["title"])
        norm_title2 = self.normalize_title(song2["title"])
        norm_artist1 = self.normalize_title(song1["artist"])
        norm_artist2 = self.normalize_title(song2["artist"])

        return norm_title1 == norm_title2 and norm_artist1 == norm_artist2

    def find_duplicate_groups(self) -> List[List[Dict]]:
        """Find groups of potentially duplicate songs."""
        print("Fetching all songs from database...")

        try:
            songs = get_all_songs()
            print(f"Found {len(songs)} songs in database")
        except Exception as e:
            print(f"Error fetching songs: {e}")
            return []

        # Convert songs to dictionaries with additional info
        song_data = []
        for song in songs:
            # Ensure title and artist are always strings for normalization
            title = str(song.title) if song.title is not None else ""
            artist = str(song.artist) if song.artist is not None else ""
            song_dict = {
                "id": str(song.id),
                "title": title or "Unknown",
                "artist": artist or "Unknown",
                "normalized_title": self.normalize_title(title),
                "original_song": song,
            }
            song_data.append(song_dict)

        print("Analyzing titles for duplicates...")

        # Find duplicate groups
        processed = set()
        duplicate_groups = []

        for i, song1 in enumerate(song_data):
            if song1["id"] in processed:
                continue

            # Find all songs similar to this one
            similar_group = [song1]
            processed.add(song1["id"])

            for j, song2 in enumerate(song_data[i + 1 :], i + 1):
                if song2["id"] in processed:
                    continue

                similarity = self.calculate_similarity(song1["title"], song2["title"])

                if similarity >= self.similarity_threshold:
                    similar_group.append(song2)
                    processed.add(song2["id"])

            # Only add groups with more than one song
            if len(similar_group) > 1:
                # Mark if this is an exact duplicate group
                is_exact_group = all(
                    self.is_exact_duplicate(similar_group[0], song)
                    for song in similar_group[1:]
                )
                duplicate_groups.append(
                    {"songs": similar_group, "is_exact": is_exact_group}
                )

        print(f"Found {len(duplicate_groups)} groups of potential duplicates")
        return duplicate_groups

    def get_song_integrity_info(self, song_id: str) -> Dict:
        """Get detailed file integrity information for a song."""
        return self.integrity_checker.check_required_files(song_id)

    def calculate_completeness_score(self, integrity_info: Dict) -> Tuple[int, int]:
        """Calculate a completeness score for a song (score, max_score)."""
        score = 0
        max_score = (
            4  # original, vocals, instrumental, thumbnail (metadata.json is legacy)
        )

        if integrity_info["original_mp3"]:
            score += 1
        if integrity_info["vocals_mp3"]:
            score += 1
        if integrity_info["instrumental_mp3"]:
            score += 1
        if integrity_info["thumbnail"]:
            score += 1

        return score, max_score

    def format_song_info(self, song: Dict, integrity_info: Dict) -> str:
        """Format song information for display."""
        score, max_score = self.calculate_completeness_score(integrity_info)
        completeness_pct = (score / max_score) * 100

        # File status indicators (excluding metadata.json as it's legacy)
        status_indicators = []
        if not integrity_info["original_mp3"]:
            status_indicators.append("❌ No original.mp3")
        if not integrity_info["vocals_mp3"]:
            status_indicators.append("❌ No vocals.mp3")
        if not integrity_info["instrumental_mp3"]:
            status_indicators.append("❌ No instrumental.mp3")
        if not integrity_info["thumbnail"]:
            status_indicators.append("❌ No thumbnail")

        # Check for zero-byte files (this might indicate corruption)
        for file_type, size in integrity_info["file_sizes"].items():
            if isinstance(size, int) and size == 0:
                status_indicators.append(f"⚠️ {file_type} is 0 bytes (corrupted?)")

        # Extra files
        if integrity_info["extra_files"]:
            status_indicators.append(
                f"📁 Extra files: {', '.join(integrity_info['extra_files'])}"
            )

        status_text = (
            "\n    ".join(status_indicators)
            if status_indicators
            else "✅ All files present"
        )

        # File sizes - show actual bytes for small files to debug the 0MB issue
        size_info = []
        for file_type, size in integrity_info["file_sizes"].items():
            if isinstance(size, int):
                if size > 1024 * 1024:  # > 1MB, show in MB
                    size_mb = size / (1024 * 1024)
                    size_info.append(f"{file_type}: {size_mb:.1f}MB")
                elif size > 1024:  # > 1KB, show in KB
                    size_kb = size / 1024
                    size_info.append(f"{file_type}: {size_kb:.1f}KB")
                elif size > 0:  # Show bytes for small files
                    size_info.append(f"{file_type}: {size}B")
                else:
                    size_info.append(f"{file_type}: 0B")
            else:
                size_info.append(f"{file_type}: {size}")

        size_text = ", ".join(size_info) if size_info else "No size info"

        return f"""  ID: {song['id']}
  Title: {song['title']}
  Artist: {song['artist']}
  Completeness: {score}/{max_score} ({completeness_pct:.1f}%)
  File Sizes: {size_text}
  Issues: {status_text}"""

    def display_duplicate_group(self, group_data: Dict, group_num: int) -> List[Dict]:
        """Display a group of duplicate songs with detailed information."""
        group = group_data["songs"]
        is_exact = group_data["is_exact"]

        duplicate_type = "🎯 EXACT DUPLICATES" if is_exact else "⚠️ SIMILAR TITLES"

        print(f"\n{'='*80}")
        print(f"DUPLICATE GROUP {group_num} ({len(group)} songs) - {duplicate_type}")
        print(f"{'='*80}")

        # Get integrity info for all songs in the group
        songs_with_info = []
        for song in group:
            integrity_info = self.get_song_integrity_info(song["id"])
            score, max_score = self.calculate_completeness_score(integrity_info)
            songs_with_info.append(
                {
                    "song": song,
                    "integrity": integrity_info,
                    "score": score,
                    "max_score": max_score,
                }
            )

        # Sort by completeness score (highest first)
        songs_with_info.sort(key=lambda x: x["score"], reverse=True)

        # Display each song
        for i, song_info in enumerate(songs_with_info):
            print(
                f"\n[{i+1}] {self.format_song_info(song_info['song'], song_info['integrity'])}"
            )

        return songs_with_info

    def interactive_selection(self, songs_with_info: List[Dict]) -> List[str]:
        """Interactive selection of songs to delete."""
        while True:
            print(f"\nOptions:")
            print("  - Enter song numbers to DELETE (e.g., '2,3' or '2 3'): ")
            print("  - Enter 'k <number>' to KEEP only that song (delete others)")
            print("  - Enter 'a' to auto-select (keep most complete, delete others)")
            print("  - Enter 's' to skip this group")
            print("  - Enter 'q' to quit")

            choice = input("\nYour choice: ").strip().lower()

            if choice == "q":
                return None  # Signal to quit
            elif choice == "s":
                return []  # Skip this group
            elif choice == "a":
                # Auto-select: keep the first one (highest completeness), delete others
                return [info["song"]["id"] for info in songs_with_info[1:]]
            elif choice.startswith("k "):
                # Keep only the specified song
                try:
                    keep_num = int(choice[2:]) - 1
                    if 0 <= keep_num < len(songs_with_info):
                        to_delete = []
                        for i, info in enumerate(songs_with_info):
                            if i != keep_num:
                                to_delete.append(info["song"]["id"])
                        return to_delete
                    else:
                        print(
                            f"Invalid song number. Please choose 1-{len(songs_with_info)}"
                        )
                        continue
                except ValueError:
                    print("Invalid format. Use 'k <number>'")
                    continue
            else:
                # Parse song numbers to delete
                try:
                    # Handle both comma and space separated
                    if "," in choice:
                        delete_nums = [int(x.strip()) for x in choice.split(",")]
                    else:
                        delete_nums = [int(x.strip()) for x in choice.split()]

                    # Validate numbers
                    valid_nums = []
                    for num in delete_nums:
                        if 1 <= num <= len(songs_with_info):
                            valid_nums.append(num - 1)  # Convert to 0-based index
                        else:
                            print(
                                f"Invalid song number: {num}. Please choose 1-{len(songs_with_info)}"
                            )
                            break
                    else:
                        # All numbers are valid
                        to_delete = [
                            songs_with_info[i]["song"]["id"] for i in valid_nums
                        ]
                        return to_delete

                except ValueError:
                    print(
                        "Invalid format. Enter song numbers separated by commas or spaces."
                    )
                    continue

    def delete_song(self, song_id: str, dry_run: bool = False) -> bool:
        """Delete a song from both database and filesystem."""
        try:
            if dry_run:
                print(f"  [DRY RUN] Would delete song {song_id}")
                return True

            # Delete from filesystem
            song_dir = self.karaoke_lib_path / song_id
            if song_dir.exists():
                shutil.rmtree(song_dir)
                print(f"  ✅ Deleted directory: {song_dir}")
            else:
                print(f"  ⚠️ Directory not found: {song_dir}")

            # Delete from database
            success = delete_song(song_id)
            if success:
                print(f"  ✅ Deleted from database: {song_id}")
                return True
            else:
                print(f"  ❌ Failed to delete from database: {song_id}")
                return False

        except Exception as e:
            print(f"  ❌ Error deleting song {song_id}: {e}")
            return False

    def export_duplicate_report(
        self, duplicate_groups: List[List[Dict]], filename: str
    ) -> None:
        """Export duplicate groups to a JSON file."""
        export_data = {
            "timestamp": datetime.now().isoformat(),
            "total_groups": len(duplicate_groups),
            "similarity_threshold": self.similarity_threshold,
            "groups": [],
        }

        for i, group in enumerate(duplicate_groups):
            group_data = {"group_number": i + 1, "songs": []}

            for song in group:
                integrity_info = self.get_song_integrity_info(song["id"])
                score, max_score = self.calculate_completeness_score(integrity_info)

                song_data = {
                    "id": song["id"],
                    "title": song["title"],
                    "artist": song["artist"],
                    "completeness_score": f"{score}/{max_score}",
                    "integrity_info": integrity_info,
                }
                group_data["songs"].append(song_data)

            export_data["groups"].append(group_data)

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, default=str)

        print(f"Duplicate report exported to: {filename}")

    def run_duplicate_management(
        self,
        dry_run: bool = False,
        auto_mode: bool = False,
        export_file: Optional[str] = None,
    ) -> None:
        """Run the complete duplicate management process."""
        print("🎵 Open Karaoke Studio - Duplicate Song Manager")
        print("=" * 60)

        # Find duplicate groups
        duplicate_groups = self.find_duplicate_groups()

        if not duplicate_groups:
            print("✅ No duplicate songs found!")
            return

        # Export report if requested
        if export_file:
            self.export_duplicate_report(duplicate_groups, export_file)

        # Process each group
        total_deleted = 0

        for i, group in enumerate(duplicate_groups):
            group_data = (
                group
                if isinstance(group, dict)
                else {"songs": group, "is_exact": False}
            )
            songs_with_info = self.display_duplicate_group(group_data, i + 1)

            if auto_mode:
                # Auto mode: keep most complete, delete others
                to_delete = [info["song"]["id"] for info in songs_with_info[1:]]
                print(
                    f"\n🤖 AUTO MODE: Keeping most complete song, deleting {len(to_delete)} others"
                )
            else:
                # Interactive mode
                to_delete = self.interactive_selection(songs_with_info)

                if to_delete is None:  # User chose to quit
                    print("\n👋 Exiting duplicate management")
                    break
                elif not to_delete:  # User chose to skip
                    print("⏭️ Skipping this group")
                    continue

            # Confirm deletion
            if to_delete and not auto_mode:
                songs_to_delete_names = []
                for song_info in songs_with_info:
                    if song_info["song"]["id"] in to_delete:
                        songs_to_delete_names.append(
                            f"{song_info['song']['title']} by {song_info['song']['artist']}"
                        )

                print(f"\n🗑️ About to delete {len(to_delete)} songs:")
                for name in songs_to_delete_names:
                    print(f"  - {name}")

                if not dry_run:
                    confirm = input("\nAre you sure? (y/N): ").strip().lower()
                    if confirm != "y":
                        print("❌ Deletion cancelled")
                        continue

            # Perform deletion
            print(f"\n🗑️ Deleting {len(to_delete)} songs...")
            deleted_count = 0

            for song_id in to_delete:
                if self.delete_song(song_id, dry_run):
                    deleted_count += 1

            total_deleted += deleted_count
            print(
                f"✅ Successfully deleted {deleted_count}/{len(to_delete)} songs from this group"
            )

        print(f"\n🎯 Summary: Deleted {total_deleted} duplicate songs")
        if dry_run:
            print("(This was a dry run - no actual deletions were performed)")


def main():
    parser = argparse.ArgumentParser(
        description="Manage duplicate songs in Open Karaoke Studio"
    )
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.8,
        help="Minimum similarity threshold (0.0-1.0, default: 0.8)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )
    parser.add_argument(
        "--auto-mode",
        action="store_true",
        help="Automatically keep the most complete version",
    )
    parser.add_argument(
        "--export-report", help="Export duplicate groups to a file before processing"
    )

    args = parser.parse_args()

    # Validate similarity threshold
    if not 0.0 <= args.similarity_threshold <= 1.0:
        print("Error: Similarity threshold must be between 0.0 and 1.0")
        return 1

    try:
        manager = DuplicateManager(args.similarity_threshold)
        manager.run_duplicate_management(
            dry_run=args.dry_run,
            auto_mode=args.auto_mode,
            export_file=args.export_report,
        )
        return 0
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
