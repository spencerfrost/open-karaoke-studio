# Your First Song - Tutorial

Congratulations on setting up Open Karaoke Studio! This tutorial will walk you through processing your first song from start to finish.

## 🎯 What You'll Learn

By the end of this tutorial, you'll know how to:
- Upload or import a song from YouTube
- Monitor the processing progress
- Access your generated karaoke tracks
- Understand the different file types created

**Time needed:** 5-10 minutes (plus processing time)

## 🚀 Prerequisites

- ✅ Open Karaoke Studio installed and running ([Installation Guide](installation.md))
- ✅ Backend accessible at http://localhost:5000
- ✅ Frontend accessible at http://localhost:5173
- 🎵 A song file (MP3, WAV, etc.) or YouTube URL ready

## 📋 Step-by-Step Tutorial

### Step 1: Open the Application

1. **Start both services** (if not already running):
   ```bash
   # Terminal 1 - Backend
   cd backend && ./run_api.sh
   
   # Terminal 2 - Frontend  
   cd frontend && pnpm dev
   ```

2. **Open your browser** and go to: http://localhost:5173

3. **Verify it's working**: You should see the Open Karaoke Studio interface

### Step 2: Choose Your Song Source

You have two options for adding songs:

#### Option A: Upload a Local File
1. Click the **"Upload Song"** button
2. Select an audio file from your computer (MP3, WAV, FLAC, etc.)
3. Wait for the upload to complete

#### Option B: Import from YouTube
1. Click the **"Import from YouTube"** button  
2. Paste a YouTube URL (e.g., `https://www.youtube.com/watch?v=VIDEO_ID`)
3. Click **"Import"**
4. Wait for the download to complete

**Recommendation:** Start with a 3-4 minute song for your first attempt.

### Step 3: Monitor Processing Progress

1. **Processing starts automatically** after upload/import
2. **Watch the progress bar** - this shows the AI vocal separation progress
3. **Processing time varies**:
   - **With GPU**: 30 seconds - 2 minutes
   - **CPU only**: 2-10 minutes (depending on song length and CPU power)

**What's happening behind the scenes:**
- Audio is being analyzed by the Demucs AI model
- Vocals are separated from instruments  
- Metadata is being enriched from online sources
- File organization is happening

### Step 4: Explore Your Results

Once processing completes, you'll see your song in the library with:

#### Generated Files
- **🎤 Vocals Track** (`vocals.mp3`) - Isolated vocals only
- **🎸 Instrumental Track** (`instrumental.mp3`) - Karaoke track (no vocals)
- **🎵 Original** (`original.mp3`) - Your original audio
- **🖼️ Artwork** (`thumbnail.jpg`) - Album cover/thumbnail

#### Metadata Information
- **Song Title** - Automatically detected or from YouTube
- **Artist Name** - From metadata sources
- **Album** - If available from online sources
- **Duration** - Length of the track
- **Year** - Release year if found

### Step 5: Test Your Karaoke Track

1. **Click on your song** in the library
2. **Preview the tracks**:
   - Click **"Play Instrumental"** - This is your karaoke track!
   - Click **"Play Vocals"** - Hear just the vocals
   - Click **"Play Original"** - Compare with the original

3. **Download if needed**:
   - Click the download icon next to any track
   - Files are saved to your downloads folder

## 🎵 Understanding the Results

### What Makes a Good Karaoke Track?

**Excellent separation:**
- Vocals completely removed from instrumental
- No vocal "bleeding" in the karaoke track
- Clear instrumental quality

**Good separation:**
- Most vocals removed
- Slight vocal traces may remain (normal for complex mixes)
- Instrumental sounds clean

**Challenging songs:**
- Live recordings (audience noise, reverb)
- Heavy vocal effects (auto-tune, heavy reverb)
- Acoustic songs (vocals and instruments overlap)

### Audio Quality Tips

**Best results with:**
- Studio recordings
- Clear vocal/instrument separation
- Modern production (post-1980s)
- Rock, pop, hip-hop genres

**May need adjustment:**
- Classical music (overlapping instruments)
- Jazz (vocal/instrument improvisation)
- Heavily processed vocals

## ✅ Success Checklist

After your first song, verify:

- [ ] Song appears in your library
- [ ] Instrumental track plays without vocals
- [ ] Vocal track contains only vocals
- [ ] Metadata looks correct (title, artist, etc.)
- [ ] You can download the files
- [ ] Processing completed without errors

## 🚀 Next Steps

**Congratulations!** You've successfully processed your first song. Now you can:

### Explore More Features
- **[YouTube Integration](../user-guide/youtube-integration.md)** - Search and import directly
- **[Library Management](../user-guide/library-management.md)** - Organize your collection
- **[Batch Processing](../user-guide/advanced-features.md)** - Process multiple songs

### Improve Your Results
- **[Audio Quality Tips](../features/audio-processing.md)** - Get better separations
- **[Metadata Management](../user-guide/library-management.md)** - Fix song information
- **[Troubleshooting](troubleshooting.md)** - Solve common issues

### Power User Features
- **[Karaoke Sessions](../user-guide/karaoke-sessions.md)** - Use the real-time queue
- **[API Integration](../api/README.md)** - Automate your workflow
- **[Custom Configuration](../deployment/configuration.md)** - Optimize settings

## 🛠️ Troubleshooting Your First Song

### Processing Stuck or Failed

**Check the logs:**
```bash
# Backend logs
tail -f backend/logs/app.log

# Look for error messages
```

**Common solutions:**
- Restart the backend service
- Try a different song (simpler format)
- Check available disk space
- Verify internet connection (for YouTube imports)

### Poor Separation Quality

**Try these songs for better results:**
- Popular rock/pop songs (e.g., "Sweet Child O' Mine" - Guns N' Roses)
- Clear studio recordings
- Songs with distinct vocal/instrumental parts

**Avoid initially:**
- Live recordings
- Acoustic songs
- Classical music
- Songs with heavy vocal effects

### No Audio Playback

**Browser issues:**
- Try a different browser (Chrome recommended)
- Check browser audio permissions
- Verify audio format support

**File issues:**
- Check if files were generated in `karaoke_library/`
- Verify file permissions
- Try downloading and playing locally

## 🎉 What's Next?

You've mastered the basics! Ready to explore more?

- **[User Guide](../user-guide/README.md)** - Complete feature walkthrough
- **[Advanced Features](../user-guide/advanced-features.md)** - Power user capabilities  
- **[Development](../development/README.md)** - Contribute to the project

---

**Questions?** 
- 💬 [Troubleshooting Guide](troubleshooting.md)
- 🐛 [Report Issues](../development/contributing/issue-reporting.md)
- 📖 [Full User Guide](../user-guide/README.md)
