#!/usr/bin/env python3
"""
Update Metadata - Incremental Development Version

Starting from a working minimal version and adding features step by step.
This replaces the hanging V2 script with a tested, working approach.

Usage:
    python update_metadata.py [options]

Examples:
    # Show current statistics only
    python update_metadata.py --stats-only

    # Dry run to see what would be updated
    python update_metadata.py --dry-run

    # Process only songs without iTunes metadata, force cover art updates
    python update_metadata.py --skip-existing --force-cover-art

    # Process first 10 songs with verbose logging
    python update_metadata.py --limit 10 --verbose
"""

import argparse
import logging
import sys
from pathlib import Path

print("Starting Update Metadata...")

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

print(f"Backend dir: {backend_dir}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

logger = logging.getLogger(__name__)

print("Importing utilities...")

from scripts.utils.cover_art_utils import get_cover_art_stats

# Import utility modules
from scripts.utils.database_utils import get_database_stats, get_songs_to_process

print("Basic imports successful, testing batch_utils...")

# Test importing batch_utils
try:
    from scripts.utils.batch_utils import estimate_processing_time

    print("batch_utils imported successfully!")
except Exception as e:
    print(f"batch_utils import failed: {e}")
    import traceback

    traceback.print_exc()

print("Testing MetadataUpdater import...")

# Test importing MetadataUpdater
try:
    from scripts.utils.metadata_updater import MetadataUpdater

    print("MetadataUpdater imported successfully!")
except Exception as e:
    print(f"MetadataUpdater import failed: {e}")
    import traceback

    traceback.print_exc()

print("Imports successful, defining print_stats_summary...")


def print_stats_summary():
    """Print a summary of current database and cover art statistics"""
    logger.info("Getting current database statistics...")

    db_stats = get_database_stats()
    cover_stats = get_cover_art_stats()

    logger.info("=" * 60)
    logger.info("CURRENT DATABASE STATISTICS")
    logger.info("=" * 60)
    logger.info(f"Total songs: {db_stats['total_songs']}")
    logger.info(
        f"With iTunes ID: {db_stats['with_itunes_id']} ({db_stats.get('with_itunes_id_percentage', 0):.1f}%)"
    )
    logger.info(
        f"With cover art: {db_stats['with_cover_art']} ({db_stats.get('with_cover_art_percentage', 0):.1f}%)"
    )
    logger.info(
        f"With genre: {db_stats['with_genre']} ({db_stats.get('with_genre_percentage', 0):.1f}%)"
    )
    logger.info(
        f"With release date: {db_stats['with_release_date']} ({db_stats.get('with_release_date_percentage', 0):.1f}%)"
    )
    logger.info(
        f"Unknown artist: {db_stats['unknown_artist']} ({db_stats.get('unknown_artist_percentage', 0):.1f}%)"
    )

    logger.info("")
    logger.info("COVER ART STATISTICS")
    logger.info("-" * 30)
    logger.info(f"High-res cover art: {cover_stats['high_res_cover_art']}")
    logger.info(f"Low-res cover art: {cover_stats['low_res_cover_art']}")
    logger.info(f"No cover art: {cover_stats['without_cover_art']}")
    logger.info(f"Missing files: {cover_stats['missing_files']}")

    total_needing_update = (
        cover_stats["low_res_cover_art"]
        + cover_stats["without_cover_art"]
        + cover_stats["missing_files"]
    )
    logger.info(f"Total needing cover art updates: {total_needing_update}")
    logger.info("=" * 60)


def main():
    """Main function - Step 2: Add argument parsing"""
    parser = argparse.ArgumentParser(
        description="Update song metadata using iTunes Search API"
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Only show statistics, don't process songs",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without making changes",
    )
    parser.add_argument(
        "--limit",
        type=int,
        metavar="N",
        help="Only process first N songs (for testing)",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Enable detailed logging"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip songs that already have iTunes metadata",
    )
    parser.add_argument(
        "--force-cover-art",
        action="store_true",
        help="Force cover art updates even for songs that already have cover art",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("Verbose logging enabled")

    print("Calling print_stats_summary...")
    print_stats_summary()
    print("Stats completed successfully!")

    if args.stats_only:
        logger.info("Stats-only mode - exiting")
        return

    # Step 5: Test getting songs to process
    logger.info("Testing song retrieval...")
    try:
        songs = get_songs_to_process(
            limit=args.limit
        )  # Use args.limit (None for all songs)
        logger.info(f"Successfully retrieved {len(songs)} songs for processing")

        if songs:
            logger.info(f"First song: {songs[0].title} by {songs[0].artist}")

            # Step 6: Simple dry-run processing
            if args.dry_run:
                logger.info("DRY-RUN MODE: Simulating metadata update process...")
                for i, song in enumerate(
                    songs[:3], 1
                ):  # Just process first 3 in dry-run
                    logger.info(f"  {i}. Would process: {song.title} by {song.artist}")
                    logger.info(
                        f"     Current iTunes ID: {song.itunes_track_id or 'None'}"
                    )
                    logger.info(
                        f"     Current cover art: {'Yes' if song.cover_art_path else 'No'}"
                    )
                logger.info("DRY-RUN MODE: Completed simulation")
            else:
                # Step 7: Actual MetadataUpdater processing
                logger.info("LIVE MODE: Running actual metadata update process...")
                try:
                    updater = MetadataUpdater(
                        dry_run=False,
                        batch_size=5,  # Reasonable batch size for production
                        delay=3.5,  # 3.5 second delay = ~17 calls/min (well under 20/min limit)
                        skip_existing=args.skip_existing,
                        force_cover_art=args.force_cover_art,
                        verbose=args.verbose,
                    )

                    logger.info(
                        f"Created MetadataUpdater, processing {len(songs)} songs..."
                    )
                    final_stats = updater.run(songs)

                    # Show final summary
                    logger.info("")
                    logger.info("Final processing summary:")
                    logger.info(f"Processed: {final_stats.processed}")
                    logger.info(f"Updated: {final_stats.updated}")
                    logger.info(f"Errors: {final_stats.errors}")
                    logger.info(
                        f"Success rate: {(final_stats.updated / final_stats.processed * 100):.1f}%"
                        if final_stats.processed > 0
                        else "N/A"
                    )

                except Exception as e:
                    logger.error(f"Error during metadata update: {e}")
                    import traceback

                    traceback.print_exc()
                    return

    except Exception as e:
        logger.error(f"Error getting songs: {e}")
        import traceback

        traceback.print_exc()
        return

    logger.info("Script completed - Step 7 (full MetadataUpdater integration)")


if __name__ == "__main__":
    main()
