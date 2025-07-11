# Enhancement: Add "Recently Added" Songs Row to Dual Display Library

## Summary

Add a persistent row of the most recently added songs to the dual display library interface. This row should always be visible above the search results grid, providing users with instant access to the latest additions to the music library, regardless of search state.

## Motivation

- **User Need:** Most users frequently access newly added songs. Currently, they must search or browse to find them, which is inefficient.
- **Efficiency:** Reduces friction for the most common user action—playing or selecting a recently added song.
- **Consistency:** Aligns with modern music library UX patterns (e.g., Spotify, Apple Music).

## Proposed Solution

- **UI:**
  - Add a horizontally scrollable (or responsive grid) row at the top of the song results section.
  - Display the N most recently added songs (configurable, e.g., 8-12).
  - Use the existing song card component for visual consistency.
- **Data:**
  - Fetch recent songs from the backend, ordered by `date_added` or similar field.
  - Add a new API endpoint if necessary (e.g., `/songs/recent?limit=12`).
- **Behavior:**
  - Always visible, even when no search query is present.
  - If a search is active, the row remains above search results.
  - Clicking a song card triggers the same actions as in the search results grid.

## Acceptance Criteria

- [ ] A new "Recently Added" row is visible at the top of the song results section.
- [ ] The row displays the most recently added songs, ordered by addition date.
- [ ] The row is responsive and works on all device sizes.
- [ ] Song cards in this row support play/select actions.
- [ ] The row is present regardless of search state.
- [ ] (Optional) The number of songs displayed is configurable.

## Out of Scope

- Advanced filtering or sorting of recent songs.
- UI for managing the number of recent songs shown (can be a config value).

## Additional Notes

- This enhancement leverages the existing song card and grid layout for consistency.
- Backend changes may be required to support efficient retrieval of recent songs.

---

**Related:** Dual Display Library Architecture, Song Search Results Grid
