# Open Karaoke Studio - Features

Complete inventory of features in the application, organized by domain and described with user needs.

Each domain has a detailed write-up under `docs/domains/` (ingestion pipeline, song library,
lyrics system, sessions & realtime, player & stage), including the known bugs in more depth.

## Table of Contents

1. [Song Library Management](#1-song-library-management)
2. [Queue Management](#2-queue-management)
3. [Playback System](#3-playback-system)
4. [Lyrics System](#4-lyrics-system)
5. [Session & Multi-User](#5-session--multi-user)
6. [Performance Controls](#6-performance-controls)
7. [Background Processing](#7-background-processing)
8. [Metadata & Search](#8-metadata--search)
9. [Authentication & User Management](#9-authentication--user-management)

---

## 1. Song Library Management

How it works: [Song & Library Metadata](/domains/song-library).

### Browse Library
**As a user, I want to browse my karaoke library** so I can find songs to add to the queue.

**Features:**
- **Phones and desktop (`/`):**
  - Search across title, artist, album and show name with live filtering
  - Two tabs when not searching: **Recently Added** (up to 48 songs) and **Recently Sang**
    (performance history, newest first)
  - Artist accordion with an A–Z index bar and infinite scroll. Shows (musicals) are listed
    alongside artists
  - Featured artists appear under their own name too
  - The stage device and admins get the full song card; guests get a tap-to-open performer card
- **The TV (`/stage`):**
  - Songs are picked from a song wheel (Artists A–Z or Recently added) that can be driven with arrow
    keys, Enter and Back, or the mouse wheel. See [Song Select Wheel](#song-select-wheel)

**Status:** ✅ Working

**Key Files:**
- [Library.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/pages/Library.tsx) - Route adapter
- [LibraryScreen.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/library/components/LibraryScreen.tsx) - The library screen
- [ArtistAccordion.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/library/components/ArtistAccordion.tsx) - Artist browsing
- [RecentlyAddedSongs.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/library/components/RecentlyAddedSongs/RecentlyAddedSongs.tsx) - Recently added
- [RecentlySang.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/library/components/RecentlySang/RecentlySang.tsx) - Recently sang

**Known Limitations:**
- Search matches the raw artist string, while the artist list uses the artist credits, so the two
  can group the same song differently (see `docs/domains/song-library.md`)

---

### Add Songs from YouTube
**As a user, I want to add songs from YouTube** so I can build my karaoke library.

**Features:**
- **YouTube Music Search:**
  - Suggestions while typing; results load when one is picked or the search is submitted
  - Picking a suggestion that YouTube Music treats as an artist ("jamiroquai") opens that
    artist, with the song results behind it on back
  - Results sorted by what a guest is looking for: the best match first, then other songs, then
    the best match's other versions (covers, live takes, remixes) folded into one row, then
    artists
  - Every credited artist is kept ("JAY-Z feat. Alicia Keys"), and each one links to their page
  - Each song says where it stands: Add, In the songbook (with Sing it to queue the library's
    copy), Getting it ready…, or Try again when the library's only copy failed (adding it
    restarts that copy instead of adding a duplicate)
  - One preview at a time, from any song's art, with a bar at the bottom; it keeps playing while
    moving between screens
- **YouTube Video Search:**
  - "Can't find it? Search YouTube" swaps in plain YouTube results
  - The channel stands in for the artist
- **Artist and album screens:**
  - An artist's albums in a row that scrolls sideways, oldest first, then their popular songs
    ("Show all popular songs" for the rest), then singles, then remixes (remix EPs, sped-up and
    slowed-down versions) from both
  - An album's cover and every track
  - Each screen has its own address on a phone (`/add?q=…`, `/add/artist/…`, `/add/album/…`), so
    the back button and links work
  - "Browse artist" from the library opens the artist only when the name matches exactly;
    otherwise it shows the search
- **Automatic Lyrics:**
  - Lyrics are fetched within seconds of adding, then timed word by word once the vocals are
    separated (see [Display Synced Lyrics](#display-synced-lyrics))
- **Background Processing:**
  - YouTube download via yt-dlp
  - AI vocal separation, always with the three-track engine from this screen
  - Progress shown on the song's card, polled every 3 seconds while jobs are active
  - Progress also shows inline under the result that was just added (search results and album
    tracks), so a phone user sees it start without leaving the page: what step it's on ("Taking
    out the vocals · step 2 of 3"), or how many songs are ahead of it in the job queue
- **On the TV:** the same screens, opened from the song wheel's + button; Back walks album →
  artist → search → the wheel. It hands back to the wheel as soon as a song is added

**Status:** ✅ Working

**Key Files:**
- [AddSong.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/pages/AddSong.tsx) - Add song page
- [add-song/](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/songs/components/add-song/) - The search, artist and album screens
- [song_intake_service.py](https://github.com/spencerfrost/open-karaoke-studio/blob/master/backend/app/services/song_intake_service.py) - Library state of results, and adding a song in one request
- [SongProcessingTracker.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/songs/processing/SongProcessingTracker.tsx) - Inline progress on an added result
- [AddSongScreen.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/stage/screens/AddSongScreen.tsx) - The TV's version

**Known Limitations:**
- No progress feedback for very long downloads (large files)
- No way to add a new song by uploading a file. Upload only replaces the audio of an existing song

---

### Edit Song Details
**As a user, I want to edit song details** so I can fix incorrect information and add missing details.

Opened from the full song card (stage device and admins). Three tabs:

**Features:**
- **Details tab:**
  - Title, album, show name, year, sung language
  - Artist with featured-artist chips
  - Read-only facts: AcoustID fingerprint status, MusicBrainz link, separation engine, loudness
    and volume correction, source, video ID
  - Vocal range (lowest/highest detected note, e.g. G2–E5)
  - Editing the album name stops automatic album lookups from changing it
- **Lyrics tab:** edit plain and synced lyrics, search for each, clear word timings
- **Actions tab:**
  - Retry download & processing (when the original audio is missing)
  - Identify the song: fingerprint lookup, MusicBrainz search
  - Replace the song from YouTube Music, or by uploading an MP3
  - Analyze vocal range
  - Reprocess audio with a different separation engine
  - Keep current details (AcoustID won't suggest other names)
- **Delete:** admins only, from the dialog's header

**Status:** ✅ Working

**Key Files:**
- [SongManagementDialog.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/songs/components/song-details/SongManagementDialog.tsx) - The dialog
- [DetailsTab.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/songs/components/song-details/tabs/DetailsTab.tsx) - Details
- [ActionsTab.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/songs/components/song-details/tabs/ActionsTab.tsx) - Actions

**Known Limitations:**
- The artist field is saved as one "Primary feat. A, B" string and re-parsed, so a featured
  artist with a comma in their name gets split
- The save endpoint accepts any session member; only the UI keeps guests out

---

### Song Actions
**As a user, I want to perform actions on songs** so I can queue them or sing them now.

**Features:**
- **Add to Queue:** with a singer name. On a phone the name is the guest's own. On a shared host
  device it asks who's singing (on the TV, through the confirm screen)
- **Sing it now:** add to the queue and start it straight away (stage device only)
- **Previews:** hover or tap to hear the original mix
- **Performer Song Card:** tap-to-open drawer for guests showing lyrics preview, audio preview,
  and Add to Queue
- **Processing Awareness:** a song still processing can be queued but not played

**Status:** ✅ Working

**Key Files:**
- [SongCard.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/songs/components/song-card/SongCard.tsx) - Full song card
- [PerformerSongCard.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/songs/components/song-card/PerformerSongCard.tsx) - Guest song card
- [useSongActions.ts](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/songs/hooks/useSongActions.ts) - Play, queue, delete
- [QueueSingerDialog.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/songs/components/song-card/QueueSingerDialog.tsx) - Who's singing?

**Known Limitations:** None

---

## 2. Queue Management

How it works: [Sessions, Queue & Realtime](/domains/sessions-realtime).

### View Queue
**As a user, I want to see the karaoke queue** so I know what's coming up next.

**Features:**
- On the TV's right rail: **Singing Now**, then **Up Next** with position numbers, singer and
  song
- Order is the rotation by default: one song per person per lap, in seat order (see
  [Rotation](#rotation)). Hosts can switch a session to plain insert order
- The join QR code stays under the rail, even while the rails are collapsed
- Real-time updates via WebSocket

**Status:** ✅ Working

**Key Files:**
- [StageQueueRail.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/player/components/stage/StageQueueRail.tsx) - Queue rail
- [useKaraokeQueue.ts](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/hooks/api/useKaraokeQueue.ts) - Queue queries

**Known Limitations:**
- Phones have no queue view

---

### Manage Queue
**As a user, I want to manage the queue** so I can control what plays next.

**Features:**
- Play any queued song now (the song that was playing fades out, and the new one starts by itself)
- Remove a song
- Bump a song to the front without changing whose turn it is (rotation mode)
- Drag to reorder (insert-order mode only)
- All actions broadcast via WebSocket to all connected devices

Playing, removing, bumping and reordering are for the session owner only.

**Status:** ✅ Working

**Key Files:**
- [Stage.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/pages/Stage.tsx) - Stage page with queue
- [useKaraokeQueue.ts](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/hooks/api/useKaraokeQueue.ts) - Queue operations

**Known Limitations:**
- A guest can't remove a song they queued by mistake

---

### Rotation
**As the room, we want everyone to get a turn** so nobody sings five songs in a row.

**Features:**
- Everyone on the session's roster has a seat. The server always names whose turn it is, even
  when that person hasn't picked a song
- The turn follows whoever sings: after an out-of-turn song, the person in the next seat is up.
  Someone's first song of the night, sung out of turn, seats them just ahead of whoever was up,
  who stays up. A bumped song for someone else is an extra song and moves nobody
- From the [Handoff Screen](#handoff-screen): Skip my turn, Add performer (they sing now and keep
  that seat), Remove from rotation (with undo)
- When two devices act at once, the first one wins and the other is quietly told

**Status:** ✅ Working

**Key Files:**
- [queue_ordering.py](https://github.com/spencerfrost/open-karaoke-studio/blob/master/backend/app/services/queue_ordering.py) - Play order
- [turn_service.py](https://github.com/spencerfrost/open-karaoke-studio/blob/master/backend/app/services/turn_service.py) - Whose turn it is
- [useTurn.ts](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/hooks/api/useTurn.ts) - Turn actions

**Known Limitations:** None

---

## 3. Playback System

How it works: [Player, Stage & Performance](/domains/player-stage).

### Main Karaoke Player
**As a user, I want to play karaoke songs** so I can sing along.

**Features:**
- **Audio Playback:**
  - Multi-track playback (vocals + instrumental + optional backing vocals)
  - Independent volume control for each track
  - Per-song loudness normalization (gain correction applied in Web Audio graph, with a limiter just under full scale)
  - Every new song counts in 3-2-1 over silence, then plays from 0:00. Restarting the same song
    doesn't count
  - The song that was playing fades out over 3 seconds first, with "Get ready" on screen
  - If the audio isn't ready yet, the count holds on 1 until it is. The song never starts early
  - The count waits while another screen (song select, the handoff screen) covers the player
  - Pressing play during the count just starts the song
- **Visual Elements:**
  - Song title and artist
  - Clickable artist name (opens the song wheel on that artist)
  - "Songbook" button in the corner
  - "{Singer}, get ready" and the 3-2-1 in the lyrics column before a new song
  - "Getting the song ready…" while the audio loads after a page reload (no count: the song waits
    for a click on play)
  - "{Singer}, open your phone" across the top during the intro of a song while the singer's linked
    phone is closed, locked or in the background, once per singer per session (see
    [Mobile Performance Controls](#mobile-performance-controls))
  - Error message with Try Again
- **Fullscreen:** the transport's fullscreen button or the F key
- **Background Music:**
  - Keeps playing while the stage browses the songbook (see Stage Now-Playing Bar)
  - Keeps playing after leaving stage mode (see Mini Player)

**Status:** ✅ Working

**Key Files:**
- [KaraokePlayer.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/player/components/KaraokePlayer.tsx) - Main player
- [useKaraokePlayer.ts](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/player/hooks/useKaraokePlayer.ts) - Player logic
- [useSongStart.ts](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/player/hooks/useSongStart.ts) - The one path that starts a song: count, then play
- [useSongCountdownStore.ts](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/stores/useSongCountdownStore.ts) and [SongCountdown.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/player/components/SongCountdown.tsx) - The count
- [OpenYourPhonePrompt.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/stage/components/OpenYourPhonePrompt.tsx) - "Open your phone"
- [useKaraokePlayerStore.ts](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/stores/useKaraokePlayerStore.ts) - Player state
- [usePlaybackStateStore.ts](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/stores/usePlaybackStateStore.ts) - Web Audio engine

**Known Limitations:**
- "Try Again" reloads the song without its loudness correction

---

### Stage Layout & Controls
**As the person at the TV, I want the controls in reach and out of the way** so the lyrics are
the show.

**Features:**
- **Three columns:** controls rail on the left, lyrics in the middle, queue rail on the right
- **Transport** under the lyrics: restart, play/pause, next song, fullscreen, time and seek bar
- **Rails collapse** to icon strips the moment a song starts, and a waveform and thin progress
  line appear along the bottom. A click, a key or deliberate mouse movement brings them back.
  They collapse again after 4 seconds of no activity
- **Keys:** Space/Enter play-pause · ↑↓ vocal volume · ←→ lyrics timing ±100 ms · F fullscreen ·
  L songbook
- **Scales to the screen:** the whole stage is sized from the viewport, so it keeps its
  proportions on any TV

**Status:** ✅ Working

**Key Files:**
- [StageLayout.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/player/components/stage/StageLayout.tsx) - The three columns
- [StageTransport.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/player/components/stage/StageTransport.tsx) - Transport
- [useStageRails.ts](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/player/components/stage/useStageRails.ts) - When the rails collapse
- [useStageKeyboard.ts](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/player/components/stage/useStageKeyboard.ts) - Keys

**Known Limitations:** None

---

### Controls Rail
**As a singer, I want quick access to lyrics and audio controls** so I can adjust things during
the song.

The same component renders on the TV's left rail and on the phone's controls page, so the two
always match.

**Features:**
- **Mix:** Vocals and Backing faders, each with mute
- **Lyrics:**
  - Search & replace, paste
  - Timing offset: drag the readout, −/+ buttons (100 ms), reset, "Save timing to song"
    (synced lyrics only)
  - Text size
  - "Something wrong?" — report Wrong words or Out of sync
- **More:** instrumental volume, lyrics auto-scroll

**Status:** ✅ Working

**Key Files:**
- [ControlsStrip.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/performance/controls/ControlsStrip.tsx) - The strip
- [MixCard.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/performance/controls/MixCard.tsx) - Faders
- [LyricsControlsCard.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/performance/controls/LyricsControlsCard.tsx) - Lyrics controls
- [MoreControlsSheet.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/performance/controls/MoreControlsSheet.tsx) - Everything else

**Known Limitations:**
- On the TV the Backing fader is enabled even for two-track songs, where it does nothing
- Every new song resets the mix and lyrics offset on the TV, but other devices aren't told

---

### Song Select Wheel
**As the person at the TV, I want to pick a song without a keyboard** so anyone can walk up and
choose.

**Features:**
- Columns on a turning cylinder, starting with a list of ways in: **Artists A–Z** (Letter →
  Artist → Song) or **Recently added** (the last 100 songs, newest first, with the artist under
  each title). ↑↓ on the list switches at once; ←→ turns the cylinder, ↑↓ moves, Enter picks, Back
  goes back. Holding ↑↓ speeds up
- Each way in keeps its place while you look at the other
- A song still processing shows in Recently added, greyed; it can be looked at and queued but
  not sung yet
- The mouse wheel scrolls the column under the pointer
- Resting on a song plays a quiet preview after 1.5 seconds
- An info card shows what's known about the song (lyrics type, year, vocal range…)
- Search for whoever has the keyboard
- Picking a song opens a confirm screen that asks who's singing, starting on whoever's turn it
  is, then **Sing it now** or **Add to queue**
- Beside the wheel, a small list of songs getting ready (see
  [Processing List on Song Select](#processing-list-on-song-select))
- "Exit stage" is small and out of reach of the arrow keys

**Status:** ✅ Working

**Key Files:**
- [SongWheel.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/stage/wheel/SongWheel.tsx) - The wheel
- [SongSelectScreen.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/stage/screens/SongSelectScreen.tsx) - The screen around it
- [SongConfirmScreen.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/stage/screens/SongConfirmScreen.tsx) - Who's singing?

**Known Limitations:**
- The tuning numbers (speeds, delays) haven't been checked on the TV yet

---

### Mini-Player
**As a user, I want music to continue when I navigate away** so I can browse the library while music plays.

Off-stage only. Inside stage mode, song select is a screen within `/stage` rather than a route,
so the mini player never shows there; the stage has its own now-playing bar (below).

**Features:**
- **Visibility:**
  - Shows after "Exit stage → Keep it running", while the song is still playing
  - Fixed position (bottom-right)
  - Smooth entrance/exit animations
- **Display:**
  - Song title and artist
  - Music icon (artwork placeholder)
  - Current time and duration
  - Progress bar (visual only, not interactive)
  - Gradient background
- **Controls:**
  - Play/pause button
  - Expand button (returns to /stage)
  - Close button (hides the mini player for this song; the music keeps playing)
- **State Sync:**
  - Reads from global player store
  - Updates based on player state changes

**Status:** ✅ Working

**Key Files:**
- [MiniPlayer.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/components/player/MiniPlayer/MiniPlayer.tsx) - Mini player component
- [useMiniPlayer.ts](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/components/player/MiniPlayer/useMiniPlayer.ts) - Mini player logic

**Known Limitations:** None

---

### Stage Now-Playing Bar
**As the room, we want to see what's playing while we pick the next song.**

**Features:**
- A footer along the bottom of song select, confirm and add, like a media player's
- Play/pause, title, artist and singer on one line, the player's gradient progress bar (display
  only) and **time left**
- Clicking it goes back to the song. After the song has ended it says whose turn is next, and
  opens the handoff screen if they have a song ready
- When another song replaces the one playing ("Sing it now", Next, the queue rail, a phone), the
  old one fades out over 3 seconds instead of cutting off, then the new one counts in (see
  [Main Karaoke Player](#main-karaoke-player)). Pause and leaving the session stay instant

**Status:** Built, not yet checked on the TV

**Key Files:**
- [StageNowPlaying.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/stage/components/StageNowPlaying.tsx) - The bar
- [useKaraokePlayerStore.ts](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/stores/useKaraokePlayerStore.ts) - `setSongAndLoad` fades the old song out first, using `fadeOut` in usePlaybackStateStore

---

### Handoff Screen
**As the room, we want to know who's up next when a song ends** so the next singer can get to the
mic.

**Features:**
- Opens by itself when a song ends on the performance screen
- **Who's up:** the next singer's name, large
- **What they're singing:** their song (click or Enter to start it). If they haven't picked one:
  "check your phone, or pick one here", up to four suggestions by the same artist, and Open the
  Songbook. If nobody has joined yet: a big QR code and the join code
- **How to change either:** Skip my turn, Add performer, Remove from rotation (with undo)
- On deck: the next three people. The full rotation order underneath
- No auto-advance: the screen waits for a person. A song started from it counts in 3-2-1 like
  any other

**Status:** ✅ Working

**Key Files:**
- [HandoffScreen.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/stage/screens/HandoffScreen.tsx) - The screen
- [StageShell.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/stage/StageShell.tsx) - Opens it when a song ends

**Known Limitations:** None

---

## 4. Lyrics System

How it works: [Lyrics System](/domains/lyrics-system).

### Display Synced Lyrics
**As a user, I want to see lyrics synchronized with the music** so I know when to sing.

**Features:**
- **Word-by-word highlighting** where the song has word timings (most songs, filled in
  automatically after separation). Lines without word timings highlight as a whole line
- **Synced Lyrics (LRC Format):**
  - Time-synchronized line highlighting
  - Auto-scroll to keep current line centered
  - Click lyrics line to seek to that timestamp
  - User scroll detection (pauses auto-scroll for 3s)
  - Responsive text sizing (small/medium/large)
  - Active line emphasis
- **Plain Text Lyrics:**
  - Non-synchronized lyrics display
  - With no lyrics at all: Search, Paste and Transcribe buttons
- **Instrumental breaks:** a progress bar across gaps of 6 seconds or more
- **Blank Line Handling:**
  - Preserves blank lines for spacing/rhythm

**Status:** ✅ Working

**Key Files:**
- [LyricsDisplay.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/lyrics/components/LyricsDisplay.tsx) - Picks plain or synced
- [KaraokeLyricsRenderer.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/lyrics/components/KaraokeLyricsRenderer.tsx) - Lyrics renderer
- [useLyricsAlignment.ts](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/hooks/api/useLyricsAlignment.ts) - Word timings

**Known Limitations:**
- Repeated lines can confuse word matching (tech-debt #21)
- "Transcribe" fetches lyrics from a provider instead when one has them

---

### Fetch and Select Lyrics
**As a user, I want to find lyrics for my songs** so I can have synchronized lyrics during playback.

**Features:**
- **Multiple Providers:**
  - syncedlyrics (Python library), tried first
  - LRCLIB (LRC database), when syncedlyrics finds nothing
- **Search Workflow:**
  - Automatic on song creation
  - Manual search from the controls rail, the song's Lyrics tab, or the admin review pages
  - Search refinement with custom query
  - Parse "Artist - Title" or "Title by Artist"
  - Reset to original search
- **Results Selection:**
  - Shows multiple lyrics options, synced first, then by closeness to the song's length
  - Preview plain and synced lyrics
  - Source indicator
  - Line count display
  - Select and confirm before saving
- **Reports:** a singer can report Wrong words or Out of sync. The app tries other lyrics or
  re-times the same words, and lists the report on the admin Lyrics Reports page

**Status:** ✅ Working

**Key Files:**
- [LyricsFetchDialog.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/lyrics/components/LyricsFetchDialog.tsx) - Fetch dialog
- [LyricsResults.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/lyrics/components/LyricsResults.tsx) - Results display
- [useLyrics.ts](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/hooks/api/useLyrics.ts) - Lyrics API hooks
- [LyricsReportRow.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/performance/controls/LyricsReportRow.tsx) - Report buttons

**Known Limitations:**
- Picking a plain-only result on a song that has synced lyrics keeps the old synced lyrics on
  screen (same bug as [Manual Lyrics Input](#manual-lyrics-input))

---

### Manual Lyrics Input
**As a user, I want to paste my own lyrics** so I can add lyrics that aren't available online.

**Features:**
- Paste lyrics from clipboard
- Plain text editor
- Replaces existing plain lyrics

**Status:** ⚠️ Bug

**Key Files:**
- [PasteLyricsDialog.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/lyrics/components/PasteLyricsDialog.tsx) - Paste dialog

**Known Limitations:**
- Pasting is meant to clear synced lyrics, but doesn't. On a song that already has synced
  lyrics, the old synced lyrics keep showing (found in the code, not yet reproduced)
- No manual LRC timestamp editor in the paste dialog (the song's Lyrics tab can edit synced text)

---

### Adjust Lyrics Timing
**As a user, I want to adjust lyrics timing** so lyrics sync better with the music.

**Features:**
- **Timing Offset:**
  - Adjust lyrics sync timing in real-time
  - +/- 100ms increments, or ←→ on the TV
  - Drag-to-adjust
  - Save permanently (updates LRC timestamps, then re-times the words)
  - Resets to zero for each new song
- **Size Control:**
  - Small/medium/large text size

**Status:** ✅ Working

**Key Files:**
- [LyricsOffsetRow.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/performance/controls/LyricsOffsetRow.tsx) - Timing controls
- [LyricsSizeRow.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/performance/controls/LyricsSizeRow.tsx) - Size control

**Known Limitations:** None

---

## 5. Session & Multi-User

How it works: [Sessions, Queue & Realtime](/domains/sessions-realtime).

### Create and Join Sessions
**As a user, I want to create or join karaoke sessions** so multiple devices can participate.

**Features:**
- **Session Creation (TV only):**
  - Sessions start only on `/stage`, from a setup screen: who's singing tonight, rotation on or
    off, session length
  - If the host already has a live session, it offers to resume it or end it and start this one
  - Generates a 4-letter code
  - Opening `/stage` again resumes tonight's session, even from another browser on the same account
- **Session Joining (phones):**
  - Scan the QR code on the TV, or go to `/join` and type the code
  - **No phone? Open a phone view**, under the join code on the stage, opens a phone-sized window
    (about 400 px wide) that joins as a guest. Only offered with a mouse, so never on the TV
  - Enter a display name once; it's remembered for next time
  - Joining adds the name to the rotation
- **Roles:**
  - **Stage device:** the TV. Plays the audio
  - **Session owner:** the host's account, on any device. Starts and pauses songs, ends the night
  - **Guests:** queue songs, use the controls page, run the handoff screen
- **Session Persistence:**
  - Stored in localStorage, shared by every tab of the host's browser
  - A guest window (a phone view, or a tab that joins as a guest in the browser running the stage)
    keeps its identity in its own sessionStorage instead, so it can't overwrite the host's or start
    out signed in as the host
  - Auto-recovery on browser refresh

**Status:** ✅ Working

**Key Files:**
- [Entry.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/pages/Entry.tsx) - Join page
- [CreateSessionScreen.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/stage/screens/CreateSessionScreen.tsx) - Session setup
- [SessionContext.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/contexts/SessionContext.tsx) - Recovery at startup
- [sessionStore.ts](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/stores/sessionStore.ts) - Session state
- [guestWindow.ts](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/lib/guestWindow.ts) - Guest windows and where identity is stored
- [StageJoinCode.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/player/components/stage/StageJoinCode.tsx) - Join code, QR and "Open a phone view"

**Known Limitations:** None

---

### Real-Time Synchronization
**As a user, I want all devices to stay in sync** so everyone sees the same thing.

**Features:**
- **Two WebSocket Endpoints:**
  1. `/ws/jobs` - Processing status, polled by the client every 3 s while jobs are active. Carries
     no join codes: a job names its session with an opaque owner tag
  2. `/ws/session/{session_id}` - All karaoke session functionality
- **Real-time Updates:**
  - Queue, rotation and roster changes broadcast to all devices
  - Player state and performance controls sent from the TV
- **Session Isolation:**
  - All state keyed by session_id
- **Event Types:**
  - `queue_updated` - Queue or turn changed (carries whose turn it is)
  - `roster_updated` - Someone joined, left or was restored
  - `presence`, `presence_updated` - Whose phone is open and on screen, by roster seat
  - `performance_state`, `control_updated` - Player state and control changes
  - `playback_play`, `playback_pause`, `song_loaded`, `song_ready` - From the TV
  - `session_ended` - The night is over; every device returns to the start

**Status:** ✅ Working

**Key Files:**
- [sessionWebSocketService.ts](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/services/sessionWebSocketService.ts) - Session WebSocket client
- [jobsWebSocketService.ts](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/services/jobsWebSocketService.ts) - Jobs WebSocket client
- [session_specific.py](https://github.com/spencerfrost/open-karaoke-studio/blob/master/backend/app/ws/session_specific.py) - Session WebSocket handler

**Known Limitations:**
- Phones send control changes but don't receive them (see
  [Mobile Performance Controls](#mobile-performance-controls))

---

### Session Lifecycle
**As a user, I want sessions to end cleanly** so resources are released.

**Features:**
- **Session Display:**
  - The join code and QR are always on the TV (right rail, song wheel, handoff screen)
  - The session popover with the QR code shows only on the stage
- **Ending a Session:**
  - "Exit stage → End the session" (owner only) ends the night for everyone and shows a recap,
    with a YouTube Music playlist of the night's songs
  - "Exit stage → Keep it running" leaves stage mode without ending anything
  - If the host's connection drops, the session waits 30 seconds for it to come back, which
    covers a page refresh or a Wi-Fi blip
  - Sessions expire after the host's chosen length (8 hours by default)
  - Ended sessions are kept for the recap and history, and deleted after 7 days
  - Leaving on one device only removes that device
- **Route Protection:**
  - Pages need an account or a session; `/stage` needs a host account; `/controls` needs a session
    and isn't for the TV
- **Session Recovery:**
  - Restores the session at startup, before any page renders
  - Loading state during recovery

**Status:** ✅ Working

**Key Files:**
- [guards.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/routes/guards.tsx) - Route protection
- [ExitStagePrompt.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/stage/ExitStagePrompt.tsx) - Keep running or end
- [SessionRecoveryLoading.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/session/components/SessionRecoveryLoading.tsx) - Recovery UI
- [useSessionConnection.ts](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/session/hooks/useSessionConnection.ts) - Connection logic

**Known Limitations:**
- If the host has two owner devices connected (the TV and their signed-in phone) and either one
  drops, the session ends 30 seconds later even though the other is still connected (found in the
  code, not yet reproduced)
- The recap playlist is keyed by the 4-letter code, so a later session that reuses a code can get
  an old playlist

---

## 6. Performance Controls

How it works: [Player, Stage & Performance](/domains/player-stage).

### Mobile Performance Controls
**As a user on mobile, I want easy access to the controls** so I can adjust things while performing.

**Features:**
- **Mobile-Optimized Interface:**
  - Dedicated page for performers (`/controls`)
  - Large touch-friendly controls
  - Its own layout for one hand: the song, the singer and Close along the top, no bottom nav
- **Controls Available:**
  - Original singer and Backup singers faders, each with mute, taking most of the screen. A song
    without a backup-singer track says so in place of that fader
  - Lyrics timing: drag the number or tap Earlier / Later, with a line saying what it does
  - Progress, display only, so a stray touch can't jump the song for the room
  - More: keep the timing for this song, find or paste different lyrics, report wrong lyrics,
    lyrics size, music volume
- **Mirrors the TV:** faders, timing and progress follow whatever the TV and other phones do
- **Session Integration:**
  - The route needs a session first
  - When a singer's song starts, their phone opens `/controls` by itself, once per song, so it never
    drags them back after they've left
  - If their phone is closed, locked or in the background, the TV says "{Name}, open your phone"
    until the first sung line (15 seconds for a song without timed lyrics). It asks each singer once
    per session, and never asks one whose phone has already been on the controls. Once the phone
    is back on the page it sees its song has started and opens the controls. A singer the host
    typed in, with no phone linked, never sees the prompt

**Status:** ✅ Working (not yet checked on a phone)

**How it works:** [Player, Stage & Performance § The phone](/domains/player-stage#the-phone)

**Key Files:**
- [PerformanceControlsPage.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/pages/PerformanceControlsPage.tsx) - Controls page
- [PerformanceControlsPanel.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/performance/components/PerformanceControlsPanel.tsx) - Controls panel
- [components/phone/](https://github.com/spencerfrost/open-karaoke-studio/tree/master/frontend/src/features/performance/components/phone) - The phone's faders, timing, top bar and More sheet
- [usePhonePresence.ts](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/session/hooks/usePhonePresence.ts) - Reports presence; opens the controls when this phone's song starts
- [presenceStore.ts](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/stores/presenceStore.ts) - Whose phone is open, and which seat this phone is

**Known Limitations:**
- Play and Restart are always disabled on the phone; the TV starts songs by itself
- No fullscreen button: the TV owns fullscreen

---

## 7. Background Processing

How it works: [Ingestion & Processing Pipeline](/domains/ingestion-pipeline).

### Processing Status
**As a user, I want to see processing status** so I know when songs are ready.

**Features:**
- A processing indicator on each song's card while it downloads and separates
- Status is polled every 3 seconds while any job is active, and up to 3 seconds stale
- Song lists refresh when a job finishes
- Failed songs are hidden from the songbook. Adding the song again restarts it, and admins see
  them on the Failed songs page
- Network and GPU memory failures retry by themselves after 1, 5, then 15 minutes
- Library-wide maintenance (lyrics alignment, album covers, artist images…) runs from the admin
  Background jobs page

**Status:** ✅ Working

**Key Files:**
- [useJobsWebSocket.ts](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/hooks/api/useJobsWebSocket.ts) - Polls job status
- [useJobsSync.ts](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/hooks/useJobsSync.ts) - Maps jobs to songs
- [ProcessingIndicator.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/songs/components/song-card/ProcessingIndicator.tsx) - Card indicator
- [AdminJobsPage.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/admin/AdminJobsPage.tsx) - Background jobs

**Known Limitations:**
- No live progress push: the Celery worker can't reach the WebSocket, so the client polls
- A cancel endpoint exists (`POST /api/jobs/{id}/cancel`) but no UI calls it. A cancelled song
  stays in the library as a failed entry

---

### Processing List on Song Select
**As a guest at the TV, I want to see my song getting ready** so I know when I can sing it, and
why it's still waiting.

**Features:**
- A small "Getting songs ready" list in a column to the left of the wheel, which shrinks to make
  room while anything is processing (on a computer it doesn't need to). Up to three rows, then
  "and N more"
- Every song in the job queue, everyone's: what step it's on ("Getting the song", "Taking out the
  vocals", "Timing the lyrics"), with a progress bar, or "Waiting its turn · N ahead"
- This session's songs are marked **Yours**. Other sessions' songs drop off when they finish
- When one of ours finishes (lyrics timing included), its row turns into **Sing this**: it adds the
  song to the queue under whoever's turn it is and starts it, with the usual 3-2-1. A song that
  failed says so, with OK to clear it
- Ownership comes from an opaque tag on each job, not the join code

**Status:** Built, not yet checked on the TV

**Key Files:**
- [StageProcessingList.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/stage/components/StageProcessingList.tsx) - The list and Sing this
- [jobTimeline.ts](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/songs/processing/jobTimeline.ts) - Joins a song's jobs into one timeline
- [jobTrackerStore.ts](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/stores/jobTrackerStore.ts) - The timelines
- [useSingThis.ts](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/stage/hooks/useSingThis.ts) - Sing this

**Known Limitations:**
- A finished song of ours keeps its row for 15 minutes if nobody acts on it, and only on the device
  that saw it finish: the jobs feed only lists jobs still in the pipeline

---

### Audio Processing Pipeline
**As a user, I want my YouTube videos processed into karaoke tracks** so I can sing along.

**Features:**
- **Processing Flow:**
  1. YouTube download via yt-dlp
  2. Audio separation using AI
  3. Vocal range detection (librosa pyin on vocals track)
  4. Loudness measurement after separation (ffmpeg EBU R128 on instrumental + backing vocals → gain correction capped by true peak)
  5. Duration measurement
  6. File storage and database update
- **Running alongside** (separate background tasks started during processing): album and cover
  lookup, AcoustID fingerprinting, lyrics fetch and word timing
- **Separation Engines:**
  - **Three-Track** (default) — Demucs + Roformer + de-noise: produces `vocals.mp3`, `backing_vocals.mp3`, `instrumental.mp3`
  - **Three-Track Duality V2** and **Three-Track Mel-1143** — the same shape with a different
    model for the vocal split
  - **Demucs Standard** — htdemucs_ft, fast 2-stem separation
  - **Audio-Sep Roformer** — better vocal isolation
  - **Hybrid Sequential** — Demucs → audio-separator refinement
  - **Clean Backing** — experimental, multi-pass
  - If a three-track engine fails, it retries once with Demucs
- **Progress Tracking:**
  - 5–12%: Download
  - 12–~95%: Separation (three-track; Demucs-style engines finish at about 50%)
- **Output (three-track engine):**
  - `original.mp3` - Original audio
  - `vocals.mp3` - Lead vocals only
  - `backing_vocals.mp3` - Cleaned backing vocals
  - `instrumental.mp3` - Pure instrumental
- **GPU Acceleration:**
  - Automatically uses CUDA if available
  - Falls back to CPU processing
  - GPU memory is released after 30 minutes with no work

**Status:** ✅ Working

**Key Files:**
- [jobs.py](https://github.com/spencerfrost/open-karaoke-studio/blob/master/backend/app/jobs/jobs.py) - Celery tasks
- [audio.py](https://github.com/spencerfrost/open-karaoke-studio/blob/master/backend/app/services/audio.py) - Analysis functions (vocal range, loudness)
- [separation_engines/](https://github.com/spencerfrost/open-karaoke-studio/tree/master/backend/app/services/separation_engines) - Per-engine separation logic
- [youtube_service.py](https://github.com/spencerfrost/open-karaoke-studio/blob/master/backend/app/services/youtube_service.py) - YouTube download

**Known Limitations:**
- CPU processing is slow (10-20 minutes per song)
- No progress feedback during download phase
- The background tasks that run alongside report nothing back, so processing shows complete
  whether or not they worked

---

## 8. Metadata & Search

How it works: [Song & Library Metadata](/domains/song-library).

### Song Identification (AcoustID)
**As a user, I want accurate metadata** so my library is well-organized.

**Features:**
- Each new song is fingerprinted and matched to a MusicBrainz recording
- A match that agrees with the song's title and artist is linked, and fills in artist credits
- A confident match with a different name is only **suggested**. It never renames the song
- Admins review suggestions, ambiguous matches and misses on the admin AcoustID page: accept the
  suggestion, keep the current name, or pick a recording by hand
- "Keep Current Details" in a song's Actions tab marks it as confirmed, so AcoustID leaves it alone
- **Album and cover:** looked up from the exact YouTube Music video, then Deezer, then the
  YouTube thumbnail

**Status:** ✅ Working

**Key Files:**
- [acoustid_service.py](https://github.com/spencerfrost/open-karaoke-studio/blob/master/backend/app/services/acoustid_service.py) - Fingerprinting and linking
- [album_service.py](https://github.com/spencerfrost/open-karaoke-studio/blob/master/backend/app/services/album_service.py) - Album and cover lookup
- [AdminAcoustIdPage.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/admin/AdminAcoustIdPage.tsx) - Review page

**Known Limitations:**
- An earlier version renamed songs from bad matches. The repair of the production library hasn't
  been confirmed (see `docs/domains/song-library.md`)
- Show names for musicals are almost never filled in, and are mostly wrong where they are

---

### YouTube Music Search
**As a user, I want to search YouTube Music** so I can find songs with better metadata.

**Features:**
- Suggestions while typing
- Results grouped into the best match, its other versions, and other songs (the grouping is
  done by the server)
- Every credited artist with their YouTube Music ids; album, length and explicit flag
- Each result's library state, checked in two queries for the whole list
- Whether the query's top result is an artist
- An artist's popular songs (first five, then all), every album oldest first, and singles; an
  album's tracks
- `502` when YouTube Music fails, `404` for an unknown artist or album

**Status:** ✅ Working

**Key Files:**
- [youtube_music_service.py](https://github.com/spencerfrost/open-karaoke-studio/blob/master/backend/app/services/youtube_music_service.py) - YouTube Music API
- [youtube_music.py](https://github.com/spencerfrost/open-karaoke-studio/blob/master/backend/app/api/youtube_music.py) - Routes and response shapes

**Known Limitations:** None

---

## 9. Authentication & User Management

How it works: [Platform Foundations](/domains/platform-foundations).

### Login & Access Control
**As a host, I want my own account** so I can run nights and guests can't end them, delete songs or
change processing settings.

**Features:**
- **Two ways in:** join a session with its 4-letter code (no account), or sign in under
  "Hosting tonight? Sign in" on the entry page. Without either, every page leads back to the entry
  page
- **Roles:** a host can start and run their own nights from `/stage`; an admin can also maintain
  the library and manage users on `/admin/users` (create an account, make it a host)
- **What a guest's phone gets:** the songbook, adding songs, and the controls while in a session.
  Settings, the stage and admin pages are for accounts
- **Stays signed in for 7 days.** When the sign-in expires the app says "Session expired"; a phone
  that's also in a session carries on as a guest
- **Leave session / Log out** from the name chip in the top-right corner of every page

**Status:** ⚠️ Working, with gaps: registration is open to anyone (an open account can't reach
anyone's session, but can add songs to the library), there's no screen to change a display name
or password, and a role change shows in an already-signed-in browser only after it signs in again

**How it works:** [Platform Foundations](/domains/platform-foundations)

---

### Live Demo
**As a visitor following a link, I want to try the app for real** without an account or a code.

**Features:**
- **Try it live** on the entry page (`/join`) starts a real 15-minute session on a free demo
  account and opens the stage with its QR code. Only shown when the server has demo accounts
- **Watch the demo** opens a recording, when one is configured
- On a phone: the recording, and a line saying the live demo needs a computer
- Plain messages when every demo seat is taken, or the visitor's network has started too many
- Limits: 3 new songs per session, 20 per day across all demo accounts, starts rate limited per IP
  (see [Demo Accounts](/demo-accounts))
- **Guided tour** on the demo stage: asks for sound, then walks through adding a song from a
  phone, spinning the wheel while it processes, **Sing this**, the countdown, and the phone's
  controls. Each step moves when the visitor actually does it, never on a "Next" click, and has a
  one-line "how this works" note with a docs link. **Skip tour** is always visible. If downloads
  run out, the queue is busy or the song fails, it offers a song already in the library. Demo
  sessions only

**Status:** ✅ Working

**Key Files:**
- [DemoEntry.tsx](https://github.com/spencerfrost/open-karaoke-studio/blob/master/frontend/src/features/demo/components/DemoEntry.tsx) - The buttons
- [demo.py](https://github.com/spencerfrost/open-karaoke-studio/blob/master/backend/app/api/demo.py) - `GET /api/demo`, `POST /api/demo/start`
- [demo_service.py](https://github.com/spencerfrost/open-karaoke-studio/blob/master/backend/app/services/demo_service.py) - Pool and quotas

---

### User Management Script
**As an operator, I want to manage user accounts from the command line** so I can set up accounts without a UI.

**Features:**
- `backend/scripts/manage_users.py create [--admin] [--host] [--demo]`
- List and delete users
- Reset passwords (the only way to change one)

**Status:** ✅ Working

**Key Files:**
- [manage_users.py](https://github.com/spencerfrost/open-karaoke-studio/blob/master/backend/scripts/manage_users.py)

---

## Feature Summary

| Domain | Features | Status |
|--------|----------|--------|
| **Song Library** | 4 features | ✅ All working |
| **Queue** | 3 features | ✅ All working |
| **Playback** | 7 features | ✅ Working (Now-Playing Bar not yet checked on the TV) |
| **Lyrics** | 4 features | ⚠️ Paste doesn't clear synced lyrics |
| **Session** | 3 features | ✅ All working |
| **Performance** | 1 feature | ✅ Working (not yet checked on a phone) |
| **Processing** | 3 features | ✅ Working (Processing List not yet checked on the TV) |
| **Metadata** | 2 features | ✅ All working |
| **Auth & Users** | 3 features | ⚠️ Registration is open |
| **TOTAL** | **30 features** | |

---

## Notes

- Bugs marked "found in the code" haven't been reproduced in the app yet
- Planned work is in the [roadmap](/roadmap)
- How each feature works: the [Architecture](/architecture) page and its domain docs
- Known issues and tech debt: [Tech Debt](/tech-debt)
