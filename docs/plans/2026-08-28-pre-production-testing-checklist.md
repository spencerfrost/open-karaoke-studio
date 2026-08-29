# Pre-Production Testing Checklist — 2026-08-28

## Context

`develop` is 40 commits ahead of `origin/develop` (nothing pushed yet). This
document tracks what those commits changed and what to click through before
pushing and updating production. Once pushed and verified, this checklist is
historical — it does not need to be kept in sync with future work.

Full commit range: `origin/develop..develop` (`3bb615224`..`6add45ec5`).

## 🔴 Highest risk — test these first

### WebSocket host authority fix (`058c7724b`)

Host status on `/ws/session` was derived from a `device_id` query param that
the registered route never actually declared, so FastAPI never populated it —
`is_host` was **false for every connection in production** (774/774 by the
commit's own count). That silently broke host→performer sync and session
cleanup. It's now fixed by authenticating the host over the socket with their
JWT instead of a spoofable device token.

- [ ] Start a session as host on one device, join as a performer on another —
      confirm playback play/pause, song-loaded, and queue updates actually
      propagate to the performer (this was the broken path).
- [ ] Close the host's tab/browser and confirm the session gets marked
      inactive instead of orphaned.
- [ ] Refresh the host page mid-session and confirm it reconnects as host
      (not a stray second session).

### Demo account pool + quota (`7ce096045`, `176e79956`, `539702dd1`, `398779fc9`, `4a7a56864`, `0fb87551b`)

New shared/demo login with download quotas and guardrails.

- [ ] Log in via a demo alias, confirm quota is enforced on both "add song"
      and the YouTube download path (not just one).
- [ ] Confirm demo accounts can't change host settings (session duration) —
      explicitly blocked to prevent slot-squatting.
- [ ] Confirm quota exhaustion returns a real 429/403, not a 500.

### Auth on song/audio endpoints (`34f4165d1`, `15ce1fcb9`, `f32bc3f35`)

Audio track serving was made unauthenticated while player bearer-token
handling and song mutation auth headers were fixed.

- [ ] Play a track as a normal (non-demo) user end-to-end.
- [ ] Confirm song create/update still requires auth and works.

## 🟡 Feature/behavior changes — worth a pass

- [ ] **In-app failure recovery** (`2a082df53`, `17b132042`) — songs that fail
      processing now surface a plain-language error + retry action in the
      song header, performer drawer, and admin audit tab. Force a
      deliberately-failing download (e.g. bad URL) and confirm the retry
      button re-dispatches the job.
- [ ] **Age-restricted YouTube downloads** (`0e6a723c9`) — cookie-file support
      for downloads that need auth on YouTube's end. Test one against a video
      that currently fails without cookies.
- [ ] **Duration parsing fix** (`f69ea6ce0`) — YouTube duration strings →
      seconds. Spot-check a song's displayed duration matches actual playback
      length.
- [ ] **Show name field** (`f05dae27b`, `b1c4ad591`) — new metadata field for
      musicals/soundtracks. Check it displays and edits correctly.
- [ ] **Artwork hover preview** (`7b1e1851c`) — hovering a library card
      previews the song. Quick UI smoke test.
- [ ] **iTunes metadata search removed** (`b38ac0ca8`) — confirm nothing in
      the UI still references it (dead links/buttons).

## 🟢 Lower risk — visual/infra only

- [ ] Large theming pass tokenizing colors across components (`a534d4b7a`,
      `6b1195146`, `5fe2ccb7a`, `0f29b9d0b`, `de988c279`, `f69e9772d`) — visual
      once-over of the main screens (library, player, admin); no logic
      changed. See [2026-07-19-theme-token-migration.md](2026-07-19-theme-token-migration.md)
      for the broader plan this is part of.
- [ ] Build now fails on TypeScript errors (`f7daa9323`) — good to know if a
      deploy suddenly breaks that didn't before.
- Test DB isolation, prettier reformat, dockerignore/symlink cleanup, docs —
  no user-facing behavior, no action needed.

## Priority

The WebSocket host-authority fix and the demo quota system are the two worth
budgeting real time for — everything else is either additive or cosmetic.
