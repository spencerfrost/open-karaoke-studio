# YouTube Music Official Audio Search Integration

## Overview

This document outlines a new feature for Open Karaoke Studio: **searching for official audio tracks on YouTube Music** (not just regular YouTube) and integrating those results into the existing download pipeline. This will dramatically improve the quality and reliability of karaoke tracks by prioritizing official, high-quality sources over random user uploads or music videos.

## Motivation

- **Current Limitation:** The current backend uses yt-dlp's `ytsearch` to search regular YouTube, which returns a mix of music videos, lyric videos, unofficial uploads, and sometimes low-quality or incomplete tracks.
- **Goal:** Only show and download official audio tracks ("songs") from YouTube Music, avoiding music videos and unofficial content.

## Solution Summary

- **Use [`ytmusicapi`](https://ytmusicapi.readthedocs.io/en/latest/)** for searching YouTube Music and filtering for "songs" (official audio).
- **Hand off the resulting videoId to yt-dlp** for downloading the actual audio file, preserving the existing download and processing pipeline.

## Implementation Plan

### 1. Backend Changes

- **Add ytmusicapi as a dependency** in `backend/requirements.txt`.
- **Create a new service module** (e.g., `youtube_music_service.py`) that:
  - Uses ytmusicapi to search YouTube Music for a query.
  - Filters results to only include type `"song"` (official audio).
  - Returns a list of results with metadata (title, artist, videoId, duration, etc.).
- **Update the main YouTubeService** to:
  - Add a new method (e.g., `search_youtube_music_songs`) that calls the new service.
  - Optionally, allow the frontend to choose between regular YouTube and YouTube Music search.
  - When a user selects a result, use the videoId with yt-dlp to download the audio as before.

### 2. API Contract

- **New endpoint:** `GET /api/youtube-music/search?q=...`
  - Returns: List of song results (with videoId, title, artist, duration, etc.)
- **Existing download endpoint:** Accepts a videoId from YouTube Music and downloads via yt-dlp.
- **TypeScript interface:** Update frontend types to match new response shape.

### 3. Frontend Changes

- **Add a toggle or new search mode** for "YouTube Music (Official Audio)" in the search UI.
- **Display results with clear indication** that they are official audio tracks.
- **Handle loading and error states** as per project standards.

## Example Workflow

1. User searches for a song with the "YouTube Music" option enabled.
2. Backend uses ytmusicapi to fetch only official audio tracks.
3. User selects a result; frontend sends the videoId to the backend for download.
4. Backend uses yt-dlp to download the audio and process as usual.

## Benefits

- **Higher quality, more reliable karaoke tracks**
- **Less manual curation needed**
- **Cleaner, more professional user experience**

## References

- [ytmusicapi documentation](https://ytmusicapi.readthedocs.io/en/latest/)
- [yt-dlp documentation](https://github.com/yt-dlp/yt-dlp)

---

**Blunt reality:** If you want "official audio" only, this is the only robust way. yt-dlp alone cannot do it. If you skip this, you'll keep getting garbage results.
