# Getting Started with Open Karaoke Studio

Welcome! This guide will help you set up and start using Open Karaoke Studio to create karaoke tracks from your favorite songs.

## 🎯 What You'll Achieve

By the end of this guide, you'll have:
- ✅ Open Karaoke Studio running locally
- ✅ Processed your first song into karaoke tracks
- ✅ Understanding of core features and workflows

## 📋 Quick Start Options

### Option 1: I Want to Try It Now (Recommended)
**Time: ~10 minutes**
- [Complete Installation Guide](installation.md) - Full setup with all features
- [First Song Tutorial](first-song.md) - Process a song end-to-end

### Option 2: I Want to Understand First
**Time: ~5 minutes reading**
- [Project Overview](../architecture/project-overview.md) - What is Open Karaoke Studio?
- [Features Overview](../features/README.md) - What can it do?

### Option 3: I'm Having Issues
- [Troubleshooting Guide](troubleshooting.md) - Common setup problems
- [System Requirements](#system-requirements) - Check compatibility

## 🎵 What Open Karaoke Studio Does

Open Karaoke Studio transforms regular songs into karaoke tracks using AI:

1. **Input**: Upload an audio file or YouTube URL
2. **Processing**: AI separates vocals from instruments
3. **Output**: Get separate vocal and instrumental tracks
4. **Bonus**: Automatic metadata, lyrics, and artwork

### Real Example
```
Input:  "Song.mp3" (original song)
Output: "vocals.mp3" (isolated vocals)
        "instrumental.mp3" (karaoke track)
        "thumbnail.jpg" (album artwork)
        "lyrics.txt" (song lyrics)
```

## 🖥️ System Requirements

### Minimum Requirements
- **OS**: Windows 10+, macOS 10.15+, or Linux
- **RAM**: 4GB (8GB recommended)
- **Storage**: 2GB free space + space for your music library
- **Network**: Internet connection for YouTube/metadata features

### Recommended for Best Performance
- **CPU**: Multi-core processor (faster processing)
- **GPU**: CUDA-compatible GPU (10x faster vocal separation)
- **RAM**: 8GB+ (handle larger audio files)
- **Storage**: SSD (faster file operations)

### Software Dependencies
- **Node.js** 16+ (for frontend)
- **Python** 3.10+ (for backend)
- **pnpm** (package manager)
- **Redis** (for background jobs)
- **FFmpeg** (for audio processing)

*Don't worry - the installation guide covers installing all of these!*

## 🚀 Next Steps

### Ready to Install?
**→ [Complete Installation Guide](installation.md)**

### Want a Quick Demo?
If you prefer to see it in action first:
1. Check out screenshots in the [User Guide](../user-guide/README.md)
2. Review the [feature overview](../features/README.md)
3. Then come back to [install](installation.md)

### Having Problems?
- **Setup issues**: [Troubleshooting Guide](troubleshooting.md)
- **Questions**: [Development FAQ](../development/contributing/README.md#faq)
- **Bugs**: [Issue Reporting](../development/contributing/issue-reporting.md)

## 📚 Related Documentation

After you get started:
- **[User Guide](../user-guide/README.md)** - Learn all features
- **[API Documentation](../api/README.md)** - For developers
- **[Development Guide](../development/README.md)** - To contribute

---

**Time Investment**: 
- **Just trying it**: 15 minutes
- **Regular use**: 30 minutes to learn features  
- **Power user**: 1 hour to master advanced features

**Next**: [Install Open Karaoke Studio →](installation.md)
