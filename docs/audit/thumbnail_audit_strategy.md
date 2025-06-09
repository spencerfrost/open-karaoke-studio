# Thumbnail Resolution Audit Strategy for Open Karaoke Studio

## Objective
To systematically audit the resolution and presence of thumbnail images (`thumbnail.jpg`) for all songs in the `karaoke_library/` directory, identify low-quality or missing thumbnails, and generate a comprehensive report to guide future improvements.

---

## 1. Directory & File Structure Review
- Each song is stored in a UUID-named directory under `karaoke_library/`.
- Typical files per song:
  - `thumbnail.jpg` (target of audit)
  - `cover.jpg` (not the focus)
  - `metadata.json` (basic song metadata, may lack videoId)
  - `original.info.json` (YouTube-dl/yt-dlp info dump, always has videoId and thumbnail info)

## 2. Data Sources for Audit
- **Primary:** `thumbnail.jpg` in each song directory
- **Supplementary:**
  - `metadata.json` for song-level metadata
  - `original.info.json` for YouTube video ID and available thumbnail URLs/resolutions

## 3. Audit Script Strategy
### a. Directory Traversal
- Iterate through all subdirectories in `karaoke_library/`.
- For each, check for the presence of `thumbnail.jpg`.

### b. Image Resolution Extraction
- If `thumbnail.jpg` exists, use Python Pillow to read its width and height.
- If missing, flag as such in the report.

### c. Metadata Extraction
- Read `metadata.json` for song title, artist, and (if present) videoId.
- Read `original.info.json` for YouTube videoId (fallback if missing in metadata) and available thumbnail URLs/resolutions.

### d. Reporting
- For each song, record:
  - Song UUID (directory name)
  - Thumbnail file presence
  - Thumbnail resolution (width x height)
  - Video ID (from metadata or info dump)
  - Any issues (missing thumbnail, low-res, missing videoId)
- Output as CSV or JSON for easy review and filtering.

### e. Low-Resolution Threshold
- Define a threshold for “low-res” (e.g., width < 300px or height < 300px).
- Flag thumbnails below this threshold.

### f. Error Handling
- Log and continue on missing/corrupt files or malformed JSON.
- Report should be robust and not break on individual errors.

## 4. Optional Enhancements
- Cross-reference available YouTube thumbnails in `original.info.json` to suggest possible upgrades.
- Optionally, generate a summary of how many thumbnails are missing, low-res, or have missing video IDs.

## 5. Implementation Notes
- Script should be placed in `backend/scripts/` for consistency.
- Use Pillow for image inspection, standard Python JSON for metadata.
- No changes to the database or files—read-only audit.
- Can be run as a standalone script (CLI, not API endpoint).

---

## Example Report Row
| Song UUID | Thumbnail | Width | Height | Video ID | Issues |
|-----------|-----------|-------|--------|----------|--------|
| abc123    | present   | 120   | 90     | xyz789   | low-res |
| def456    | present   | 640   | 480    | abc123   |         |
| ghi789    | missing   |       |        | def456   | missing thumbnail |

---

## Summary
This strategy ensures a thorough, robust, and actionable audit of all song thumbnails, leveraging both local files and YouTube metadata. The resulting report will help prioritize which thumbnails need replacement or further attention.
