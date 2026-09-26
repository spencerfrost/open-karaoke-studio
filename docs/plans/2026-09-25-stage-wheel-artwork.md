# Stage wheel artwork

Follows [2026-09-25-stage-song-wheel.md](2026-09-25-stage-song-wheel.md), which is built. Not in
the [sequencing](2026-08-29-sequencing.md) table; nothing depends on it.

**Status:** steps 1–4 of the order of work are built (2026-09-25). Step 5, the check on the TV,
is still to do.

**Prototype:** [prototypes/2026-09-25-song-wheel.html](prototypes/2026-09-25-song-wheel.html),
also at <https://claude.ai/artifact/RE7TN2Zbkh3n2Gv6JNDUqD>. Open "Tune the wheel". The
Artwork section switches each piece on and off. The images and song details in it are made up.

## Why

The wheel is text on a dark background. It reads well, but nothing on screen shows the artist
or song you are sitting on. The library already has artist photos, album covers and YouTube
stills. The wheel just doesn't use them.

## What we have

Counted from the live database on 2026-09-25. This decides what is worth showing.

| Field | Coverage | Source in the API |
|---|---|---|
| Artist image | 561 of 752 artists (75%). 152 `not_found`, 39 `not_checked` | `GET /api/artists/image?name=` |
| Album cover | 528 of 1479 songs (36%). 557 albums still `not_checked` | `albumCoverUrl`, set only when a cover exists |
| YouTube still | 1049 songs have a stored thumbnail (71%), 1140 have a `videoId` (77%) | `/api/songs/{id}/thumbnail`, else the YouTube CDN |
| Duration | all | `duration` |
| Vocal range | 783 (53%) | `vocalRangeLow`, `vocalRangeHigh` |
| Year | 212 (14%) | `year` (falls back to `releaseDate`) |
| Lyrics | word-synced 581, synced 1309, plain 848 | `wordSyncedLyrics`, `syncedLyrics`, `plainLyrics` |
| Backing vocals track | 1469 (99%) | `backingVocalPath` |
| Explicit | 25 | `itunesExplicit` |

What follows from it:

- **Album covers are the thin spot.** The YouTube still is the image most songs have, so it
  leads the card. The cover is an extra.
- **Year is almost always empty.** Show it only when it is there. Don't hold a slot for it.
- **"Backing vocals" says nothing.** Nearly every song has one. The prototype shows it as a
  tag; drop it.
- All of these fields are already in the songs-by-artist response the wheel fetches. **No
  backend changes are needed.**

## The design

### 1. Artist image in the songs heading

A round artist image, 84px, sits left of "Songs / ARTIST NAME" at the top of the songs column.
When the artist column is at the front, the songs column is to its right. The heading then
works as the artist's card without adding anything new to the screen.

- Source: `/api/artists/image?name=`, the same URL
  [ArtistSection.tsx](../../frontend/src/features/library/components/ArtistSection.tsx) uses.
- No image: a dark round tile with the artist's first letter (leading "The" dropped).
- Shows (`isShow`) have no artist row. Use the letter tile.
- The songs list moves down to make room. `LIST_TOP` for the song column goes from about 96 to
  about 124 in frame pixels.

### 2. Song info card

A card on the right, shown only while the songs column is at the front. That is the only time
the right side of the screen is empty. It slides in when you turn to the songs column. It
leaves when you turn back or open the confirm screen.

```
┌────────────────────────────┐
│ ┌────────────────────────┐ │
│ │     YouTube still      │ │   400px wide, frame pixels,
│ │ ┌──────┐   16:9        │ │   right: 56px, vertically centred
│ └─┤cover ├───────────────┘ │
│   └──────┘                 │   cover inset only when albumCoverUrl exists
│ Go Your Own Way            │
│ Fleetwood Mac              │
│ Rumours                    │   album line only when album exists
│ ────────────────────────── │
│ LENGTH   RANGE    YEAR     │   range and year only when present
│ 3:38     G3–D4    1977     │
│ [SYNCED] [EXPLICIT]        │
└────────────────────────────┘
```

| Part | From | When missing |
|---|---|---|
| Hero image | Stored thumbnail, then YouTube CDN from `videoId` | Use the album cover as the hero. If neither exists, a plain tile with the title's first letter |
| Cover inset | `albumCoverUrl` | Leave it out. At 36% coverage a letter tile would be on most cards |
| Title, artist | `title`, `artist` (featured artists from `artists` if present) | always present |
| Album | `album` | Leave the line out |
| Length | `duration` | always present |
| Range | `vocalRangeLow`–`vocalRangeHigh` | Leave the cell out |
| Year | `year` | Leave the cell out |
| Lyrics tag | Word-synced, else Synced, else Plain lyrics | "No lyrics" in the quiet style |
| Explicit tag | `itunesExplicit` | No tag |
| Processing tag | `status !== "processed"` | No tag |

This differs from the prototype in two places: missing facts are dropped instead of shown as
"—", and there is no letter tile for a missing cover. Both follow from the coverage numbers.

### 3. Blurred backdrop (try it on the TV)

The selected artist image, or the song's hero image once in the songs column, is shown full
screen behind everything. It is blurred heavily, darkened in the middle and crossfaded on
change. It gives the room colour without adding a panel.

Keep it only if it looks good on the TV and the machine handles a full-screen 90px blur
without stutter. It is the one piece that can be cut without touching the others.

### Not doing

- **Image beside the selected row.** It was in the prototype as an option. The heading and the
  card already show the same images. Text sliding sideways as the image comes in made the
  column less calm.
- **Technical fields** (separation engine, loudness, AcoustID). They don't help anyone pick a
  song.
- **The confirm screen.** [SongConfirmScreen.tsx](../../frontend/src/features/stage/screens/SongConfirmScreen.tsx)
  already shows `getArtworkUrl(song)`. The prototype's confirm card was catching up to it.

## Loading rules

Holding ▼ passes about 30 rows a second, so images must not follow the cursor row by row.

- **Nothing is requested until the cursor settles.** Same 150ms as `SONGS_SETTLE_MS` in
  [useSongWheel.ts](../../frontend/src/features/stage/wheel/useSongWheel.ts). The artist side
  already has a settled artist; the song side needs a settled song index the same way.
- **This matters for artist images in particular.** For a `not_checked` artist,
  `/api/artists/image` fetches from Discogs on the spot. Discogs allows 60 requests a minute.
  A held key without settling would burn through that in two seconds.
- **Keep the old image until the new one has loaded,** then fade across. Don't flash to empty
  between artists.
- **A failed image falls back and is not asked for again** in the same session.
- **Check the cache headers** on `/api/artists/image` and `/api/albums/{id}/cover`. They are
  served with `FileResponse`, which revalidates on every view unless `Cache-Control` is set.
  Scrolling back and forth over the same artists should not hit the server each time.
- **Reduced motion:** no slide, fade or crossfade. Images swap in place.

## How it fits the code

- **`WheelArtwork`**, new in `features/stage/wheel/`: an image with the letter fallback, the
  keep-until-loaded fade and the failed-URL memory. It has a round (artist) and a square (song)
  variant. The heading, the card and the backdrop all use it.
- **The heading** goes into the `header` prop `SongWheel` already passes to the song
  `WheelColumn` ([SongWheel.tsx](../../frontend/src/features/stage/wheel/SongWheel.tsx)).
- **`SongInfoCard`**, new in `features/stage/wheel/`. Takes the settled `Song` and nothing else.
  It sits in the 1600×900 frame next to the ring, not inside it, so the cylinder transforms
  don't touch it.
- **Hero image order** matches `getArtworkUrl` in
  [useSongs.ts](../../frontend/src/hooks/api/useSongs.ts), except the card wants the still
  first and the cover second. Add a small helper for that order rather than changing
  `getArtworkUrl`, which the rest of the app relies on.

## Order of work

1. `WheelArtwork` and the settled song index.
2. Artist image in the songs heading, with the list moved down.
3. Song info card.
4. Backdrop, behind a constant so it is easy to switch off.
5. On the TV: check readability from the couch, backdrop smoothness, and whether the 150ms
   settle feels laggy or natural.

## Open questions

1. **557 albums have never been checked for a cover.** Covers are downloaded during iTunes
   enrichment, so these albums never went through it. A backfill would raise cover coverage
   well above 36%. That belongs to the enrichment work, not this plan, but it decides how
   often the cover inset shows up.
2. **Year.** At 14% it could be dropped from the card entirely. Keep it for now since it costs
   nothing when absent.
3. **iTunes preview.** `itunesPreviewUrl` could play 30 seconds of the original while the card
   is up ("what's this one again?"). Needs an answer for mixing with the song that's playing,
   like the sound effects idea parked in the wheel plan.
