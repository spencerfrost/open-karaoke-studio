"""
Simplified Metadata Updater using utility modules

This is a much smaller, focused version of the metadata updater that
delegates most functionality to utility modules.
"""

import logging
from typing import Optional, List

from app.db.models import DbSong
from .itunes_utils import search_itunes_for_song, enhance_song_with_itunes_data
from .cover_art_utils import should_download_cover_art, download_high_res_cover_art
from .database_utils import update_song_metadata
from .batch_utils import BatchProcessor, ProcessingStats, create_progress_callback

logger = logging.getLogger(__name__)


class MetadataUpdater:
    """Simplified metadata updater that orchestrates the utility modules"""
    
    def __init__(
        self,
        dry_run: bool = False,
        batch_size: int = 10,
        delay: float = 3.0,
        skip_existing: bool = False,
        force_cover_art: bool = False,
        verbose: bool = False
    ):
        self.dry_run = dry_run
        self.skip_existing = skip_existing
        self.force_cover_art = force_cover_art
        self.verbose = verbose
        
        # Initialize batch processor
        self.batch_processor = BatchProcessor(batch_size=batch_size, delay=delay)
        
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        
        logger.info(f"MetadataUpdater initialized - dry_run: {dry_run}, batch_size: {batch_size}, delay: {delay}")
    
    def process_song(self, song: DbSong, stats: ProcessingStats) -> bool:
        """
        Process a single song: search iTunes, update metadata, download cover art.
        
        Args:
            song: The song to process
            stats: Processing statistics object
            
        Returns:
            True if song was updated, False if skipped
        """
        try:
            logger.debug(f"Processing song {song.id}: '{song.title}' by '{song.artist}'")
            
            # Skip if song already has iTunes ID and skip_existing is True
            if self.skip_existing and song.itunes_track_id:
                logger.debug(f"Skipping song {song.id} - already has iTunes track ID")
                return False
            
            # Search iTunes for metadata
            logger.debug(f"Searching iTunes for song {song.id}")
            itunes_data = search_itunes_for_song(song)
            stats.increment_api_calls()
            
            if not itunes_data:
                logger.info(f"No iTunes match found for song {song.id}: '{song.title}' by '{song.artist}'")
                return False
            
            # Create enhanced metadata using the iTunes data we already fetched
            enhanced_metadata = enhance_song_with_itunes_data(song, itunes_data)
            if not enhanced_metadata:
                logger.warning(f"Failed to create enhanced metadata for song {song.id}")
                return False
            
            # Check if we need to download cover art
            should_download, reason = should_download_cover_art(song, self.force_cover_art)
            
            cover_art_path = None
            if should_download:
                logger.info(f"Song {song.id}: {reason}")
                cover_art_path = download_high_res_cover_art(song, itunes_data, self.dry_run)
                if cover_art_path:
                    enhanced_metadata['cover_art_path'] = cover_art_path
            else:
                logger.debug(f"Song {song.id}: {reason}")
            
            # Update database
            success = update_song_metadata(song, enhanced_metadata, self.dry_run)
            
            if success:
                logger.info(f"Successfully processed song {song.id}")
                return True
            else:
                logger.error(f"Failed to update song {song.id} in database")
                return False
                
        except Exception as e:
            logger.error(f"Error processing song {song.id}: {e}")
            return False
    
    def run(self, songs: List[DbSong]) -> ProcessingStats:
        """
        Run the metadata update process on a list of songs.
        
        Args:
            songs: List of songs to process
            
        Returns:
            Processing statistics
        """
        logger.info("=" * 60)
        logger.info("STARTING METADATA UPDATE PROCESS")
        logger.info("=" * 60)
        
        if self.dry_run:
            logger.info("🔍 DRY RUN MODE - No changes will be made")
        
        if not songs:
            logger.info("No songs to process")
            return ProcessingStats()
        
        # Create progress callback for logging
        progress_callback = create_progress_callback(log_interval=5)
        
        # Process songs using batch processor
        stats = self.batch_processor.process_songs(
            songs=songs,
            processor_func=self.process_song,
            progress_callback=progress_callback
        )
        
        return stats
