# Admin Features Backlog

A backlog of admin panel features to build, one at a time. Each item includes a description, the data involved, and the intended UI approach.

---

## 1. Data Quality Audit

**Goal:** Scan the song library for records with missing or obviously incorrect metadata and surface them for manual review.

**Issues to detect:**
- Empty or null `title` or `artist` fields
- Titles that look like raw YouTube video titles — contain patterns like "Official Music Video", "Official Video", "(HD)", "(Lyrics)", "(Audio)", "ft.", " - Topic", etc.
- Suspiciously long titles (> 80 characters) that were never cleaned up
- Title and artist fields that may be swapped (e.g., artist field looks like a song title)
- Songs with no `date_added` or `source` recorded
- Songs with special characters or encoding artifacts (unusual Unicode, garbled text)

**UI approach:**
- New "Data Quality" tab in Admin Panel
- "Run Scan" button (on-demand, like the Library Audit tab)
- Results list: each flagged song shows the issue label(s) as badges
- Clicking a row expands inline to the `SongActionPanel` for fixing metadata
- Summary bar showing issue counts by type

---

## 2. Duplicate Detection

**Goal:** Find songs that appear more than once in the library, likely downloaded multiple times.

**Detection logic:**
- Case-insensitive match on `title + artist` combination
- Group duplicates together

**UI approach:**
- On-demand scan with "Find Duplicates" button
- Results grouped by duplicate cluster (e.g., "3 versions of Song X")
- Each entry shows title, artist, date added, and total file size
- "Delete" button per entry — keeps the others, removes one
- No auto-selection of which to keep; user decides

---

## 3. Storage Analytics

**Goal:** Give visibility into how much disk space the library is using and where it's going, with tools to reclaim space.

**Data to surface:**
- Total library size
- Breakdown by file type: originals, vocals, instrumentals, thumbnails
- Top N largest songs by total directory size
- Songs where `original.mp3` is still present after successful processing (these are the biggest space savings — originals are large and not needed once separated)

**Actions:**
- "Delete Original" button per song — removes `original.mp3` only, leaves separated tracks intact
- Bulk "Delete All Originals for Processed Songs" option

**UI approach:**
- Summary cards at the top (total size, breakdown)
- Sortable table of songs by size
- Originals-still-present section with selective and bulk delete

---

## 4. Processing Health

**Goal:** Surface songs that are stuck in processing or have never been processed/fingerprinted.

**Issues to detect:**
- Songs with `status = "processing"` for longer than a configurable threshold (e.g., > 30 minutes) — likely stuck jobs
- Songs where `acoustid_fingerprint_status` is null — fingerprinting was never attempted
- Overall processing success/failure rate as a summary stat

**Actions:**
- "Retry" button on stuck songs — re-queues the processing job
- "Fingerprint" button on unfingerprinted songs

**UI approach:**
- Summary stats cards (stuck count, unfingerprinted count, success rate)
- Two lists: stuck songs and unfingerprinted songs
- Retry/fingerprint actions per row

---

## 5. Bulk Operations

**Goal:** Allow admins to perform actions on multiple songs at once instead of one at a time.

**Operations to support:**
- Bulk re-fingerprint
- Bulk delete
- Bulk reprocess (re-separate audio)

**UI approach:**
- Add checkbox column to existing song lists in the admin panel (Metadata Review, Data Quality, etc.)
- "Select All" / "Deselect All" toggle
- Floating action bar appears at bottom of screen when items are selected, showing available bulk actions
- Progress indicator during bulk operations (e.g., "Dispatching 12 of 47...")
- Results summary toast when complete

---

## Priority Order (suggested)

1. **Data Quality Audit** — most directly useful, complements the existing Library Audit
2. **Duplicate Detection** — common real-world problem, straightforward to build
3. **Storage Analytics** — useful housekeeping, especially the "delete originals" flow
4. **Processing Health** — good for debugging stuck jobs
5. **Bulk Operations** — quality-of-life improvement once the other tabs have content

---

*Last updated: 2026-03-23*
