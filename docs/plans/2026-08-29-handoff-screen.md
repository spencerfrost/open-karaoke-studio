# Unit 4 — The handoff screen

Part of [2026-08-29-sequencing.md](2026-08-29-sequencing.md). Depends on **both**
[unit 2 — stage mode](2026-08-29-stage-mode.md) (the shell it renders into) and
[unit 3 — roster + rotation](2026-08-29-roster-and-rotation.md) (the order it reads).

Design source: [The Rotation Problem](https://claude.ai/code/artifact/e8bcfb43-9e1b-4b5d-8bbf-12d242defb6c),
section 05 / phase 3.

## Context

The gap between songs is the only moment the rotation is actually load-bearing. The roster,
the lap integer and the sort all exist so that **this screen can answer one question
correctly, in front of everybody, without the host getting up.**

This is the screen the stage-mode plan originally listed as a deferred "between songs /
attract" nicety. It is not polish — it is the part guests operate.

Today the moment is split across two components chosen by a length check in
[KaraokePlayer.tsx:152-166](frontend/src/features/player/components/KaraokePlayer.tsx#L152-L166):
`hasNextSong` renders [SongEnded](frontend/src/features/player/components/subcomponents/SongEnded.tsx),
otherwise [QueueEnded](frontend/src/features/player/components/subcomponents/QueueEnded.tsx). They
share no layout, no hierarchy, and no concept of a person.

## Merging them isn't cosmetic — it's what makes the logic tractable

Once ordering comes from a roster, **"the queue is empty" stops being a state.** It collapses
into one reading of the question the screen always asks: *whose turn is it, and do they have
a song?* An empty queue is not a conclusion — it is Sarah's turn with nothing in her slot.

That reframing matters because today's empty-state copy ("Queue Complete! 🎉 / No more songs
left to sing") announces the end of a party that is still very much happening, and every
suggestion tapped from it is filed under the literal string `"Host"`
([QueueEnded.tsx:101](frontend/src/features/player/components/subcomponents/QueueEnded.tsx#L101)).

The practical argument is stronger than the aesthetic one: **turn logic built into two sibling
components gets implemented twice and drifts** — the same way `build_queue_state()` and
`get_current_queue_state()` already did. One screen, one state machine.

## Settled decisions

| Decision | Choice |
|---|---|
| `SongEnded` + `QueueEnded` | **Merged into one screen.** The empty queue becomes a state, not a component |
| Layout | Three fixed slots, always in the same place |
| Turn ownership | **Server-authoritative.** The screen renders `session.current_turn`, it does not decide it |
| Passing someone over | Automatic, invisible, one lap forward. The person stepping up never adjudicates it |
| Stepping out | `Skip me for now` — deliberate, self-service, deactivates the seat |
| Rejected | A skip-or-delay dialog asking the room |
| Countdown | **Conditional**, and cancelled permanently by any tap |
| Empty slot | Push to the phone first; suggestion tiles as the fallback |

## Three slots, always in the same place

1. **Who's up** — the name, at headline scale. It is currently a small orange line under the
   artist ([SongEnded.tsx:159-161](frontend/src/features/player/components/subcomponents/SongEnded.tsx#L159-L161));
   the information is already there and the hierarchy is backwards.
2. **What they're singing** — the queued song with artwork and the auto-advance ring, *or*
   the empty-slot treatment that asks them to pick one. **The only slot whose content varies.**
3. **How to change either** — *That's not me* · *Skip me for now* · and who is on deck after
   this. Quiet, always present, never a modal.

## The state machine

| Situation | Slot 2 shows | Timer |
|---|---|---|
| Next seat has a song | Song, artwork, countdown ring | Auto-advance, 30s |
| Next seat is empty, others have songs | Pick-a-song prompt for that person | Auto-pass, ~45s |
| Nobody on the roster has a song | Pick-a-song prompt, still addressed by name | None — wait |
| Someone tapped anything | Unchanged | **Cancelled, does not resume** |
| Roster is empty | Join prompt + QR code | None |

The countdown becoming conditional is a real change from today's unconditional 30-second
timer. A clock ticking down while someone is halfway through deciding who they are is
hostile — so any interaction kills it permanently for that handoff. But removing it entirely
recreates the exact stall the feature exists to prevent, which is why the empty-seat case
gets its own slower timer instead.

## Skip or delay? Delay — and make it automatic

Someone steps up who is not the person named on screen. They tap **That's not me** and get the
roster as a grid of names plus *Someone else…* — **the same picker unit 3 builds for stage
walk-ups.** Second caller, no new component.

The important call is what happens to the person passed over, and the person stepping up must
never decide it. No dialog, no "should we skip Sarah?", no social weight on someone who just
wants to sing. One tap, and the pass-forward happens invisibly:

| | Action | Effect |
|---|---|---|
| **Automatic** | Passed over | Sarah's item takes `lap = current_lap + 1`. Up next lap, not next song. Keeps her seat, loses nothing cumulative |
| **Deliberate, self-service** | `Skip me for now` | Marks the roster entry inactive. The seat stops being offered until she queues something, taps back in, or the host restores her |
| **Rejected** | Ask the room | Makes a stranger adjudicate someone else's turn, in front of everyone, on a 30-second clock. Do not build the dialog |

Why a full lap rather than straight back to the front: with an immutable low `lap` she would
sort first again immediately, so the room would offer her the mic *and* pass her over every
three minutes for as long as she is gone. One lap of breathing room, one integer write.

**The same one-lap bump covers nobody stepping up at all** — the ~45-second auto-pass fires,
the turn moves on, and the night keeps going without anyone touching the host device. That is
the entire point of the feature, expressed as a timeout.

## Filling an empty slot

A full library browse on a TV, with no keyboard and a room watching, is the worst place to
pick a song. Two paths, in this order:

1. **Push it to the phone.** If the person has a device on the roster, the screen says
   "Sarah — check your phone" and waits; the moment she adds anything it flips to her song.
   She browses in private at full speed, and the WebSocket plumbing to make the flip instant
   already exists.
2. **Suggestion tiles on the TV.** The one-tap impulse path, and the fallback for anyone
   without a phone in hand. [useSongSuggestions](frontend/src/features/player/hooks/useSongSuggestions.ts)
   already renders four of these — but it seeds them from the song that just finished, by
   artist. **Re-seeding from the upcoming performer is genuinely new logic, not a prop
   rename**, though the hook's own doc comment already lists it as the intended next step.

## Make the turn server-authoritative

Once this screen holds decisions rather than just a countdown, it stops being safe as local
state — and today's version keeps its countdown in `useState` behind a `hasTriggeredRef`
guard.

Sarah tapping *I'm here* on her phone races Dan tapping *That's not me* on the TV. Both are
legitimate, both arrive over the same session socket. **The claim must be idempotent and
first-write-wins on the server**, broadcast to the room, with the screen rendering
`session.current_turn` rather than deciding it. Same session-keyed invariant as everything
else — see `.claude/rules/websocket.md`.

Also fix: `queueItems.find(item => item.position === 1)` has to become the server's computed
next item, not a client-side position scan.

## What stays off this screen

The line to hold: **the handoff screen owns turn-level decisions; session-level settings live
elsewhere.** Who sings next and what they sing belongs here, operable by any guest. Rotation
mode, and anything else that rewrites the rules of the night, does not — a mode toggle on the
TV lets a guest silently change how the whole evening works on their way to the microphone.

> The original design said those settings "stay on the host dashboard." There is no host
> dashboard — [unit 0](2026-08-29-kj-removal.md) deleted it. Their new home is
> [unit 3's open decision](2026-08-29-roster-and-rotation.md); this constraint is unchanged
> either way.

The deliberate escape hatches that *do* belong here are narrow and turn-scoped: claim the open
turn, pass yourself, bump the person who is about to leave.

## The rest of the room

- **On deck** — the person after next, in slot 3. Bars show two or three ahead so people can
  get ready, and it costs nothing: the list is already sorted.
- **Rotation ribbon** — `Spencer → Dan → Sarah → Spencer` between songs, so the circle is
  visible and nobody has to ask how it works. Suppressed below two active performers.
- **Phones** — "You're 3rd — about 11 minutes." Durations are already in the queue payload,
  so the ETA is a sum. It is the single most useful thing a phone can say at a party, and it
  removes most of the reason anyone interrupts the host.

## Verification

**Frontend** — run individually, never `pnpm run check`:

```bash
cd frontend
pnpm run type-check
pnpm run lint:check
pnpm run test:run
pnpm exec prettier --write "src/<only files touched>"
```

**Backend**

```bash
cd backend && source venv/bin/activate
pytest                                   # turn claim idempotency, auto-pass lap write
```

**End-to-end**, with three people and a real session — services run under tmux; do not
restart them.

1. Finish a song with someone queued → their **name** is the headline, their song is slot 2,
   the ring counts down and auto-advances.
2. Tap anything during the countdown → it stops and **does not resume**.
3. Tap *That's not me*, pick a different roster name → the new person's song plays, and the
   passed-over person reappears one lap later, **not** immediately.
4. Let the ~45s empty-seat timer expire with nobody at the TV → the turn passes on its own.
5. Reach a state where nobody has a song queued → the screen still addresses the next person
   by name and prompts, rather than announcing the party is over.
6. With that prompt showing, add a song **from that person's phone** → the TV flips to it
   without anyone touching the TV.
7. Race it: tap *I'm here* on the phone and *That's not me* on the TV at the same time →
   one wins, both screens agree, no split state.
8. Empty the roster entirely → join prompt and QR, no countdown.
