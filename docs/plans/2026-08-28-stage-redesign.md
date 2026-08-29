# Stage Rewrite — three-column player + mirrored phone controls

## Context

`/stage` is built like a YouTube video: [KaraokePlayer.tsx](frontend/src/features/player/components/KaraokePlayer.tsx#L379) wraps everything in `h-[70vh] aspect-video`, letterboxing lyrics inside a box inside a page, then bolts on fullscreen to undo it. Because that box is small, every control had to hide — hover overlays, a 30s mouse-idle timer, and a nested popover stack (`main → lyrics → lyricsTiming`) that portals itself into the fullscreen element.

The real usage is a living room: TV across the room, **mouse on the mic stand**, keyboard nearby for search. That is a 10-foot UI with a pointer. Hover-to-reveal fails (you can't aim at chrome you must discover), thin sliders fail (one-handed, mic in the other), and `w-5 h-5` icons are a dot at 8 feet.

Separately, three control surfaces expose overlapping settings and have drifted: `SettingsMenu` (stage), `PerformanceControlsPanel` (`/controls`), `MoreOptionsSheet`. `/controls` has rotted — **lyrics search, the #3 most-used control, does not exist there at all**.

Outcome: one three-column stage sized for a TV, and a left rail that is the *same channel strip* as the phone, so the two read as one instrument.

Approved mockup: https://claude.ai/code/artifact/16a9f525-9249-48b0-8f23-0e3d65ef082d

## Settled decisions

| Decision | Choice |
|---|---|
| Layout | 3 columns, full viewport. Rails 356px, centre fluid |
| Transport | Under the **centre column only** — gives rails full 1032px height |
| Left rail | Two cards: **MIX** (vocals + backing faders) then **LYRICS** (search, offset, size), then More |
| Control priority | Vocals → Backing → Lyrics search → Offset → Size → rest |
| Offset | Drag the readout (primary), ± flank it (fine-tune) |
| Faders | Always visible. Never behind a button |
| Mute | Icon in each channel's name row, not a separate button |
| While playing | Rails collapse to 72px icon strips, chrome dims to 35%. **Nothing unmounts** |
| Backing fader, two-track songs | Render **disabled** at 0 with a hint. Never reflows the layout |
| Queue rows | **Full replacement** — delete `KaraokeQueueList`/`KaraokeQueueItem` (one call site each) |
| Scale | 80px transport buttons, 64px rail controls, 48px minimum touch targets |

## The core move: one strip, two densities

`ControlsStrip` takes `density: "tv" | "touch"` and is rendered by **both** the stage left rail and `/controls`. Same order, same components, same tokens; only type scale and input handlers differ. This is what stops the two surfaces drifting again.

### New: `frontend/src/features/performance/controls/`

| File | Purpose |
|---|---|
| `ControlsStrip.tsx` | Composition: `MixCard` → `LyricsControlsCard` → More trigger. Takes `density` |
| `MixCard.tsx` | Card wrapper, two `VocalFader`s in a 2-col grid |
| `VocalFader.tsx` | Replaces [VolumeChannel.tsx](frontend/src/features/performance/components/VolumeChannel.tsx). Name row with mute icon, VT323 % readout, vertical `Slider variant="performance"`. Accepts `disabled` |
| `LyricsControlsCard.tsx` | Card wrapper: search button, offset row, size row. **Named to avoid colliding with the existing [LyricsCard.tsx](frontend/src/features/lyrics/components/LyricsCard.tsx)** |
| `LyricsOffsetRow.tsx` | `[−] [draggable readout] [+]`, plus reset and the save-to-LRC button |
| `useLyricsOffsetDrag.ts` | Mouse + touch drag hook |
| `LyricsSizeRow.tsx` | `Size  [S][M][L]` inline |
| `MoreControlsSheet.tsx` | Instrumental, speed, chords, auto-scroll, session. Absorbs `MoreOptionsSheet` |

**Reuse, do not rewrite:**

- **The offset drag already exists and works**, mouse *and* touch, with correct global-listener cleanup: [LyricsTimingView.tsx:80-160](frontend/src/features/player/components/subcomponents/settings-menu/LyricsTimingView.tsx#L80-L160). Lift verbatim into `useLyricsOffsetDrag.ts`.
- Save-to-LRC (`applyOffsetToLrc` + `useUpdateSong`): [LyricsTimingView.tsx:44-70](frontend/src/features/player/components/subcomponents/settings-menu/LyricsTimingView.tsx#L44-L70).
- Search/paste dialogs and their update mutations: [LyricsEditView.tsx](frontend/src/features/player/components/subcomponents/settings-menu/LyricsEditView.tsx) wraps `LyricsFetchDialog` + `PasteLyricsDialog` — becomes the search button's target on both surfaces.
- Fader visuals: `Slider variant="performance"` in [slider.tsx:66-80](frontend/src/components/ui/slider.tsx#L66-L80) is already a mixer fader. Do not restyle it.
- Volume toggles and size conversions: [usePerformanceControlsLogic.ts](frontend/src/features/performance/hooks/usePerformanceControlsLogic.ts) and [performanceControls.ts](frontend/src/utils/performanceControls.ts).

**Backing availability:** `backingVocalUrl` on `useKaraokePlayerStore` is `""` for two-track songs — use that as the `disabled` signal. `backingVocalVolume` is not on `useKaraokePlayer`'s return; read it from the store (or extend the hook).

### New: `frontend/src/features/player/components/stage/`

| File | Purpose |
|---|---|
| `StageLayout.tsx` | The 3-col grid, rail collapse state, dim-on-play |
| `StageQueueRail.tsx` | Right rail: Singing Now, Up Next rows, session QR. Replaces the deleted queue components |
| `StageTransport.tsx` | Prev / play (88px) / next, timecodes, `ProgressBar` |
| `useStageRails.ts` | Collapse derived from `isPlaying` + pointer activity |

### Rewritten

- **[Stage.tsx](frontend/src/pages/Stage.tsx)** — keeps session recovery and the queue WebSocket effect as-is; renders `StageLayout` instead of the centred column + "Up Next" list.
- **[KaraokePlayer.tsx](frontend/src/features/player/components/KaraokePlayer.tsx)** — becomes the centre column only: title, `LyricsDisplayWithCountIn`, `ChordCarousel`, `SongEnded`/`QueueEnded`, error state. All chrome, hover overlays and the mouse-idle timer are removed.
- **[PerformanceControlsPanel.tsx](frontend/src/features/performance/components/PerformanceControlsPanel.tsx)** — renders `<ControlsStrip density="touch" />` plus its existing transport and the stage-fullscreen button. Keeps `sessionWebSocketService.toggleFullscreen()`.

### Deleted

`BottomControlsArea.tsx` · `SettingsMenu.tsx` and all six `settings-menu/*` views · `MoreOptionsSheet.tsx` · `VolumeChannel.tsx` · `LyricsTimingControls.tsx` · `KaraokeQueueList.tsx` · `KaraokeQueueItem.tsx`

Update the barrels: [subcomponents/index.ts](frontend/src/features/player/components/subcomponents/index.ts), [performance/index.ts](frontend/src/features/performance/index.ts), [lyrics/index.ts](frontend/src/features/lyrics/index.ts), [queue/index.ts](frontend/src/features/queue/index.ts). `QRCodeDisplay` stays — `SessionInfoDisplay` and `SessionEndModal` import it.

### Untouched

`useKaraokePlayer` · `useKaraokePlayerStore` · `useAudioControlsStore` · `LyricsDisplayWithCountIn` · `KaraokeLyricsRenderer` · `ChordCarousel` · `ProgressBar` · `SongEnded` / `QueueEnded` · all backend and WebSocket code.

**Sync plumbing needs no work.** `useKaraokePlayerStore` already broadcasts via `updatePerformanceControl` (line 465) and handles inbound at lines 536/546/570. The rot is UI-level only.

## Fullscreen

Once the page *is* the player, fullscreen's only remaining job is hiding browser chrome. Keep `usePlayerUI`'s `toggleFullscreen` and — critically — its **`toggle_fullscreen` WebSocket listener**, which is how the phone drives the TV. Drop `FullscreenContainer`'s hover plumbing and `SettingsMenu`'s `fsContainer` portal juggling, which exist only to make popovers work inside the fullscreen element.

## Keyboard

Keep the existing spacebar play/pause. Add arrow-key offset nudge and seek — the keyboard is already in the room and it's the fastest fix when lyrics drift.

## Order of work

1. **Shared controls** (`features/performance/controls/`) — ~4h. Build first so both surfaces land together and cannot drift.
2. **`StageLayout` + left rail** renders `<ControlsStrip density="tv" />` — ~2.5h.
3. **`PerformanceControlsPanel`** rewritten onto the same strip — ~1.5h.
4. **`StageTransport` + `StageQueueRail`** — ~3h.
5. **Rail collapse, dim-on-play, lyric size bump** — ~1.5h.
6. **Deletions + barrel cleanup** — ~1.5h.

Roughly 12-14 hours. Step 1 is the load-bearing one; steps 5-6 can slip without blocking use.

## Verification

Services already run under tmux — **do not start or restart them** (API and frontend hot-reload; only Celery needs manual restarts, and nothing here touches it).

```bash
cd frontend
pnpm run type-check
pnpm run lint:check
pnpm run format:check
pnpm run test:run          # KaraokeLyricsRenderer, activeLineTiming, useKaraokePlayerStore
tmux capture-pane -t open-karaoke:0.1 -p | tail -20   # frontend build errors
```

End-to-end, in a real session:

1. Open `/stage`, load a song. Confirm the three columns fill the viewport with no `aspect-video` letterboxing and no page scroll.
2. Move both faders on the TV; confirm audio changes and the phone's faders follow.
3. Move them on `/controls`; confirm the TV follows. This exercises the `updatePerformanceControl` round trip.
4. Drag the offset readout on both surfaces; confirm lyrics shift and the save-to-LRC button appears only with synced lyrics and a non-zero offset.
5. Open lyrics search **from the phone** — the capability that did not previously exist there.
6. Play; confirm rails collapse to icon strips and chrome dims without anything unmounting or shifting.
7. Load a two-track song; confirm the Backing fader is disabled, not hidden, and the layout does not move.
8. Hit the phone's fullscreen button; confirm the TV toggles.
9. Navigate away mid-song; confirm the mini-player still takes over.

## Defects found while planning

Not in scope to fix separately — the first two die with their components:

1. **[LyricsTimingControls.tsx:44-56](frontend/src/features/lyrics/components/LyricsTimingControls.tsx#L44-L56)** — the `+50` button sets `+100` and the `+100` button sets `+50`. Labels and values are swapped. This is the phone's offset control today.
2. **Double spacebar binding** — [usePlayerUI.ts:88-92](frontend/src/features/player/hooks/usePlayerUI.ts#L88-L92) registers a no-op `" "` handler that still calls `preventDefault()`, while [KaraokePlayer.tsx:80-84](frontend/src/features/player/components/KaraokePlayer.tsx#L80-L84) registers the real one. Consolidate into one handler.
3. **Two competing offset controls** — `LyricsTimingView` (drag + save) and `LyricsTimingControls` (knob, no save). Unifying on the former removes the divergence.
