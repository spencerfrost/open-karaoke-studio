# Enhanced YouTube Music Search — Artist Browse + Albums

Goal
- Let users click an artist in YouTube Music search results and explore that artist's top songs and albums, with the ability to expand albums to see tracks and add any track to the existing Add-to-Library flow.

Scope
- Backend: new endpoints to browse artist and album data from ytmusicapi (or fallback to search / hybrid metadata). Return stable artist/album ids (browseId) and normalized track objects containing videoId when available.
- Frontend: clickable artist names in search results, an Artist Browse panel with Top Songs and Albums (albums expandable to show tracks), hooks for the new endpoints, and types.
- UX: breadcrumb/back navigation to return to previous search context; reuse existing Add-to-Library flow (createSong -> start download -> stepper dialog).

Checklist
- Clicking an artist shows that artist's top songs.
- Albums are presented as an expandable list; expanding an album loads tracks and shows Add buttons for each track.
- Backend returns artist ids (browseId) so frontend can request artist/album data reliably.
- Fallback/hybrid metadata (iTunes) used only when ytmusicapi returns insufficient album metadata.

API contract (examples)
- GET /api/youtube-music/artist/:artistId?limitTop=12
	- Response:
		{
			"artist": { "id": "ARTIST_ID", "name": "Artist Name", "thumbnails": [...] },
			"topSongs": [ { videoId, title, artist, duration, album?, thumbnails } ],
			"error": null
		}

- GET /api/youtube-music/artist/:artistId/albums
	- Response:
		{
			"albums": [ { "id": "ALBUM_ID", "title": "Album", "year": 2021, "thumbnails": [...], "trackCount": 10 } ],
			"error": null
		}

- GET /api/youtube-music/album/:albumId/tracks
	- Response:
		{ "tracks": [ { videoId, title, trackNumber, duration, thumbnails } ], "error": null }

Backend changes (files to modify)
- `backend/app/services/youtube_music_service.py`
	- Add methods: `artist_top_songs(self, artist_id, limit=12)`, `artist_albums(self, artist_id)`, `album_tracks(self, album_id)`.
	- Normalize results to a shape the frontend expects (include videoId when present, thumbnails, durations).
	- Add short TTL caching (in-process LRU/TTL) to protect ytmusicapi.
- `backend/app/api/youtube_music.py`
	- Add routes that map to the service methods: `/artist/<artist_id>`, `/artist/<artist_id>/albums`, `/album/<album_id>/tracks`.

Frontend changes (files to modify/create)
- `frontend/src/components/add/YouTubeMusicSearch.tsx`
	- Make the artist name clickable and include `artistId`/`browseId` in responses where possible.
- New components:
	- `frontend/src/components/add/YTMusic/ArtistBrowsePanel.tsx` (shows Top Songs + Albums)
	- `frontend/src/components/add/YTMusic/AlbumList.tsx` (expandable albums that lazy-load tracks)
- Hooks:
	- `frontend/src/hooks/api/useYouTubeMusicArtist.ts` (GET `/api/youtube-music/artist/:id`)
	- `frontend/src/hooks/api/useYouTubeMusicAlbums.ts` (GET `/api/youtube-music/artist/:id/albums`)
	- `frontend/src/hooks/api/useYouTubeMusicAlbumTracks.ts` (GET `/api/youtube-music/album/:id/tracks`)
- Types:
	- Update `frontend/src/types/YouTubeMusic.ts` to add `YouTubeMusicArtist` and `YouTubeMusicAlbum` and optionally `artistId?: string` on song objects.

UX behaviour
- Click artist -> push a breadcrumb/panel header (Artist: NAME) with a back button to return to previous search.
- Show Top Songs and Albums sections. Albums are collapsed by default; clicking an album expands it and lazy-loads tracks.
- Each track shows the same Add-to-Library action used across the app. If an album/track lacks a videoId, show "no video" or attempt to resolve via search.

Fallback / hybrid metadata
- Only if album metadata is missing from ytmusicapi, the backend may call iTunes Lookup to enrich albums (artwork, tracklisting). iTunes data used for metadata only; downloads remain YouTube-based.

Edge cases & notes
- Ensure backend returns stable `browseId` for artists; if only a name is available, resolve it server-side to the best matching browseId.
- Some tracks may not have videoIds — mark them and allow the user to try a search or skip.
- Cache results for 15–60 minutes to reduce calls to ytmusicapi.

Tests & acceptance criteria
- Backend unit tests: mock ytmusicapi responses and validate `artist_top_songs`, `artist_albums`, `album_tracks` normalize correctly.
- Manual UI smoke test: search => click artist => see Top Songs and Albums => expand album => see tracks => click Add => existing pipeline runs (createSong -> download stepper).

Estimate
- Backend: 6–10 hours (service methods, routes, caching, basic tests).
- Frontend: 6–12 hours (hooks, components, wiring, styling, manual QA).

Sample curl for smoke test
```
# get artist top songs
curl -s "http://localhost:5000/api/youtube-music/artist/ARTIST_BROWSE_ID?limitTop=10" | jq

# list albums
curl -s "http://localhost:5000/api/youtube-music/artist/ARTIST_BROWSE_ID/albums" | jq

# album tracks
curl -s "http://localhost:5000/api/youtube-music/album/ALBUM_ID/tracks" | jq
```

Next steps
- I can implement a focused prototype for this task (backend endpoints first, then frontend ArtistBrowse panel). If you'd like that, tell me and I will scaffold the backend service and routes in a branch.

