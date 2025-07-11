# Migrating Song Duration to Milliseconds (ms) – Open Karaoke Studio

## Why Migrate to Milliseconds?

- **Precision:** Milliseconds are the industry standard for audio timing (used in DAWs, MIDI, lyric alignment, etc.).
- **Future-proof:** Enables accurate lyric syncing, waveform scrubbing, and advanced features.
- **Consistency:** Avoids lossy conversions and ambiguity between seconds, floats, and string formats.

## Migration Plan Overview

### 1. Backend Changes

- **Model:**
  - Change `duration` field in the `Song` model to `duration_ms` (integer, milliseconds).
  - Update all code to use and expect `duration_ms`.
- **Database:**
  - Write a migration to add `duration_ms` (int) to the songs table.
  - Backfill `duration_ms` from existing `duration` (multiply by 1000).
  - Remove the old `duration` field.
- **Audio Processing:**
  - After downloading/processing audio, use `librosa` or `ffmpeg` to measure the true duration in ms and save it to `duration_ms`.
- **API:**
  - All endpoints should send/receive `duration_ms` (int, ms) instead of `duration` (seconds).
  - Update OpenAPI/docs accordingly.

### 2. Frontend Changes

- **Types:**
  - Update all TypeScript interfaces to use `duration_ms: number`.
  - Remove `duration` fields.
- **UI:**
  - Create formatters to convert `duration_ms` to `mm:ss.SSS` or `mm:ss` for display.
  - Accept and pass ms everywhere in code, never seconds or strings. Only format right before rendering.
- **API Calls:**
  - Update all fetch/mutation calls to use `duration_ms`.

### 3. Data Migration

- **Write a script or Alembic migration** to:
  - Add `duration_ms` column.
  - For each song, set `duration_ms = duration * 1000` (if `duration` exists).
  - Remove the old `duration` column.

### 3.1 Data Migration Script

> **Do NOT** expose a bulk endpoint that processes all songs in one request. This is bad practice for reliability, error handling, and server load.

### Recommended Backend Endpoint (Flask)

```python
@migration_bp.route('/update_duration/<song_id>', methods=['POST'])
def update_duration(song_id):
    song = get_song_by_id(song_id)
    if not song:
        return jsonify({'error': 'Song not found'}), 404
    mp3_path = song.get('originalPath')
    if not mp3_path or not os.path.isfile(mp3_path):
        return jsonify({'error': 'File not found'}), 400
    # HIGH PRECISION: Use sample count, not float seconds
    try:
        y, sr = librosa.load(mp3_path, sr=None)
        duration_ms = int(round(len(y) * 1000 / sr))
        update_song_duration_ms(song_id, duration_ms)
        return jsonify({'song_id': song_id, 'duration_ms': duration_ms})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

### Migration Script (Client)

- Fetch all song IDs from the backend.
- For each song, POST to `/api/migration/update_duration/<song_id>` and wait for the response.
- Log errors and retry as needed.

**This is robust, RESTful, and production-grade.**

---

**This migration is essential for a modern, pro-level karaoke and audio app. Do it once, do it right.**

---

**This is the gold standard for duration accuracy.**
