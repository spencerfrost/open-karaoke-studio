# Stage Mode — the stage becomes a full-screen app tied to a session

> **Unit 2** of [2026-08-29-sequencing.md](2026-08-29-sequencing.md).
> **Blocked by** [unit 1 — session lifecycle](2026-08-29-session-lifecycle.md) and
> [unit 0 — KJ removal](2026-08-29-kj-removal.md). Runs in parallel with the rotation
> roster; the two meet at the handoff screen, which this plan does **not** build.

## Context

The bottom nav bar was built for phones and it works there. On the TV it is wrong — not because navigation is wrong, but because phone-sized chrome is pinned to the bottom of a screen someone is looking at from across the room, and because it makes the stage feel like a page in a website rather than a thing you walk up to.

The real usage is an arcade cabinet. TV across the room, **mouse on the mic stand**, keyboard nearby but awkward. Someone walks up, picks a song, sings it, and the screen moves on. While a song is playing the TV **recedes but stays live** — the rails collapse to icon strips and the chrome dims to 35%, and any mouse move or keypress brings it straight back. Browsing, queuing and adding are better done on phones, but the person at the mic has the mouse and can reach the transport, the faders and the lyrics offset without touching anything else.

So the TV is not a page with a nav bar. It is a full-screen app with two resting states — song select and performance — that bounces between them, plus an add-song detour for the person standing at the mic who wants something the library does not have.

The phone app is already correct and is **not touched by this plan**. The desktop app (library, add, settings, admin, nav bar) is also **not touched**, apart from one addition noted below.

Follows on from [2026-08-28-stage-redesign.md](2026-08-28-stage-redesign.md), which already built the performance screen: [StageLayout.tsx](frontend/src/features/player/components/stage/StageLayout.tsx) is a full-viewport three-column player whose rails collapse during playback. This plan builds everything *around* it.

## Settled decisions

| Decision | Choice |
|---|---|
| What stage becomes | A full-screen **mode**, not a page. No nav bar, ever |
| Nav bar elsewhere | Untouched. Phone and desktop app keep it |
| Library / Add on the TV | **Mirrored** into stage as screens — the phone and desktop versions stay as they are |
| Library sizing | Fine as-is. This is not a 10-foot re-scale of the library |
| Navigation model | Advance by doing. One back affordance on select-family screens only |
| Queue | Stays a rail. Never a destination |
| During a performance | Lyrics lead; controls recede but stay reachable. Nothing unmounts |
| Session lifetime | A session is created by **entering stage mode**, and only there |
| Exiting stage | Prompts: end the session, or keep it running |
| Adding a song | Existing contextual paths stay; add one FAB on song select for the cold start |
| Between-songs screen | **Not this plan.** It is the rotation work's handoff screen (unit 4) |
| Attract / idle screen | Deferred. Polish, not blocking |

## The screens

Stage mode owns these. They are screens in a shell, not routes with shared chrome.

| Screen | State | Notes |
|---|---|---|
| **Song select** | Resting / home | The mirrored library. Mouse-driven browse and search. Where the exit control and the add FAB live |
| **Song confirm** | Transient | Who is singing; play now or add to queue. The moment the cabinet asks "ready?" |
| **Add song** | Detour | The mirrored add flow. Must not end in a spinner — see below |
| **Performance** | Resting | Already built. Lyrics, rails, transport. Fully interactive — but no *navigation* affordances |
| *Attract / idle* | Deferred | Join QR, session code, recently played. May just be song select with a QR on it |

**The between-songs screen is not in this plan.** An earlier draft listed it here as
deferred polish. It is the same screen the rotation work calls the handoff screen — who is
up, what they are singing, and how to change either — and it is that plan's central piece,
not a placeholder. Stage mode provides the shell it renders into and stops there. See
[unit 4](2026-08-29-sequencing.md).

### Transitions

- **select → confirm → performance** — the main path, driven by clicking.
- **performance → select** — needs building. The nav bar was the only path and it is going away. **This is the one genuinely missing piece.**
- **select → performance** — the reverse. After queueing something, get back to the player.
- **select ↔ add** — both directions; back affordance on the add screen.
- **add → select** — on submit, *not* on completion. Download plus Demucs takes minutes, so the add screen hands back immediately with a "we'll have it shortly" acknowledgement and the song surfaces in the library when it lands.

## Getting into the add flow

Three paths exist today. Two of them are good and survive unchanged — both already navigate to `/add?q=...`, so inside stage mode they become screen transitions rather than route changes, with no change to their logic:

- **YouTube fallback on an empty search** — [SongResultsGrid.tsx:44](frontend/src/features/library/components/SongResultsGrid.tsx#L44). Requires zero results first, so it only ever appears when it is relevant.
- **"Find more from {artist}"** at the end of an artist's section — [BrowseArtistCard.tsx:16](frontend/src/features/library/components/BrowseArtistCard.tsx#L16). Deep-links into add with `browseArtist=true`.

The third is the nav bar's Add tab, which is going away on the TV.

Both surviving paths are *contextual* — they appear once you have discovered a gap. What is missing is the cold start: "I want to add a song and I am not searching for one yet." A floating action button on song select covers exactly that, and is the cheap answer. No redesign of the add flow itself.

## Sessions

This is the part that got simpler once stage became a mode — but it is **not free**. Both
branches of the exit prompt below land on code that does not work today: `/leave` 404s by
construction, and 30s of host disconnect deletes the session and cascades the queue away.
[Unit 1](2026-08-29-session-lifecycle.md) fixes both, and must ship before this.

**Today**, `createSession` defaults to `deviceType: "stage"` ([sessionStore.ts:175](frontend/src/stores/sessionStore.ts#L175)) and `SessionEntry` calls it whenever `SessionGuard` blocks any session-required route ([SessionEntry.tsx:131](frontend/src/components/SessionEntry.tsx#L131), [:141](frontend/src/components/SessionEntry.tsx#L141)). So merely landing on the library with no session spins up a stage session. That is why sessions appear practically every time an admin logs in.

**After**, session creation happens in exactly one place: entering stage mode. [Stage.tsx:45-60](frontend/src/pages/Stage.tsx#L45-L60) already does create-or-recover on mount, so most of the work is deleting the incidental paths, not building a new one.

The model:

- **No session running** → the desktop app exactly as it is today.
- **Session running** → stage mode, full screen.
- **Exit stage** → prompt: *End session* or *Keep running*. Keeping it running is the escape hatch (drop out of full screen for a minute, check something on the desktop) and re-entering stage recovers the same session — `recoverSession` and `createSession` are already distinct in the store, and the server already gives sessions a duration.

The desktop app gets **one** addition: while a session is live, a way back into stage. Not a second mode — just an affordance that makes that state read as temporary.

`EndSessionButton` remains the explicit end — rewired to unit 1's `DELETE /api/sessions/{id}`
rather than the broken `/leave` call it makes today. Exit and End are already different
things in the code; this makes them visibly different in the UI.

**Logout needs a new home.** Its only call site in the app is
[SessionEntry.tsx:289](frontend/src/components/SessionEntry.tsx#L289) — inside the host
card this plan deletes. It goes in Settings, as a plain account section. Without that there
is no logout anywhere.

**Where the auto-create actually dies.** `SessionEntry` fires because `/` and `/add` are
wrapped in `SessionGuard` with `requireSession` defaulting true
([App.tsx:43-58](frontend/src/App.tsx#L43-L58)). Relax those two and the auto-create
paths have nothing left to trigger them — the `joinAsHost()` block in
[SessionContext.tsx:42-47](frontend/src/contexts/SessionContext.tsx#L42-L47) and the
host effect in [SessionEntry.tsx:64-92](frontend/src/components/SessionEntry.tsx#L64-L92)
just get deleted, with no replacement screen to build. Performers still need the gate:
`/controls` stays session-required and the join-by-code path (`QRJoinPage`, `SessionEntry`'s
performer half) is untouched. `SessionEntry` survives as the *performer* entry — it loses
only its host card.

## Open questions

- **A phone queues while the TV sits in song select.** Does the TV react and move, or stay put?
- **Exit control placement.** Song select only, never during a performance, and deliberate enough that nobody at the mic stand hits it by accident.

> **Resolved, and it was never really open: aborting a stuck song.** An earlier draft claimed
> the TV takes no input during a performance and that skip/abort therefore had to come from a
> phone. That is not what shipped. `useStageRails` re-opens the rails on any `mousemove`,
> `pointerdown` or `keydown`; the collapse only hides the strip, so
> [StageTransport](frontend/src/features/player/components/stage/StageTransport.tsx) stays mounted
> and clickable at 35% opacity, and
> [useStageKeyboard](frontend/src/features/player/components/stage/useStageKeyboard.ts) keeps
> Space, the arrows and F live throughout. Skip already works from the mouse on the mic stand.
> Nothing to build.

## Prerequisite: the KJ is gone

An earlier draft filed this as "out of scope, but noted." It is now
[unit 0](2026-08-29-kj-removal.md) and ships first, for two reasons this plan depends on:

- **`isHost` collapses to one meaning.** Removing `user.isHost` leaves only the device role,
  so the split becomes a rename — `isStageDevice` plus `isSessionOwner` derived from
  `host_user_id`. Stage mode makes the device meaning *load-bearing* (it decides whether to
  render a full-screen app), so conflating the two is riskier after this change than before
  it. Compare `isHost` from the session store with `user.isHost` from the auth store in
  [AppLayout.tsx:31-70](frontend/src/components/layout/AppLayout.tsx#L31-L70).
- **The dead feature has a live trap.** Approval mode is not inert:
  [karaoke_queue.py:367-375](backend/app/api/karaoke_queue.py#L367-L375) really does mark
  submissions `pending`, and [:336](backend/app/api/karaoke_queue.py#L336) really does
  reject on `queue_open: false`. The only UI that can approve a pending song is the dashboard
  nobody opens.

If unit 0 slips, this plan can still land — but the `isHost` rename then has to happen here
instead, against code that is on its way out.
