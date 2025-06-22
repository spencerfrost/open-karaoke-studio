# YouTube Music "Add to Library" Flow – Open Karaoke Studio

## Overview

This document outlines the precise sequence of events and architectural decisions for the new YouTube Music "Add to Library" flow. This approach maximizes user experience, metadata quality, and reliability by leveraging official YouTube Music data, iTunes metadata, and lyrics APIs in parallel.

---

## Sequence of Events

1. **User clicks “Add to Library” on a YouTube Music result.**

2. **Immediately (in parallel, without waiting for responses):**
   - **Trigger the download process:**
     - Send videoId, artist, title, and album to the backend.
     - Backend starts the download (yt-dlp pipeline).
   - **Trigger a metadata service endpoint:**
     - Send artist, title, and album to the backend.
     - Backend fetches iTunes metadata and saves the first result to the song (no user interaction, no result returned to frontend).
   - **On the frontend:**
     - Open a lyrics selection dialog immediately.
     - Fire a lyrics search using artist, title, and album.
     - Show lyrics options as soon as they load.
     - User selects lyrics and closes the dialog.
     - (Optionally: auto-select the lyrics closest in duration to the track, as in the YouTube search flow.)

---

## Key Principles

- **Download and metadata requests are fire-and-forget:**
  - User does not wait for these; they are handled entirely by the backend.
- **Lyrics selection is the only user-facing step:**
  - Dialog pops up immediately, lyrics are fetched in the background, user picks one and closes.
- **All three requests (download, metadata, lyrics) are triggered in parallel** as soon as the user clicks “Add to Library.”
- **No unnecessary user friction:**
  - The only thing the user sees is the lyrics dialog, and it’s as fast as possible.

---

## Implementation Notes

- Backend should provide a single endpoint that fetches and saves iTunes metadata in one go, not returning it to the frontend.
- Frontend lyrics dialog should use the same logic as the YouTube search flow, including auto-selecting the best match by duration.
- UI should not block or wait for download/metadata; only lyrics selection is interactive.

---

## Benefits

- **High-quality, official audio** from YouTube Music.
- **Accurate, rich metadata** from iTunes, auto-saved with no user friction.
- **Fast, low-friction lyrics selection** for the user.
- **All actions are parallelized for speed and reliability.**

---

## Example Timeline

1. User clicks “Add to Library.”
2. Download and metadata requests are sent to backend (fire-and-forget).
3. Lyrics dialog opens instantly; lyrics search is triggered.
4. User selects lyrics and closes dialog.
5. Song is now fully processed with official audio, rich metadata, and user-selected lyrics.

---

**This is the gold standard for a modern, low-friction, high-quality karaoke library workflow.**
