**Issue Title:** Investigate YouTube Automatic Captions for AI-Generated/Synced Lyrics

**Issue Type:** 💡 Enhancement / 🔬 Research

**Labels:** `enhancement`, `lyrics`, `research`, `youtube-api`, `data-processing`, `AI-potential`

---

### Description

During the YouTube API response data prioritization, we noted the presence of `automatic_captions` within the raw YouTube data. While these are currently being stored in the raw JSON payload due to their potentially large size (up to 5000 lines for a single entry), we've identified a significant potential opportunity for generating lyrics and even synced lyrics for karaoke within our application.

**Problem/Opportunity:**
Our primary source for lyrics is a separate API. However, if that API fails to provide lyrics or synced lyrics for a specific track, YouTube's `automatic_captions` could serve as an invaluable fallback or even a primary source for AI-generated, time-aligned lyrics. This could drastically increase the number of songs with functional karaoke features.

**Current State:**
* `automatic_captions` data (and `subtitles`) from YouTube's `yt-dlp` output are currently stored as part of the `youtubeRawMetadata` JSON string on the `Song` model.
* The raw data contains URLs for these captions, but a quick manual check shows these URLs might not directly serve the content without further API interaction or authentication.
* The size of this data (e.g., 5000 lines) makes direct parsing and storage within the main `Song` model impractical without further processing.

**Proposed Solution / Next Steps (Research & Development):**

1.  **Feasibility Study:**
    * **Fetch Captions:** Investigate how to programmatically access and download the actual caption content from the URLs provided in the `automatic_captions` field. This may require specific YouTube Data API calls or `yt-dlp` features not yet explored.
    * **Format Analysis:** Understand the format of the downloaded captions (e.g., WebVTT, SRT, XML).
    * **Quality Assessment:** Evaluate the quality of the auto-generated captions for a diverse set of songs. How accurate are they? Are they typically time-synced?
    * **Sync Potential:** Determine if the captions inherently contain timing information that can be readily converted into our `syncedLyrics` format.

2.  **Processing & Storage Strategy (if feasible):**
    * If captions are high quality and parseable, design a separate processing pipeline to:
        * Extract `automatic_captions` for relevant languages (e.g., English).
        * Parse the caption content into a usable format (e.g., plain text lyrics, or timed lyric segments).
        * Potentially store the parsed, time-aligned lyrics in a dedicated field (e.g., `youtubeAutoLyrics: Optional[List[Dict[str, Any]]]`) on the `Song` model, separate from `lyrics` and `syncedLyrics` derived from the primary source.
        * Consider whether to apply further AI processing to refine auto-generated lyrics (e.g., punctuation, grammar, speaker separation - a future, more complex step).

3.  **Integration with Lyrics Fallback Logic:**
    * If successful, integrate this processed data into our lyrics retrieval logic, potentially making it a secondary or tertiary fallback for `lyrics` and `syncedLyrics`.

**Considerations/Challenges:**
* **API Rate Limits/Costs:** Fetching caption data via official APIs might incur costs or hit rate limits.
* **Data Volume:** While not stored directly on the main model, the processing of 5000-line entries for each song could be resource-intensive.
* **Caption Accuracy:** Auto-generated captions are not always perfect and may require sanitization or quality checks.
* **Language Support:** Focus initially on relevant languages (e.g., English).

**Goal:**
To determine the viability of utilizing YouTube's `automatic_captions` to augment or provide fallback lyrics, especially synced lyrics, thereby enriching the karaoke experience for a broader range of songs.