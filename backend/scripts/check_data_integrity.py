#!/usr/bin/env python3
"""
Data Integrity Check Script for Open Karaoke Studio

This script verifies data integrity between the songs database and the karaoke library
file system. It identifies missing files, orphaned directories, and generates a
comprehensive report.

Usage:
    python check_data_integrity.py [options]

Options:
    --output FILE      Save report to specified file (default: console output)
    --format FORMAT    Output format: markdown (default), json, csv, txt
    --karaoke-lib PATH Override karaoke library path
    --verbose          Enable detailed logging
"""

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Set

from app.config import get_config
from app.db.song_operations import get_songs
from app.services.file_service import FileService

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


# File extensions to check for thumbnails
THUMBNAIL_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]


class DataIntegrityChecker:
    def __init__(self, karaoke_lib_path: Optional[str] = None):
        self.config = get_config()
        self.karaoke_lib_path = (
            Path(karaoke_lib_path)
            if karaoke_lib_path
            else Path(self.config.LIBRARY_DIR)
        )
        self.file_service = FileService(str(self.karaoke_lib_path))

    def get_database_song_ids(self) -> Set[str]:
        """Get all song IDs from the database."""
        try:
            songs = get_songs()
            return {str(song.id) for song in songs}
        except Exception as e:
            print(f"Error fetching songs from database: {e}")
            return set()

    def get_database_songs_info(self) -> Dict[str, Dict[str, str]]:
        """Get song info from database including title and artist."""
        try:
            songs = get_songs()
            return {
                str(song.id): {
                    "title": str(song.title) if song.title is not None else "Unknown",
                    "artist": (
                        str(song.artist) if song.artist is not None else "Unknown"
                    ),
                }
                for song in songs
            }
        except Exception as e:
            print(f"Error fetching song info from database: {e}")
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

    def check_required_files(self, song_id: str) -> Dict[str, any]:
        """Check for required files in a song directory."""
        song_dir = self.karaoke_lib_path / song_id

        result = {
            "song_id": song_id,
            "directory_exists": song_dir.exists(),
            "original_mp3": False,
            "vocals_mp3": False,
            "instrumental_mp3": False,
            "thumbnail": None,
            "thumbnail_format": None,
            "metadata_json": False,
            "file_sizes": {},
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

        # Check file sizes for existing files
        for file_path, key in [
            (original_path, "original_mp3"),
            (vocals_path, "vocals_mp3"),
            (instrumental_path, "instrumental_mp3"),
        ]:
            if file_path.exists():
                try:
                    size = file_path.stat().st_size
                    result["file_sizes"][key] = size
                    if size == 0:
                        result["missing_files"].append(f"{key} (0 bytes)")
                except Exception as e:
                    result["file_sizes"][key] = f"Error: {e}"
            else:
                result["missing_files"].append(key)

        # Check for thumbnail with any valid extension
        thumbnail_found = False
        for ext in THUMBNAIL_EXTENSIONS:
            thumbnail_path = song_dir / f"thumbnail{ext}"
            if thumbnail_path.exists():
                result["thumbnail"] = True
                result["thumbnail_format"] = ext[1:]  # Remove the dot
                thumbnail_found = True
                try:
                    size = thumbnail_path.stat().st_size
                    result["file_sizes"]["thumbnail"] = size
                    if size == 0:
                        result["missing_files"].append("thumbnail (0 bytes)")
                except Exception as e:
                    result["file_sizes"]["thumbnail"] = f"Error: {e}"
                break

        if not thumbnail_found:
            result["thumbnail"] = False
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

    def run_integrity_check(self) -> Dict[str, any]:
        """Run the complete data integrity check."""
        print("Starting data integrity check...")

        # Get song IDs and info from both sources
        db_song_ids = self.get_database_song_ids()
        db_songs_info = self.get_database_songs_info()
        fs_song_ids = self.get_filesystem_song_ids()

        print(f"Found {len(db_song_ids)} songs in database")
        print(f"Found {len(fs_song_ids)} directories in filesystem")

        # Find discrepancies
        consistent_ids = db_song_ids & fs_song_ids
        missing_directories = db_song_ids - fs_song_ids
        orphaned_directories = fs_song_ids - db_song_ids

        # Check files for all directories that exist
        file_checks = []
        all_existing_ids = consistent_ids | orphaned_directories

        for song_id in sorted(all_existing_ids):
            file_check = self.check_required_files(song_id)
            # Add song info if available from database
            if song_id in db_songs_info:
                file_check["title"] = db_songs_info[song_id]["title"]
                file_check["artist"] = db_songs_info[song_id]["artist"]
            else:
                file_check["title"] = "Unknown (Orphaned)"
                file_check["artist"] = "Unknown (Orphaned)"
            file_checks.append(file_check)

        return {
            "timestamp": datetime.now().isoformat(),
            "karaoke_library_path": str(self.karaoke_lib_path),
            "summary": {
                "total_db_songs": len(db_song_ids),
                "total_fs_directories": len(fs_song_ids),
                "consistent_entries": len(consistent_ids),
                "missing_directories": len(missing_directories),
                "orphaned_directories": len(orphaned_directories),
            },
            "discrepancies": {
                "consistent_ids": sorted(list(consistent_ids)),
                "missing_directories": sorted(list(missing_directories)),
                "orphaned_directories": sorted(list(orphaned_directories)),
                "missing_directory_info": [
                    {
                        "song_id": song_id,
                        "title": db_songs_info.get(song_id, {}).get("title", "Unknown"),
                        "artist": db_songs_info.get(song_id, {}).get(
                            "artist", "Unknown"
                        ),
                    }
                    for song_id in sorted(missing_directories)
                ],
            },
            "file_integrity": file_checks,
        }


class ReportGenerator:
    @staticmethod
    def generate_markdown_report(data: Dict[str, any]) -> str:
        """Generate a markdown report with detailed tables."""
        report = []

        # Header
        report.append("# Open Karaoke Studio - Data Integrity Report")
        report.append(f"**Generated:** {data['timestamp']}")
        report.append(f"**Karaoke Library Path:** `{data['karaoke_library_path']}`")
        report.append("")

        # Summary
        summary = data["summary"]
        report.append("## Summary")
        report.append("")
        report.append("| Metric | Count |")
        report.append("|--------|-------|")
        report.append(f"| Total Database Songs | {summary['total_db_songs']} |")
        report.append(
            f"| Total Filesystem Directories | {summary['total_fs_directories']} |"
        )
        report.append(f"| ✅ Consistent Entries | {summary['consistent_entries']} |")
        report.append(f"| ❌ Missing Directories | {summary['missing_directories']} |")
        report.append(f"| ⚠️ Orphaned Directories | {summary['orphaned_directories']} |")
        report.append("")

        # Directory Discrepancies
        if data["discrepancies"]["missing_directories"]:
            report.append("## ❌ Missing Directories")
            report.append("Songs in database but missing filesystem directories:")
            report.append("")
            report.append("| Song ID | Title | Artist |")
            report.append("|---------|-------|--------|")
            for song_info in data["discrepancies"]["missing_directory_info"]:
                song_id = song_info["song_id"]
                title = song_info["title"].replace(
                    "|", "\\|"
                )  # Escape pipes for markdown
                artist = song_info["artist"].replace(
                    "|", "\\|"
                )  # Escape pipes for markdown
                report.append(f"| `{song_id}` | {title} | {artist} |")
            report.append("")

        if data["discrepancies"]["orphaned_directories"]:
            report.append("## ⚠️ Orphaned Directories")
            report.append(
                "Filesystem directories without corresponding database entries:"
            )
            report.append("")
            for song_id in data["discrepancies"]["orphaned_directories"]:
                report.append(f"- `{song_id}`")
            report.append("")

        # File Integrity Check
        report.append("## File Integrity Check")
        report.append("")

        # Create detailed table
        report.append(
            "| Song ID | Title | Artist | Original | Vocals | Instrumental | Thumbnail | Thumbnail Format | Metadata | Missing Files | File Sizes | Extra Files |"
        )
        report.append(
            "|---------|-------|--------|----------|--------|-------------|-----------|------------------|----------|---------------|------------|-------------|"
        )

        for check in data["file_integrity"]:
            song_id = check["song_id"]
            title = check.get("title", "Unknown").replace(
                "|", "\\|"
            )  # Escape pipes for markdown
            artist = check.get("artist", "Unknown").replace(
                "|", "\\|"
            )  # Escape pipes for markdown
            original = "✅" if check["original_mp3"] else "❌"
            vocals = "✅" if check["vocals_mp3"] else "❌"
            instrumental = "✅" if check["instrumental_mp3"] else "❌"
            thumbnail = "✅" if check["thumbnail"] else "❌"
            thumbnail_format = check["thumbnail_format"] or "N/A"
            metadata = "✅" if check["metadata_json"] else "❌"
            missing_files = (
                ", ".join(check["missing_files"]) if check["missing_files"] else "None"
            )
            extra_files = (
                ", ".join(check["extra_files"]) if check["extra_files"] else "None"
            )

            # Format file sizes
            sizes = []
            for file_type, size in check["file_sizes"].items():
                if isinstance(size, int):
                    if size > 0:
                        sizes.append(f"{file_type}: {size//1024//1024}MB")
                    else:
                        sizes.append(f"{file_type}: 0B")
                else:
                    sizes.append(f"{file_type}: {size}")

            file_sizes = ", ".join(sizes) if sizes else "N/A"

            report.append(
                f"| `{song_id}` | {title} | {artist} | {original} | {vocals} | {instrumental} | {thumbnail} | {thumbnail_format} | {metadata} | {missing_files} | {file_sizes} | {extra_files} |"
            )

        report.append("")

        # Statistics
        total_checks = len(data["file_integrity"])
        if total_checks > 0:
            complete_songs = sum(
                1
                for check in data["file_integrity"]
                if check["original_mp3"]
                and check["vocals_mp3"]
                and check["instrumental_mp3"]
                and check["thumbnail"]
            )

            report.append("## Statistics")
            report.append("")
            report.append("| Metric | Count | Percentage |")
            report.append("|--------|-------|------------|")
            report.append(
                f"| Complete Songs (all 4 files) | {complete_songs} | {complete_songs/total_checks*100:.1f}% |"
            )

            # File type statistics
            for file_type in [
                "original_mp3",
                "vocals_mp3",
                "instrumental_mp3",
                "thumbnail",
            ]:
                count = sum(1 for check in data["file_integrity"] if check[file_type])
                percentage = count / total_checks * 100 if total_checks > 0 else 0
                file_name = file_type.replace("_", " ").title()
                report.append(f"| {file_name} Present | {count} | {percentage:.1f}% |")

            # Thumbnail format breakdown
            thumbnail_formats = {}
            for check in data["file_integrity"]:
                if check["thumbnail_format"]:
                    fmt = check["thumbnail_format"]
                    thumbnail_formats[fmt] = thumbnail_formats.get(fmt, 0) + 1

            if thumbnail_formats:
                report.append("")
                report.append("### Thumbnail Formats")
                report.append("")
                report.append("| Format | Count |")
                report.append("|--------|-------|")
                for fmt, count in sorted(thumbnail_formats.items()):
                    report.append(f"| {fmt.upper()} | {count} |")

        return "\n".join(report)

    @staticmethod
    def generate_json_report(data: Dict[str, any]) -> str:
        """Generate a JSON report."""
        return json.dumps(data, indent=2, default=str)

    @staticmethod
    def generate_csv_report(data: Dict[str, any]) -> str:
        """Generate a CSV report focusing on file integrity."""
        fieldnames = [
            "song_id",
            "title",
            "artist",
            "original_mp3",
            "vocals_mp3",
            "instrumental_mp3",
            "thumbnail",
            "thumbnail_format",
            "metadata_json",
            "missing_files",
            "extra_files",
            "file_sizes_mb",
        ]

        # Create CSV content
        csv_data = []
        for check in data["file_integrity"]:
            row = {
                "song_id": check["song_id"],
                "title": check.get("title", "Unknown"),
                "artist": check.get("artist", "Unknown"),
                "original_mp3": check["original_mp3"],
                "vocals_mp3": check["vocals_mp3"],
                "instrumental_mp3": check["instrumental_mp3"],
                "thumbnail": check["thumbnail"],
                "thumbnail_format": check["thumbnail_format"] or "",
                "metadata_json": check["metadata_json"],
                "missing_files": "; ".join(check["missing_files"]),
                "extra_files": "; ".join(check["extra_files"]),
                "file_sizes_mb": "; ".join(
                    [
                        (
                            f"{k}:{v//1024//1024}MB"
                            if isinstance(v, int) and v > 0
                            else f"{k}:{v}"
                        )
                        for k, v in check["file_sizes"].items()
                    ]
                ),
            }
            csv_data.append(row)

        # Write to string
        from io import StringIO

        output_io = StringIO()
        writer = csv.DictWriter(output_io, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_data)

        return output_io.getvalue()

    @staticmethod
    def generate_text_report(data: Dict[str, any]) -> str:
        """Generate a plain text report."""
        report = []

        report.append("OPEN KARAOKE STUDIO - DATA INTEGRITY REPORT")
        report.append("=" * 50)
        report.append(f"Generated: {data['timestamp']}")
        report.append(f"Karaoke Library Path: {data['karaoke_library_path']}")
        report.append("")

        # Summary
        summary = data["summary"]
        report.append("SUMMARY")
        report.append("-" * 20)
        report.append(f"Total Database Songs: {summary['total_db_songs']}")
        report.append(
            f"Total Filesystem Directories: {summary['total_fs_directories']}"
        )
        report.append(f"Consistent Entries: {summary['consistent_entries']}")
        report.append(f"Missing Directories: {summary['missing_directories']}")
        report.append(f"Orphaned Directories: {summary['orphaned_directories']}")
        report.append("")

        # File integrity summary
        total_checks = len(data["file_integrity"])
        if total_checks > 0:
            complete_songs = sum(
                1
                for check in data["file_integrity"]
                if check["original_mp3"]
                and check["vocals_mp3"]
                and check["instrumental_mp3"]
                and check["thumbnail"]
            )

            report.append("FILE INTEGRITY SUMMARY")
            report.append("-" * 25)
            report.append(
                f"Complete Songs (all 4 files): {complete_songs}/{total_checks} ({complete_songs/total_checks*100:.1f}%)"
            )
            report.append("")

        return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(
        description="Check data integrity between database and filesystem"
    )
    parser.add_argument("--output", "-o", help="Save report to specified file")
    parser.add_argument(
        "--format",
        "-f",
        choices=["markdown", "json", "csv", "txt"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    parser.add_argument("--karaoke-lib", help="Override karaoke library path")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )

    args = parser.parse_args()

    # Initialize checker
    checker = DataIntegrityChecker(args.karaoke_lib)

    # Run the check
    try:
        result = checker.run_integrity_check()
    except Exception as e:
        print(f"Error during integrity check: {e}")
        return 1

    # Generate report
    generator = ReportGenerator()

    if args.format == "markdown":
        report_content = generator.generate_markdown_report(result)
    elif args.format == "json":
        report_content = generator.generate_json_report(result)
    elif args.format == "csv":
        report_content = generator.generate_csv_report(result)
    elif args.format == "txt":
        report_content = generator.generate_text_report(result)

    # Output report
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(report_content)
            print(f"Report saved to: {args.output}")
        except Exception as e:
            print(f"Error saving report: {e}")
            return 1
    else:
        print(report_content)

    return 0


if __name__ == "__main__":
    exit(main())
