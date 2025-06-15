# YouTube Integration

Open Karaoke Studio seamlessly integrates with YouTube, allowing you to import songs directly from YouTube videos and automatically process them into karaoke tracks.

## 🎬 How YouTube Integration Works

### Automatic Processing Pipeline
1. **Video Download** - Downloads audio from YouTube using yt-dlp
2. **Metadata Extraction** - Automatically extracts title, artist, duration
3. **Thumbnail Processing** - Downloads and processes video thumbnails
4. **Audio Conversion** - Converts to optimal format for vocal separation
5. **AI Processing** - Applies Demucs vocal separation
6. **Library Integration** - Adds to your song library with rich metadata

## 🔗 Importing from YouTube

### Single Video Import

**Method 1: Direct URL**
1. Copy a YouTube video URL
2. Navigate to the **Add** tab
3. Paste the URL in the **YouTube URL** field
4. Click **"Import from YouTube"**

**Method 2: Search Integration** *(Coming Soon)*
- Search directly within the app
- Preview results before importing
- Batch select multiple videos

### Supported YouTube URL Formats
```
https://www.youtube.com/watch?v=VIDEO_ID
https://youtu.be/VIDEO_ID
https://www.youtube.com/watch?v=VIDEO_ID&t=30s
https://music.youtube.com/watch?v=VIDEO_ID
```

### Bulk Import
- Paste multiple URLs (one per line) in the text area
- Click **"Import All"** to process multiple videos
- Monitor progress in the Jobs queue

## 📊 Metadata Enhancement

### Automatic Metadata Extraction
YouTube integration automatically captures:

- **Video Title** → Song Title
- **Channel Name** → Artist (when appropriate)
- **Video Duration** → Track Length
- **Upload Date** → Import Date
- **Video Description** → Additional metadata parsing
- **Thumbnails** → Multiple resolution cover art

### Smart Metadata Processing
The system intelligently processes video titles to extract:
- Artist and song names from formatted titles
- Album information when present
- Featured artists and collaborations
- Release years and versions

**Example Transformations:**
```
"Queen - Bohemian Rhapsody (Official Video)" 
→ Artist: "Queen", Title: "Bohemian Rhapsody"

"Ed Sheeran - Shape of You [Official Audio]"
→ Artist: "Ed Sheeran", Title: "Shape of You"

"Various Artists - Song Title (Album Version)"
→ Artist: "Various Artists", Title: "Song Title"
```

## 🎵 Audio Quality Considerations

### Quality Optimization
- **Default Quality**: Downloads highest available audio quality
- **Format Preference**: Automatically selects optimal audio format
- **Processing Enhancement**: Post-download audio optimization

### Expected Results
- **Music Videos**: Generally excellent vocal separation
- **Live Performances**: Variable results depending on recording quality
- **Covers/Acoustic**: Often excellent for vocal separation
- **Electronic/Synthesized**: Results vary based on original production

## 🚫 Limitations & Restrictions

### Content Restrictions
- **Copyright Protected**: Some videos may be blocked from download
- **Age Restricted**: Videos requiring sign-in cannot be processed
- **Private/Unlisted**: Only public videos can be imported
- **Geographic Restrictions**: Region-locked content may not be available

### Technical Limitations
- **Maximum Duration**: Very long videos (>2 hours) may timeout
- **Live Streams**: Cannot process live or ongoing streams
- **Premium Content**: YouTube Premium exclusive content cannot be accessed

## 🔧 Advanced YouTube Features

### Metadata Override
After import, you can:
- Edit extracted metadata
- Add additional tags and information
- Correct artist/title mismatches
- Add album and genre information

### Playlist Processing *(Future Feature)*
- Import entire YouTube playlists
- Batch metadata processing
- Smart duplicate detection
- Playlist organization preservation

### Channel Integration *(Future Feature)*
- Subscribe to artist channels
- Automatic import of new releases
- Channel-based organization
- Release notifications

## 📱 Mobile YouTube Integration

### Mobile Workflow
1. **Find Video**: Use the YouTube mobile app
2. **Share URL**: Tap "Share" → "Copy Link"
3. **Import**: Paste in Open Karaoke Studio mobile interface
4. **Process**: Monitor progress on your phone or computer

### Cross-Device Sync
- Import on mobile, process on server
- Access results on any device
- Real-time processing updates

## 🔍 Troubleshooting YouTube Import

### Common Issues

**"Video Unavailable" Error**
- Video may be private, deleted, or restricted
- Try accessing the video directly in a browser first
- Check for geographic restrictions

**"Download Failed" Error**
- Video may have download restrictions
- Try a different video from the same artist
- Check internet connection stability

**Poor Audio Quality**
- Source video may have low audio quality
- Music videos typically work better than live performances
- Try finding an official audio version

**Metadata Extraction Issues**
- Some video titles don't follow standard formats
- Manual metadata editing is available after import
- Use the iTunes search feature for official metadata

### Performance Tips

**For Best Results:**
- Use official music videos or audio uploads
- Avoid live performances with crowd noise
- Choose videos with clear artist/title information
- Prefer higher quality video sources

**Processing Optimization:**
- Import during off-peak hours for faster processing
- Process one video at a time for immediate results
- Use bulk import for large collections during maintenance windows

## 🎯 Best Practices

### Content Selection
- **Official Channels**: Prefer official artist channels
- **Audio Quality**: Choose "Official Audio" or "Official Video" when available
- **Version Selection**: Studio versions typically separate better than live versions

### Library Organization
- Use consistent naming conventions
- Group by artist or album after import
- Tag favorites for quick access
- Regular metadata cleanup and enhancement

### Legal Considerations
- Respect copyright and fair use guidelines
- Use imported content for personal karaoke only
- Support artists through official channels
- Remove content if requested by copyright holders

## 🔗 Integration with Other Features

### iTunes Metadata Enhancement
- After YouTube import, the system automatically searches iTunes
- Adds official album art and metadata when available
- Combines YouTube and iTunes data for comprehensive information

### Real-time Queue Integration
- Imported songs are immediately available for queue addition
- No need to wait for complete processing to start using
- Background processing continues during karaoke sessions

### Search and Discovery
- YouTube-imported songs are indexed for search
- Metadata tags improve discoverability
- Integration with library browsing and filtering

## 📈 Future Enhancements

### Planned Features
- **Playlist Import**: Import entire YouTube playlists
- **Channel Monitoring**: Auto-import from subscribed channels
- **Quality Selection**: Choose specific audio quality/format
- **Preview Mode**: Preview before full import
- **Smart Suggestions**: Recommend related videos for import

### Integration Improvements
- **Spotify Integration**: Cross-reference with Spotify metadata
- **Last.fm Integration**: Enhanced metadata and tags
- **Lyrics Integration**: Automatic lyrics fetching for imported songs
- **Social Features**: Share and discover YouTube imports from other users

---

**Related Guides:**
- **[Uploading Songs](uploading-songs.md)** - Other methods to add music
- **[Library Management](library-management.md)** - Organizing imported content
- **[Advanced Features](advanced-features.md)** - Power user YouTube features
