# Enhanced YouTube Video Search — Channel Browse

Goal
- Let users click a channel/uploader in YouTube video search results and switch into a channel browsing mode that lists that channel's uploads (top / latest), with sorting and pagination, and the ability to add videos to the library.

Scope
- Backend: endpoint(s) to list channel uploads / playlist videos, sortable by top/latest/views.
- Frontend: clickable channel names in video results, a Channel Browse panel with sorting and pagination, and reuse of the Add-to-Library flow.

Checklist
- Clicking a channel shows that channel's uploads or top videos.
- Sorting options available (Top / Latest / Most Viewed) and basic pagination (limit + offset / pageToken).
- Frontend shows breadcrumbs/back navigation and Add-to-Library on each video.

API contract (examples)
- GET /api/youtube/channel/:channelId/videos?limit=20&sort=top
	- Response:
		{
			"channel": { "id": "CHANNEL_ID", "title": "Channel Name", "thumbnails": [...] },
			"videos": [ { id, title, url, thumbnail, duration, viewCount } ],
			"error": null
		}

Backend changes (files to modify/create)
- Prefer implementation in a YouTube service file:
	- `backend/app/services/youtube_service.py` (create or extend existing service)
		- Add `get_channel_videos(channel_id, limit=20, sort='top'|'latest'|'popular')`.
	- `backend/app/api/youtube.py` (or the existing youtube API module) — add route `/channel/<channel_id>/videos`.

Implementation options
- If a YouTube Data API key is available: use the `playlistItems` endpoint on the channel's uploads playlist and fetch video statistics to enable sorting by views.
- If no API key: use `yt-dlp` or lightweight scraping (`--flat-playlist`) on `https://www.youtube.com/channel/<id>/videos` as a fallback, but document reliability limits.
- Add caching to reduce repeated requests.

Frontend changes (files to modify/create)
- `frontend/src/components/add/youtube/YouTubeSearch.tsx` — make channel/uploader clickable; include `channelId` in result objects where available.
- New component: `frontend/src/components/add/YTVideo/ChannelBrowsePanel.tsx` (header with channel info, sorting dropdown, video list with Add button).
- Hook: `frontend/src/hooks/api/useYouTubeChannel.ts` to call `/api/youtube/channel/:id/videos`.
- Types: update `frontend/src/types/Youtube.ts` to include `channelId?: string` and a `YouTubeChannel` interface for the channel endpoint.

UX behaviour
- Click channel -> show ChannelBrowsePanel with back breadcrumb.
- Default sort: Top (by view count) with option to switch to Latest.
- Video list uses same cards as search results; Add button uses existing pipeline.

Edge cases & notes
- Some search results may not include a `channelId` — in that case resolve channel by name server-side or disable the click.
- Scraping fallback is brittle; prefer adding a YouTube Data API key for robust behavior.
- Cache responses for a reasonable TTL to reduce scraping/API usage.

Tests & acceptance criteria
- Backend: endpoint returns channel metadata and non-empty videos array for known channels.
- Frontend smoke: search -> click channel -> ChannelBrowsePanel lists videos; click Add -> existing Add-to-Library flow executes.

Estimate
- Backend: 4–10 hours (depends on YouTube Data API available or scraping fallback).
- Frontend: 4–8 hours.

Sample curl for smoke test
```
curl -s "http://localhost:5000/api/youtube/channel/CHANNEL_ID/videos?sort=latest&limit=20" | jq
```

Next steps
- I can implement the backend route for listing channel videos (prefer Data API; fallback to yt-dlp) and wire a simple ChannelBrowsePanel to the frontend. Tell me if you want me to start with this task and I will scaffold the backend first.

