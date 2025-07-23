# Uploading Songs to Your Library

Learn how to add songs to your Open Karaoke Studio library through multiple methods.

## 🎵 Upload Methods

### 1. Local File Upload

**Supported Formats**: MP3, WAV, FLAC, M4A, AAC, OGG

**Steps:**

1. Navigate to the **Add** tab in the application
2. Click **"Choose Audio File"** or drag and drop your file
3. Fill in song metadata:
   - **Title** (required)
   - **Artist** (required)
   - **Album** (optional)
4. Click **"Create Karaoke Tracks"**
5. Monitor processing progress in the **Jobs** section

**Processing Time**: 2-5 minutes per song (depending on length and system performance)

### 2. YouTube Import

**Quick Import:**

1. Go to the **Add** tab
2. Paste a YouTube URL in the **YouTube URL** field
3. Click **"Import from YouTube"**
4. The system will automatically:
   - Download the audio
   - Extract metadata (title, artist, duration)
   - Begin vocal separation processing

**Bulk Import:**

- Paste multiple YouTube URLs (one per line)
- Click **"Import All"** to process multiple songs

### 3. iTunes Metadata Enhancement

**Automatic Enhancement:**

- When uploading any song, the system searches iTunes for matching metadata
- If found, it automatically adds:
  - Official artwork
  - Album information
  - Release year
  - Genre classification

**Manual Enhancement:**

1. Upload your song normally
2. In the song library, click on a song
3. Click **"Edit Metadata"**
4. Click **"Search iTunes"** to find and apply official metadata

## 📊 Processing Workflow

### Stage 1: Upload & Validation

- File format validation
- Basic metadata extraction
- Audio quality check

### Stage 2: Metadata Enhancement

- iTunes API search
- YouTube metadata extraction (if applicable)
- Thumbnail generation

### Stage 3: Vocal Separation

- AI-powered processing with Demucs
- Creates separate vocal and instrumental tracks
- Quality optimization

### Stage 4: Library Integration

- Final metadata application
- File organization
- Search index update

## 🎯 Best Practices

### Audio Quality

- **Recommended**: 320kbps MP3 or higher
- **Minimum**: 128kbps for acceptable results
- **Optimal**: WAV or FLAC for best vocal separation

### Metadata Tips

- Use consistent artist naming (e.g., "The Beatles" not "Beatles")
- Include album names for better organization
- Add genre tags when available

### Batch Processing

- Upload multiple songs simultaneously
- Monitor the Jobs queue for processing status
- Processing happens in the background - you can continue using the app

## 🔍 Troubleshooting

### Upload Fails

- **Check file format** - Ensure it's a supported audio format
- **File size** - Very large files (>100MB) may timeout
- **Connection** - Ensure stable internet connection

### Processing Stuck

- Check the **Jobs** section for error details
- Some files may fail due to unusual audio encoding
- Retry with a different file format if needed

### Poor Separation Quality

- Higher quality input files produce better results
- Songs with heavy reverb or compression may not separate cleanly
- Live recordings typically produce mixed results

### YouTube Import Issues

- **Invalid URL** - Ensure the URL is accessible and not private/restricted
- **Copyright restrictions** - Some videos may be blocked from download
- **Age restrictions** - Sign-in required videos cannot be processed

## 📱 Mobile Usage

### Uploading from Mobile

- Use the file picker to select audio files from your device
- Cloud storage integration works (Google Drive, iCloud, etc.)
- Processing happens on the server - your device won't be slowed down

### YouTube Import on Mobile

- Copy YouTube URLs from the YouTube app
- Paste directly into Open Karaoke Studio
- Processing status is available in real-time

## 🚀 Advanced Features

### Custom Metadata

- Edit any song's metadata after upload
- Add custom tags and categories

### Library Organization

- Songs are automatically organized by artist and album
- Use search to find specific tracks quickly
- Filter by processing status, or custom tags

### Background Processing

- Multiple songs can be processed simultaneously
- Background jobs continue even if you close the browser
- Real-time progress updates via WebSocket connections

## 🔗 Related Features

- **[Library Management](library-management.md)** - Organizing your music collection
- **[Karaoke Sessions](karaoke-sessions.md)** - Using your uploaded songs
- **[Advanced Features](advanced-features.md)** - Power user capabilities

---

**Next Steps**: Once you've uploaded your first few songs, learn how to [organize your library](library-management.md) and start [hosting karaoke sessions](karaoke-sessions.md).
