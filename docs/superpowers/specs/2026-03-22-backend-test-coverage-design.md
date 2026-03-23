# Backend Test Coverage — New Features (March 2026)

**Date:** 2026-03-22
**Scope:** pytest tests for uncommitted backend features added to the `develop` branch

---

## Context

Several new backend features were added in the past few days but have no test coverage yet. The recently merged `feature/metadata-enrichment` branch already shipped tests for AcoustID service, LastFM service, artist/album repositories, and the albums API. This spec covers the remaining gap: the uncommitted changes in songs API, YouTube API, song schemas, YouTube service, and Celery jobs.

---

## Features to Cover

| Area | Feature | File |
|---|---|---|
| Songs API | `GET /songs/by-fingerprint-status` | `backend/app/api/songs.py` |
| Songs API | `POST /songs/{id}/fingerprint` | `backend/app/api/songs.py` |
| Songs API | `POST /songs/{id}/replace-youtube` | `backend/app/api/songs.py` |
| Songs API | `POST /songs/{id}/replace-upload` | `backend/app/api/songs.py` |
| YouTube API | `GET /youtube/preview/{video_id}` | `backend/app/api/youtube.py` |
| Schema | `SongReplaceYouTubeRequest` | `backend/app/schemas/song.py` |
| Service | `YouTubeService.get_audio_preview_url()` | `backend/app/services/youtube_service.py` |
| Celery job | `fingerprint_single_song` task | `backend/app/jobs/jobs.py` |

---

## Approach

**Option B (chosen):** New focused test files per feature group, appending to existing files where appropriate. The new endpoints involve mocking Celery, `FileService`, and `YouTubeService` — a natural fit for the FastAPI mock-based test layer.

Testing patterns follow the existing codebase conventions:
- FastAPI tests: `TestClient` + `unittest.mock.patch` as context managers, class-based grouping
- Schema tests: direct Pydantic instantiation, `pytest.raises(ValidationError)`
- Jobs tests: import function directly, `@patch` decorators on dependencies

---

## Files to Create/Modify

### 1. `tests/fastapi/test_songs_fingerprint.py` *(new)*

**`TestGetSongsByFingerprintStatus`**
- Valid status `"not_checked"` → 200, returns list
- Invalid status `"garbage"` → 400
- `limit` / `offset` query params are accepted

**`TestFingerprintSingleSong`**
- Song exists → 202, response contains `taskId` and `status: "dispatched"`
- Song not found → 404

**`TestReplaceSongYouTube`**
- Happy path → 202, response contains `jobId` and `status: "pending"`
- Song not found → 404
- Active job already exists for song → 409
- Invalid `engine_type` in body → 422 (Pydantic validation fires before the handler runs)

**`TestReplaceSongUpload`**
- Valid audio file (content_type `audio/mpeg`) → 202
- Song not found → 404
- Non-audio content type → 400
- Invalid `engine_type` form field → 400
- Active job already exists for song → 409

Mocking strategy:
- `app.api.songs.SongRepository` — module-level import; mock `.fetch()` and `.update()`
- `app.repositories.JobRepository` — local import inside each handler; patch at source to intercept `.get_jobs_by_status()`, `.create()`, `.update()`
- `app.api.songs.FileService` — module-level import; mock `.delete_song_files()` and `.get_song_directory()` (return a `MagicMock` whose `__truediv__` returns a mock with a no-op `write_bytes`, to avoid filesystem writes in replace-upload)
- `app.services.youtube_service.YouTubeService` — local import inside `replace_song_youtube`; patch at source, mock `.download_and_process_async()` returning `"job-123"`
- `app.jobs.celery_app.celery` — patch the object at source; mock `.send_task()` for fingerprint and replace-upload endpoints

### 2. `tests/fastapi/test_youtube.py` *(append)*

**`TestYouTubePreview`** (new class at bottom of existing file)

Patch `app.api.youtube.YouTubeService`:
- Valid video ID → 302 with `Location` header pointing to the mocked stream URL
- `ValidationError` raised by service → 400
- `ServiceError` raised by service → 500
- Unexpected exception → 500

### 3. `tests/unit/test_schemas/test_song_schemas.py` *(append)*

**`TestSongReplaceYouTubeRequest`** (new class at bottom of existing file)
- Minimal valid request (only `video_id`) → fields populate correctly
- Full request with optional `title`, `artist`, `engine_type` → all set
- Default `engine_type` is `"three_track"`
- Invalid `engine_type` value → `ValidationError`
- `video_id` exceeding 100 characters → `ValidationError`

### 4. `tests/unit/test_services/test_youtube_service_unit.py` *(append)*

**`TestGetAudioPreviewUrl`** (new class at bottom of existing file)

Patch `yt_dlp.YoutubeDL` as context manager:
- `info["url"]` is present → returns the URL string
- `info["url"]` is `None` → raises `ServiceError`
- `yt_dlp.YoutubeDL.__enter__` raises exception → raises `ServiceError`

### 5. `tests/jobs/test_fingerprint_jobs.py` *(new)*

**Prerequisite fix:** `fingerprint_single_song` has a latent bug — it uses `get_db_session`, `SongRepository`, and `AcoustIdService` without importing them locally (unlike `batch_fingerprint_songs` which does import them). This causes a `NameError` at runtime. Before writing tests, add the missing local imports at the top of the function body:
```python
from app.db.database import get_db_session
from app.repositories.song_repository import SongRepository
from app.services.acoustid_service import AcoustIdService
```

Import `fingerprint_single_song` directly. Because these are **local imports** inside the function, patch at their source modules:
- `app.db.database.get_db_session` — mock as context manager yielding a mock session
- `app.services.acoustid_service.AcoustIdService` — mock the class so `.fingerprint_and_identify()` is controllable
- `app.repositories.song_repository.SongRepository` — mock `.update()`
- `pathlib.Path.exists` via `patch.object(pathlib.Path, "exists", ...)` — `Path` is also a local import; patching the method on the class directly is the correct approach

Cases:
- Instrumental file exists, vocals does not → uses instrumental path, calls `fingerprint_and_identify`, returns `{"status": "ok", "song_id": ...}`
- Only vocals file exists → uses vocals path, returns `{"status": "ok", ...}`
- Neither file exists → calls `SongRepository.update(song_id, acoustid_fingerprint_status="failed")`, returns `{"status": "no_audio", ...}`
- `fingerprint_and_identify` raises exception → exception is logged and swallowed, still returns `{"status": "ok", ...}`

---

## Out of Scope

- Frontend TypeScript changes (separate concern)
- Previously tested features from `feature/metadata-enrichment` merge
- WebSocket tests for these endpoints (no WS surface exposed)
- Performance or load testing
