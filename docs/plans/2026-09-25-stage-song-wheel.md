# Stage song wheel

Replaces [2026-08-30-stage-cabinet.md](archive/2026-08-30-stage-cabinet.md), which is kept for its
ideas. Builds on [unit 2 — stage mode](archive/2026-08-29-stage-mode.md). Not in the
[sequencing](2026-08-29-sequencing.md) table; nothing in the rotation chain depends on it.

**Prototype:** [prototypes/2026-09-25-song-wheel.html](prototypes/2026-09-25-song-wheel.html)
(open it in a browser; the "Tune the wheel" button exposes the numbers below). Also published
as an artifact: <https://claude.ai/artifact/RE7TN2Zbkh3n2Gv6JNDUqD>.

**Follow-up:** artist images and a song info card are planned in
[2026-09-25-stage-wheel-artwork.md](2026-09-25-stage-wheel-artwork.md).

## Why

The stage's song select screen renders the regular `LibraryScreen`
([SongSelectScreen.tsx](../../frontend/src/features/stage/screens/SongSelectScreen.tsx)). That
library was designed when it *was* the app. Stage mode has since turned the TV into a
walk-up-and-sing screen, and the library still behaves like a web page: a long scroll of artist
accordions.

How the room actually works:

- A **wireless mouse** sits on a shelf on the mic stand. That is how singers pick songs today.
- A **keyboard** lives on the coffee table. Someone else usually grabs it to type.
- The plan is to add a **reprogrammed numpad** at the mic stand. This plan designs for plain
  arrow keys, Enter and Back; mapping the numpad onto those is a later, separate job.

An accordion of ~600 artists cannot really be driven by up/down/enter/back. A wheel can: it is
the shape those four keys want, which is why DDR uses one. The mouse keeps working, and arguably
gets better, since its scroll wheel spins the song wheel directly.

## The design

Three columns (**Letter → Artist → Song**) sit on a cylinder whose axis is behind the middle of
the screen. The active column is at the front. The others sit further back and to the side.
Left/Right turns the cylinder. Up/Down moves within the column at the front.

```
 seen from above
                          · axis
                ╱                    ╲
         A–Z   ╱                      ╲   SONGS
      (further                          (further back,
        back)          ARTISTS            dimmer)
                    ━━━━━━━━━━━━━━
                       at the front
      ─────────────────── the TV ───────────────────
```

- **Text always faces forward.** Columns travel around the cylinder, but each one counter-rotates
  so its text is never angled. Side columns read as smaller and further away, not tilted.
- **No column surfaces.** Text on the background, no panels or borders. The selected row in the
  active column gets a soft glow behind it and glowing text.
- **Dimming compounds with depth.** One step back is shown at the side brightness; two steps
  back gets that squared (45% → ~20%).
- **Spacing follows real widths.** Neighbours are spaced by their widths plus a gap, measured
  along the curve, so the narrow letter column sits close to the artists instead of taking an
  equal slice of the circle.
- **The cursor stays centred.** Each list moves through a fixed selection row, like a DDR wheel.

### Controls

| Input | Letter | Artist | Song | Confirm card |
|---|---|---|---|---|
| ▲ ▼ | Previous / next letter that has artists | Previous / next artist | Previous / next song | — |
| ◀ ▶ | Change column | Change column | Change column | Choose button |
| Enter | Go to artists | See songs | Open "Sing it now / Add to queue" | Do it |
| Back | Leave the library | Leave the library | Back to artists | Cancel |
| Mouse wheel | Spins the column under the pointer and brings it to the front | ← | ← | — |
| Click | Side column: bring it to the front. Any row: go to it and on to artists | Side column: bring it to the front. Any row: go to it and on to songs | Side column: bring it to the front. Centred row: same as Enter; other rows: go to it | Buttons |

- **Left at the leftmost column does nothing.** It must not fall through to the performance
  screen, where Left would nudge the lyrics offset.
- **Back is the only way out of the library.**
- **Held ▲▼ ramps up.** The OS key repeat is ignored in favour of our own: the first repeat comes
  after ~350ms, then speed climbs from ~8 to ~36 rows/sec over about a second.

### Letters and artists are one cursor

The letter column is **derived from the artist cursor**, never stored separately. Sitting on
Fleetwood Mac and turning left lands on F. If they were two pieces of state they would disagree
after a scroll.

- All 26 letters plus `#` are always shown, so the geometry never shifts. Letters with no artists
  are greyed out and skipped by ▲▼.
- Leading articles are ignored for filing: "The Beatles" is under B.

### Starting values (from the prototype)

| Setting | Value |
|---|---|
| Column widths (letter / artist / song) | 130 / 560 / 620 px at 1600×900 |
| Gap between columns | 110 px |
| Cylinder radius | 1100 px |
| Turn duration | 320 ms, `cubic-bezier(.2,.8,.25,1)` |
| Side brightness | 45% one step back, squared per extra step |
| Hold-to-scroll top speed | 36 rows/sec |

These are the prototype's defaults. Tune them on the real TV before treating them as settled.

## How it fits the code

- **A new component tree for the stage.** The phone keeps `LibraryScreen` unchanged. The wheel
  shares the data hooks, not the components.
- **Data is already there.** `useArtists`
  ([useArtists.ts](../../frontend/src/hooks/api/useArtists.ts)) returns every artist with
  `songCount` and `firstLetter` in one request. Songs for the focused artist come from the
  existing songs-by-artist endpoint (`get_songs_by_artist` in
  [songs.py](../../backend/app/api/songs.py)).
- **Only the visible rows are rendered.** About nine rows per column, not 600. The accordion's
  mount cost (~600 rows × two React Query observers) is the reason song select is never
  unmounted in [StageShell.tsx](../../frontend/src/features/stage/StageShell.tsx). The wheel may
  let that special case go. Measure before removing it.
- **Keys are handled while the select screen is showing.** `useStageKeyboard` already switches
  behaviour by screen and backs off for inputs and dialogs. The wheel gets its own handler, active
  only while song select is up, following the same rules.
- **Confirm stays the existing screen.** The prototype's confirm card stands in for
  `SongConfirmScreen`. Enter on a song should open the real one; the card is not a new thing
  to build.
- **Search stays.** Put a quiet search affordance somewhere on the wheel screen (see open
  questions). Every song must still be reachable without typing.
- **Exit stage stays out of reach of the arrow keys.** Nobody walking up to sing should end the
  night by pressing Back one too many times.
- **Reduced motion** turns off the turn and scroll animations.

## Also in scope: two small fixes

These are independent of the wheel and can ship first.

### "Sing it now" opens a paused player

`handlePlayAs` in
[useSongActions.ts](../../frontend/src/features/songs/hooks/useSongActions.ts) queues and
plays the song, but
[StageLayout.tsx](../../frontend/src/features/player/components/stage/StageLayout.tsx) renders
`<KaraokePlayer>` without `autoPlay`, which defaults to `false`. The singer lands on a paused
player and has to press play. Fix: pass `autoPlay` and show a plain loading state until
`isReady`.

### Arrow keys on the performance screen

[useStageKeyboard.ts](../../frontend/src/features/player/components/stage/useStageKeyboard.ts)
binds ◀▶ to seek ±5s and ▲▼ to lyrics offset. Seek is rarely what anyone wants mid-song.
Proposed:

```
▲▼  vocal volume        ◀▶  lyrics offset
Space / Enter  play / pause
```

Seek stays on the transport and the restart button.

## Order of work

1. "Sing it now" autoplay fix.
2. Rebind the performance-screen arrow keys.
3. The wheel: the cylinder and billboard layout, then the columns with their shared cursor, then
   keys and mouse, then hold-to-scroll.
4. Wire Enter to the existing confirm screen and Back to the performance screen.
5. Try it on the TV, tune the numbers, then decide about unmounting song select.

## Open questions

1. **Leading articles.** The backend sorts by `DbArtist.name` and takes `firstLetter` from its
   first character. Check whether `name` already drops "The"; if not, strip it in one place,
   probably the API, so the phone's A–Z bar agrees.
2. **Odd first characters.** `firstLetter` is `#` only for digits. Names starting with
   punctuation or accented letters currently get their own letter. Fold them into `#` or their
   base letter.
3. **Musicals and soundtracks.** `useArtists` merges shows in as artists. Does that still read
   right on the wheel?
4. **Short song lists sit low.** With the cursor centred, a one-song artist shows a single row
   halfway down under empty space. Normal for a wheel; pulling short lists up may read better.
5. **Where search lives.**
6. **Column labels.** In the prototype, rows scroll up behind the column labels now that columns
   have no surfaces. Start each list's fade below its label.

## Parked

Ideas from the old plan, kept so they are not lost. None of them block the wheel.

| Idea | Note |
|---|---|
| Screen transitions (framer-motion, shared artwork between screens, animate-then-hide wrapper) | framer-motion is already a dependency. Screens are hidden with `display:none` for good reasons (see the old plan), so exit animations need a wrapper first |
| 3-2-1 countdown into a song | Could cover the audio load once autoplay works. A plain loading state comes first |
| Sound effects on cursor move and confirm | Needs an answer for mixing with the song audio |
| An on-screen key legend driven by the active controls | The prototype hard-codes one. A real one should read from the bindings so it cannot drift |
| A general input-scope stack | Only worth building if more screens get arrow-key control |
| More wheel sources ("Recently added", "Most sung", "By decade") | Each would be a different set of columns. Build the second one when it is wanted, not before |
| Blur mode at high scroll speed | Show only the big letter when rows go by too fast to read |
| Attract / idle screen | |
| Controls-strip mode (arrow keys over the mixer) | |
| NVIDIA Shield TV app | A TV remote's D-pad sends arrow keys, Enter and Back, so arrow-key-first work carries over |
