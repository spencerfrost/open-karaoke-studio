# SongRepository Migration Plan

## Overview

This document tracks the migration from legacy song operations to a new, flexible `SongRepository` in the Open Karaoke Studio backend. It will be updated as we progress.

---

## 1. Implement SongRepository

- [ ] Create `backend/app/repositories/song_repository.py` with CRUD and query methods:
  - `create(song_data)`
  - `fetch(song_id)`
  - `fetch_all(**filters)`
  - `update(song_id, **fields)`
  - `delete(song_id)`
  - (Optional) `search(query, **params)` for advanced/fuzzy search

## 2. Audit Existing Song Operations

- [ ] List all functions in `backend/app/db/song_operations.py`:
  - `get_songs`
  - `get_song`
  - `create_or_update_song`
  - `delete_song`
  - `update_song_audio_paths`
  - `update_song_with_metadata`
  - `update_song_thumbnail`
  - `get_artists_with_counts`
  - `get_artists_total_count`
  - `get_songs_by_artist`
  - `search_songs_paginated`
- [ ] Search for all usages of these functions in the codebase (API, jobs, services, etc.)

## 3. Update Codebase to Use SongRepository

- [ ] Replace usages of old functions with repository methods in:
  - `backend/app/api/songs.py`
  - `backend/app/jobs/jobs.py`
  - Any other relevant modules

## 4. Remove/Deprecate Old Functions

- [ ] Remove or deprecate legacy functions in `song_operations.py` after migration.

## 5. Test and Validate

- [ ] Test all endpoints and jobs for correct song CRUD behavior.
- [ ] Pay special attention to PATCH, metadata updates, and YouTube job flows.

---

## Progress Log

### 2025-07-06

- [x] Implemented `SongRepository` with CRUD and query methods in `backend/app/repositories/song_repository.py`.
- [x] Updated integration tests to use backend-generated IDs and new API contract.
- [x] Patched API endpoints to use repository for create, update, delete, and fetch operations.
- [x] Validated that all main CRUD tests pass (except for unicode test, which needs test data).
- [x] Identified all legacy usages of song operations in the codebase (see summary table below).
- [x] Migrated all main API endpoint usages of get_song and get_songs to SongRepository in api/songs.py.
- [x] Migrated all script usages of get_songs to SongRepository (data integrity, cleanup, lyrics, duplicates scripts).
- [x] Migrated get_song usage in jobs/jobs.py (YouTube job process) to SongRepository.
- [ ] Migration of other legacy usages to repository methods is in progress (e.g., update_song_with_metadata, delete_song, artist endpoints, etc.).
- [ ] Plan to remove/deprecate legacy functions after migration is complete.

#### Migration Status Summary

- **Already migrated to SongRepository:**

  - Main API endpoints for song CRUD in `api/songs.py` (create, fetch, update, delete).
  - All script usages of get_songs (data integrity, cleanup, lyrics, duplicates) migrated.
  - All get_song usages in jobs/jobs.py migrated.

**Still need migration (auto-checked as of 2025-07-06):**

- `delete_song`, `update_song_with_metadata` in `api/songs.py` (still import/use legacy functions)
- `get_songs`, `get_song` in `utils/error_handlers.py` and `utils/validation.py` (still defined/used)
- `create_or_update_song`, `update_song_audio_paths`, `update_song_with_metadata`, `update_song_thumbnail` in `jobs/jobs.py` and `services/youtube_service.py` (still import/use legacy functions)
- `get_artists_with_counts`, `get_artists_total_count`, `get_songs_by_artist`, `search_songs_paginated` in `api/songs_artists.py` and related files (still defined/used)

The main API endpoints for song CRUD are migrated. All other usages (especially in jobs, services, and artist-related endpoints) still need to be migrated to use the repository.

## Legacy Song Operation Usages (Summary Table)

| Function                    | Main Usages (files/lines)                                                                                       |
| --------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `get_songs`                 | `song_operations.py`, `api/songs.py`, `utils/error_handlers.py`, `utils/validation.py`                          |
| `get_song`                  | `song_operations.py`, `api/songs.py`                                                                            |
| `create_or_update_song`     | `song_operations.py`, `db/__init__.py`, `services/youtube_service.py`, `services/interfaces/youtube_service.py` |
| `delete_song`               | `song_operations.py`, `api/songs.py`, `services/file_service.py`, `services/interfaces/file_service.py`         |
| `update_song_audio_paths`   | `song_operations.py`, `jobs/jobs.py`                                                                            |
| `update_song_with_metadata` | `song_operations.py`, `api/songs.py`                                                                            |
| `update_song_thumbnail`     | `song_operations.py`, `services/youtube_service.py`                                                             |
| `get_artists_with_counts`   | `song_operations.py`, `api/songs_artists.py`                                                                    |
| `get_artists_total_count`   | `song_operations.py`, `api/songs_artists.py`                                                                    |
| `get_songs_by_artist`       | `song_operations.py`, `api/songs_artists.py`                                                                    |
| `search_songs_paginated`    | `song_operations.py`, `api/songs_artists.py`                                                                    |

- _Add notes, blockers, and decisions here as we go._

---

## TODO

- [ ] Scaffold `SongRepository` class
- [ ] Enumerate all usages of legacy song operations
- [ ] Begin incremental migration
