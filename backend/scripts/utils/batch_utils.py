"""
Batch Processing Utilities for Metadata Update Script

This module handles batch processing operations including:
- Processing songs in batches
- Rate limiting
- Progress tracking
- Statistics management
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from app.db.models import DbSong

logger = logging.getLogger(__name__)


@dataclass
class ProcessingStats:
    """Statistics tracking for batch processing"""

    total_songs: int = 0
    processed: int = 0
    updated: int = 0
    skipped: int = 0
    errors: int = 0
    api_calls: int = 0
    start_time: float = field(default_factory=time.time)

    def increment_api_calls(self):
        """Increment API call counter"""
        self.api_calls += 1

    def increment_processed(self):
        """Increment processed counter"""
        self.processed += 1

    def increment_updated(self):
        """Increment updated counter"""
        self.updated += 1

    def increment_skipped(self):
        """Increment skipped counter"""
        self.skipped += 1

    def increment_errors(self):
        """Increment error counter"""
        self.errors += 1

    def get_elapsed_time(self) -> float:
        """Get elapsed time since start"""
        return time.time() - self.start_time

    def get_progress_percentage(self) -> float:
        """Get progress as percentage"""
        if self.total_songs == 0:
            return 0.0
        return (self.processed / self.total_songs) * 100

    def get_estimated_time_remaining(self) -> Optional[float]:
        """Get estimated time remaining in seconds"""
        if self.processed == 0:
            return None

        elapsed = self.get_elapsed_time()
        rate = self.processed / elapsed
        remaining_songs = self.total_songs - self.processed

        if rate <= 0:
            return None

        return remaining_songs / rate

    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary for logging"""
        return {
            "total_songs": self.total_songs,
            "processed": self.processed,
            "updated": self.updated,
            "skipped": self.skipped,
            "errors": self.errors,
            "api_calls": self.api_calls,
            "elapsed_time": round(self.get_elapsed_time(), 1),
            "progress_percentage": round(self.get_progress_percentage(), 1),
        }


class BatchProcessor:
    """Handles batch processing of songs with rate limiting and progress tracking"""

    def __init__(self, batch_size: int = 10, delay: float = 1.0):
        self.batch_size = batch_size
        self.delay = delay
        self.stats = ProcessingStats()

    def process_songs(
        self,
        songs: List[DbSong],
        processor_func: Callable[[DbSong, ProcessingStats], bool],
        progress_callback: Optional[Callable[[ProcessingStats], None]] = None,
    ) -> ProcessingStats:
        """
        Process a list of songs in batches with rate limiting.

        Args:
            songs: List of songs to process
            processor_func: Function to process each song (song, stats) -> success
            progress_callback: Optional callback for progress updates

        Returns:
            Final processing statistics
        """
        self.stats = ProcessingStats()
        self.stats.total_songs = len(songs)

        logger.info(f"Starting batch processing of {len(songs)} songs")
        logger.info(f"Batch size: {self.batch_size}, Delay: {self.delay}s")

        try:
            # Process songs in batches
            for i in range(0, len(songs), self.batch_size):
                batch = songs[i : i + self.batch_size]
                batch_num = (i // self.batch_size) + 1
                total_batches = ((len(songs) - 1) // self.batch_size) + 1

                logger.info(
                    f"Processing batch {batch_num}/{total_batches} ({len(batch)} songs)"
                )

                for song in batch:
                    try:
                        success = processor_func(song, self.stats)

                        if success:
                            self.stats.increment_updated()
                        else:
                            self.stats.increment_skipped()

                        self.stats.increment_processed()

                        # Rate limiting - delay between songs
                        if self.delay > 0:
                            time.sleep(self.delay)

                        # Call progress callback if provided
                        if progress_callback:
                            progress_callback(self.stats)

                    except KeyboardInterrupt:
                        logger.info("Received interrupt signal, stopping...")
                        raise
                    except Exception as e:
                        logger.error(f"Unexpected error processing song {song.id}: {e}")
                        self.stats.increment_errors()
                        self.stats.increment_processed()
                        continue

                # Log batch completion
                self._log_batch_progress(batch_num, total_batches)

        except KeyboardInterrupt:
            logger.info("Processing interrupted by user")
        except Exception as e:
            logger.error(f"Fatal error during batch processing: {e}")
            self.stats.increment_errors()

        # Log final statistics
        self._log_final_stats()
        return self.stats

    def _log_batch_progress(self, batch_num: int, total_batches: int):
        """Log progress after each batch"""
        progress = self.stats.get_progress_percentage()
        elapsed = self.stats.get_elapsed_time()
        eta = self.stats.get_estimated_time_remaining()

        eta_str = f", ETA: {eta:.1f}s" if eta else ""
        logger.info(
            f"Batch {batch_num}/{total_batches} complete - "
            f"Progress: {progress:.1f}% ({self.stats.processed}/{self.stats.total_songs}), "
            f"Updated: {self.stats.updated}, Skipped: {self.stats.skipped}, "
            f"Errors: {self.stats.errors}, Elapsed: {elapsed:.1f}s{eta_str}"
        )

    def _log_final_stats(self):
        """Log final processing statistics"""
        elapsed = self.stats.get_elapsed_time()
        rate = self.stats.processed / elapsed if elapsed > 0 else 0

        logger.info("=" * 60)
        logger.info("BATCH PROCESSING COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total songs: {self.stats.total_songs}")
        logger.info(f"Processed: {self.stats.processed}")
        logger.info(f"Updated: {self.stats.updated}")
        logger.info(f"Skipped: {self.stats.skipped}")
        logger.info(f"Errors: {self.stats.errors}")
        logger.info(f"API calls: {self.stats.api_calls}")
        logger.info(f"Total time: {elapsed:.1f}s")
        logger.info(f"Processing rate: {rate:.2f} songs/second")
        logger.info("=" * 60)


def create_progress_callback(
    log_interval: int = 10,
) -> Callable[[ProcessingStats], None]:
    """
    Create a progress callback that logs every N processed songs.

    Args:
        log_interval: Log progress every N songs

    Returns:
        Progress callback function
    """

    def progress_callback(stats: ProcessingStats):
        if stats.processed % log_interval == 0:
            progress = stats.get_progress_percentage()
            eta = stats.get_estimated_time_remaining()
            eta_str = f", ETA: {eta:.1f}s" if eta else ""

            logger.info(
                f"Progress: {progress:.1f}% ({stats.processed}/{stats.total_songs}) - "
                f"Updated: {stats.updated}, API calls: {stats.api_calls}{eta_str}"
            )

    return progress_callback


def estimate_processing_time(
    num_songs: int, delay: float, api_calls_per_song: float = 1.5
) -> float:
    """
    Estimate total processing time for a number of songs.

    Args:
        num_songs: Number of songs to process
        delay: Delay between songs in seconds
        api_calls_per_song: Average API calls per song

    Returns:
        Estimated time in seconds
    """
    # Base processing time per song (API calls + processing overhead)
    base_time_per_song = (
        api_calls_per_song * 0.5
    ) + 0.1  # 0.5s per API call + 0.1s overhead

    # Total time = (base time + delay) * number of songs
    total_time = (base_time_per_song + delay) * num_songs

    return total_time
