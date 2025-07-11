# Library Management

Master your music collection with powerful organization, search, and management features in Open Karaoke Studio.

## 📚 Library Overview

Your library contains all processed songs with rich metadata, artwork, and organization tools. The library automatically grows as you add songs and enhances over time with improved metadata.

### Library Structure

- **Artists** - Organized alphabetically with song counts
- **Albums** - Grouped by release with track listings
- **Recent** - Recently added or played songs
- **Processing** - Songs currently being processed

## 🔍 Search & Discovery

### Dual Display Interface

The library features a modern dual-display interface that combines search and browsing:

**Song Results Section:**

- **Prominent Search Results** - Large grid view of matching songs
- **Fuzzy Search** - Finds songs even with typos or partial matches
- **Infinite Scroll** - Continuously loads more results as you scroll
- **Real-time Filtering** - Results update instantly as you type

**Artist Browsing Section:**

- **Alphabetical Organization** - Artists grouped and sorted A-Z
- **Expandable Sections** - Click to reveal all songs by an artist
- **Song Counts** - See how many tracks each artist has
- **Compact View** - Horizontal song cards for efficient browsing

### Intelligent Search

- **Global Search Bar** - Single search input for the entire library
- **Multi-field Matching** - Searches titles, artists, albums simultaneously
- **Fuzzy Matching** - Finds results even with typos or alternative spellings
- **Debounced Input** - Optimized search performance with smart request timing

### Search Features

**Smart Matching Examples:**

```
"bohemian" → Finds "Bohemian Rhapsody"
"queen boh" → Finds "Queen - Bohemian Rhapsody"
"rhapsody bohemian" → Finds "Bohemian Rhapsody" (word order independent)
"boh rhap" → Finds "Bohemian Rhapsody" (partial matching)
```

**Performance Optimizations:**

- **Infinite Pagination** - Large libraries load efficiently
- **Conditional Loading** - Artist songs load only when expanded
- **Search Debouncing** - Reduces server load with smart request timing
- **Result Caching** - Common searches cached for instant results

### Advanced Search _(Coming Soon)_

- **Filter by Genre** - Music style categories
- **Duration Range** - Find songs by length
- **Processing Quality** - Filter by vocal separation quality
- **Import Source** - YouTube vs. local uploads

### Search Tips

**Basic Search:**

```
"bohemian" → Finds "Bohemian Rhapsody"
"queen boh" → Finds "Queen - Bohemian Rhapsody"
"rock" → Finds all songs with "rock" in title, artist, or album
```

**Future Advanced Search:**

```
"genre:rock" → Future: Genre-based search
"duration:3-5min" → Future: Duration filtering
"year:2020-2023" → Future: Year range filtering
```

## 🗂️ Organization Methods

### By Artist

- **Dual Display Browsing** - Artists listed in expandable sections alongside search results
- **Alphabetical Organization** - Artists sorted A-Z with clear letter grouping
- **Song Count Display** - See total tracks per artist at a glance
- **Expandable Interface** - Click artist name to reveal all songs
- **Compact Song Cards** - Horizontal layout for efficient artist song browsing
- **Infinite Scroll** - Large artist collections load progressively
- **Smart Grouping** - Handles "The Beatles" vs "Beatles" intelligently
- **Collaboration Handling** - Featured artists and duets properly categorized

### By Album

- **Album View** - Complete album listings with artwork
- **Track Order** - Maintains original track sequencing when available
- **Compilation Albums** - Various Artists and soundtrack organization
- **Release Information** - Year, genre, and label data

### Custom Organization _(Future)_

- **Custom Playlists** - Create themed collections
- **Smart Playlists** - Auto-updating based on criteria
- **Folders** - Hierarchical organization
- **Tags** - Custom categorization system

## 🎵 Song Management

### Individual Song Actions

**View Song Details:**

- Click any song to open detailed view
- See complete metadata, artwork, and processing info
- Play preview of vocal/instrumental tracks
- Access download links for separated tracks

**Edit Metadata:**

- Click "Edit" on any song
- Modify title, artist, album, year
- Add custom tags and notes
- Save changes with instant updates

### Batch Operations (FUTURE FEATURE)

**Select Multiple Songs:**

- Checkbox selection for batch operations
- "Select All" for entire artist/album
- Shift+click for range selection

**Batch Actions:**

- Remove from library
- Edit metadata for multiple songs
- Export song information

## 📊 Library Statistics

### Overview Dashboard

- **Total Songs** - Complete library count
- **Processing Status** - Songs in various stages
- **Storage Usage** - Disk space utilization
- **Recent Activity** - Latest additions and modifications

### Quality Metrics

- **Processing Success Rate** - Vocal separation quality distribution
- **Metadata Completeness** - Songs with full vs. partial metadata
- **Audio Quality** - Bitrate and format distribution
- **Source Breakdown** - YouTube vs. local upload statistics

## 🎨 Visual Management

### Artwork Handling

- **Automatic Artwork** - iTunes and YouTube thumbnail extraction
- **Custom Artwork** - Upload your own images
- **Artwork Quality** - Multiple resolutions maintained
- **Missing Artwork** - Placeholder system for songs without images

### Visual Browsing

- **Grid View** - Album cover browsing
- **List View** - Compact text-based view
- **Detail View** - Rich information display
- **Thumbnail Previews** - Quick visual identification

## 🔧 Maintenance & Cleanup

### Library Health

**Duplicate Detection:**

- Automatic duplicate identification
- Similarity matching for potential duplicates
- Merge or remove duplicate entries
- Preserve best quality versions

**Metadata Cleanup:**

- Standardize artist names
- Complete missing information
- Verify and correct metadata
- Bulk metadata operations

**Quality Assessment:**

- Identify low-quality vocal separations
- Flag problematic audio files
- Re-process failed separations
- Archive low-quality tracks

### Backup & Export

**Library Backup:**

- Export complete library metadata
- Backup processed audio files
- Settings and preferences export
- Restoration procedures

**Data Export:**

- CSV/JSON metadata export
- Playlist export formats
- Integration with external systems
- Migration tools

## 📱 Mobile Library Management

### Mobile Interface

- **Touch-Optimized** - Large touch targets for easy navigation
- **Responsive Design** - Adapts to phone and tablet screens
- **Gesture Support** - Swipe actions for common operations
- **Offline Browsing** - Cached metadata for offline viewing

### Mobile-Specific Features

- **Quick Add** - Fast song addition from mobile
- **Voice Search** _(Future)_ - Speak song names to find them
- **Location Tagging** _(Future)_ - Tag songs with location data
- **Social Sharing** _(Future)_ - Share favorites with friends

## 🚀 Advanced Library Features

### Smart Collections

**Auto-Generated Collections:**

- Recently Added (last 30 days)
- Most Played (usage-based)
- High Quality (excellent vocal separation)
- Complete Albums (full album collections)

**Maintenance Collections:**

- Needs Metadata (incomplete information)
- Processing Failed (requires attention)
- Low Quality (poor separation results)
- Orphaned Files (missing metadata)

### Integration Features

**External Service Sync:**

- iTunes metadata enhancement
- YouTube metadata updates
- Last.fm scrobbling _(Future)_
- Spotify playlist sync _(Future)_

**API Integration:**

- RESTful API for library access
- Webhook notifications for changes
- Third-party tool integration
- Custom application development

## 🔍 Troubleshooting Library Issues

### Common Problems

**Songs Not Appearing:**

- Check processing status in Jobs queue
- Verify file upload completed successfully
- Check for processing errors in logs
- Refresh browser or restart application

**Missing Metadata:**

- Use "Search iTunes" feature for automatic enhancement
- Manually edit song information
- Check original file metadata
- Verify internet connection for external lookups

**Poor Search Results:**

- Check spelling in search terms
- Try partial matches or alternative spellings
- Clear search filters that might be limiting results
- Verify songs exist in library

**Slow Library Loading:**

- Large libraries may take time to load
- Use search to find specific content quickly
- Consider archiving old or unused songs
- Check system performance and available memory

### Performance Optimization

**Large Library Management:**

- Use filtering and search instead of browsing all songs
- Consider archiving seasonal or occasional-use songs
- Organize by most-used artists and albums first
- Regular cleanup of failed or low-quality tracks

**Search Performance:**

- Use specific search terms rather than very broad ones
- Utilize artist or album filters when possible
- Clear browser cache if search becomes slow
- Report persistent performance issues

## 📈 Future Library Features

### Planned Enhancements

- **Machine Learning Recommendations** - Suggest similar songs
- **Advanced Analytics** - Usage patterns and insights
- **Collaborative Filtering** - Community-based recommendations
- **Playlist Generation** - AI-powered playlist creation

### Integration Roadmap

- **Streaming Service Integration** - Spotify, Apple Music sync
- **Social Features** - Share libraries and recommendations
- **Cloud Backup** - Automatic cloud synchronization
- **Multi-Device Sync** - Seamless cross-device experience

## 🔗 Related Features

- **[Uploading Songs](uploading-songs.md)** - Adding content to your library
- **[YouTube Integration](youtube-integration.md)** - Importing from YouTube
- **[Karaoke Sessions](karaoke-sessions.md)** - Using your organized library
- **[Advanced Features](advanced-features.md)** - Power user library tools

---

**Pro Tips:**

- Regularly update metadata for better organization
- Take advantage of automatic iTunes enhancement
- Keep your library clean with regular maintenance
