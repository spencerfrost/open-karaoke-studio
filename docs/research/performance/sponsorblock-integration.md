# Issue: SponsorBlock Integration for YouTube Media Filtering & Cropping

## Metadata
- **Type:** Enhancement
- **Priority:** High
- **Effort:** Medium (2-3 days implementation + testing)
- **Components:** Backend (Python/Flask), Audio Processing Pipeline
- **Related Issues:** #010, #011d, #005a

## 🎯 Summary
Implement SponsorBlock API integration to automatically filter out unusable YouTube music videos (with midroll/non-music segments) and crop intros/outros based on community segment data. This will improve lyric sync and user experience by ensuring only music content is processed and delivered.

## 📝 Background
- Current system relies on YouTube, which often includes non-music sections (intros, outros, midrolls, etc.) that cause lyric misalignment and poor karaoke experience.
- SponsorBlock provides a public API for segment data (intro, outro, sponsor, etc.) for YouTube videos.
- The API is open for use, with attribution required and no rate limits for reasonable use.

## 🛠️ Implementation Tasks
1. **Backend: SponsorBlock Fetch Utility**
   - Create a Python utility to fetch segment data for a given YouTube video ID using SponsorBlock's `/api/skipSegments` endpoint.
   - Parse and cache results for performance.
   - Handle API errors and missing data gracefully.
2. **Backend: Audio Processing Integration**
   - Integrate SponsorBlock data into the audio processing pipeline:
     - **Auto-reject** videos with midroll (non-music) segments (e.g., `music_offtopic`, `interaction`, etc. in the middle).
     - **Crop** intros/outros (categories: `intro`, `outro`) from the audio before separation.
   - Fallback to duration matching if no SponsorBlock data is available.
3. **Testing & Validation**
   - Test with a variety of real-world YouTube videos.
   - Ensure cropping is accurate and does not introduce artifacts.
   - Log and handle edge cases (e.g., no segments, ambiguous data).
4. **Documentation & Attribution**
   - Add clear attribution to SponsorBlock in the codebase and user-facing documentation as required by their license.
   - Optionally, notify SponsorBlock maintainers of our usage as requested in their API docs.

## ✅ Acceptance Criteria
- [ ] SponsorBlock segment data is fetched and cached for each processed YouTube video.
- [ ] Videos with midroll/non-music segments are auto-rejected.
- [ ] Intros/outros are cropped from audio using SponsorBlock timestamps.
- [ ] Fallback to duration matching if no SponsorBlock data is available.
- [ ] SponsorBlock is properly attributed in code and documentation.

## ⚠️ Risks & Considerations
- **Coverage:** Not all videos have SponsorBlock data; fallback logic is required.
- **Accuracy:** Cropping must be precise; test thoroughly to avoid cutting music content.
- **Legal:** Ensure SponsorBlock attribution and API usage guidelines are followed.
- **Performance:** Cache API results to minimize redundant calls and latency.

## 💎 Value Proposition
> "Increase the percentage of karaoke tracks that match official album versions and eliminate non-music sections, leveraging community-powered segment data for a seamless user experience."
