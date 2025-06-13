# High-Resolution Cover Art Update Script Requirements

## Overview
Create a script to update all existing songs in the database with high-resolution (600x600) iTunes cover art. This addresses the issue where songs processed before the 600x600 URL fix still have low-resolution (100x100) cover art images.

## Background
- **Problem**: Existing songs in the database have low-resolution cover art (100x100, ~5KB files)
- **Root Cause**: Songs were processed before the iTunes URL replacement fix (`100x100bb.jpg` → `600x600bb.jpg`)
- **Solution**: Re-download cover art for existing songs using the fixed `get_itunes_cover_art()` function

## Current State Analysis
The existing `update_metadata.py` script has a `download_cover_art_if_needed()` method that:
- ✅ Checks if cover art already exists and skips if present
- ❌ Uses `download_image()` directly with original iTunes URLs (downloads 100x100)
- ❌ Does not use the fixed `get_itunes_cover_art()` function (which downloads 600x600)

## Requirements

### Core Functionality
1. **Database Query**: Identify songs that need cover art updates
   - Songs with existing iTunes metadata (`itunes_track_id` NOT NULL)
   - Songs with either:
     - No cover art (`cover_art_path` IS NULL), OR
     - Low-resolution cover art (file size < 20KB)

2. **Cover Art Detection Logic**
   ```
   FOR EACH song in database:
     IF song has iTunes track ID:
       IF song has no cover_art_path:
         → NEEDS UPDATE
       ELSE IF cover art file exists AND file size < 20KB:
         → NEEDS UPDATE (low-res)
       ELSE:
         → SKIP (already has high-res)
   ```

3. **Cover Art Download Process**
   - Use existing `get_itunes_cover_art()` function (has 600x600 fix)
   - Construct iTunes track data from stored metadata
   - Download to standard `cover.jpg` location
   - Update database `cover_art_path` field

4. **iTunes Data Reconstruction**
   - Extract iTunes artwork URLs from `itunes_artwork_urls` field (JSON array)
   - Construct track_data dict compatible with `get_itunes_cover_art()`
   - Fallback to iTunes API search if artwork URLs unavailable

### Script Options
- `--dry-run`: Show what would be updated without making changes
- `--limit N`: Process only first N songs (for testing)
- `--batch-size N`: Process songs in batches (default: 10)
- `--delay N`: Delay between downloads in seconds (default: 0.5)
- `--force-redownload`: Re-download even if cover art exists
- `--verbose`: Enable detailed logging
- `--resume-from ID`: Resume processing from specific song ID

### File Size Thresholds
- **Low-resolution indicator**: < 20KB (suggests 100x100 image)
- **High-resolution indicator**: > 20KB (suggests 600x600 image)
- **Expected high-res size**: 50-150KB for typical album art

### Error Handling & Logging
1. **Skip Conditions** (log as INFO):
   - Song directory doesn't exist
   - No iTunes metadata available
   - Already has high-resolution cover art

2. **Warning Conditions** (log as WARNING):
   - iTunes artwork URLs unavailable
   - Download failed but not critical
   - File size unexpectedly small after download

3. **Error Conditions** (log as ERROR):
   - Database connection issues
   - File system permission errors
   - Critical failures that should stop processing

### Progress Tracking
- Total songs to process
- Current progress (X of Y)
- Downloaded count vs skipped count
- Processing rate (songs/minute)
- Estimated time remaining

### Database Safety
- Use transactions for database updates
- Backup original `cover_art_path` before updating
- Rollback mechanism in case of failures
- Verify file exists before updating database

## Implementation Notes

### Key Functions to Reuse
- `get_itunes_cover_art()` - Use this instead of `download_image()` directly
- `get_cover_art_path()` - For determining save location
- Database functions from existing update script

### iTunes Data Structure
```python
track_data = {
    'artworkUrl100': 'https://...100x100bb.jpg',
    'artworkUrl60': 'https://...60x60bb.jpg', 
    'artworkUrl30': 'https://...30x30bb.jpg'
}
```

### File Structure
```
backend/scripts/update_cover_art.py  # New script
backend/scripts/update_metadata.py  # Existing (reference only)
```

## Success Criteria
1. Script successfully identifies songs needing cover art updates
2. Downloads high-resolution (600x600) cover art using fixed logic
3. Updates database records with new cover art paths
4. Handles errors gracefully without corrupting data
5. Provides clear progress reporting and logging
6. Can be run safely multiple times (idempotent)

## Testing Strategy
1. **Dry Run Test**: Verify song identification logic
2. **Small Batch Test**: Process 5-10 songs, verify file sizes
3. **File Size Verification**: Confirm downloaded images are >50KB
4. **Database Integrity**: Verify all database updates are correct
5. **Frontend Verification**: Confirm updated cover art displays in UI

## Future Considerations
- Could be integrated into existing `update_metadata.py` as an option
- May need similar logic for YouTube thumbnails
- Could be extended to validate image quality/format
