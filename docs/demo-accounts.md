# Demo Accounts

The demo account pool lets you publish **one** username/password on a portfolio
or landing page so a visitor can genuinely host a karaoke session — search
YouTube, download a song, get AI-separated vocals/instrumentals, run a session —
without exposing your homelab to unbounded compute or letting two visitors
collide into the same session.

The feature is **disabled by default** and only turns on when you set the alias
environment variables (below).

## How it works

- **One published alias, many real accounts.** You publish a single credential
  (`DEMO_LOGIN_USERNAME` / `DEMO_LOGIN_PASSWORD`). Behind it sits a small pool of
  ordinary host accounts flagged `is_demo`. On login the server resolves the
  alias to a *free* pool account and issues that account's token — visitors never
  see the pool.
- **A session starts immediately.** Sessions are per-account, not per-login, so a
  shared account would mean shared sessions. To prevent that, an alias login
  eagerly creates the chosen account's karaoke session and starts its clock right
  away. Two simultaneous visitors get two different accounts and two isolated
  sessions.
- **The pool can fill up.** If every pool account already has a live session, the
  alias login returns a friendly `503` ("The demo is busy right now — try again
  in a few minutes"). Accounts free up automatically when their session expires.
- **Downloads are quota-limited.** Only new-song downloads cost compute (queuing
  an existing library song is unlimited). Demo sessions are capped per session and
  the whole pool shares a daily budget.

Everything else is the real application — there is no demo watermark or crippled
mode. That is the point.

## Defaults

| Setting | Value | Where |
|---|---|---|
| Pool size | 3 accounts (`demo-pool-1..3`) | you seed these |
| Session length | 15 minutes (`0.25h`) | seeded `HostSettings` |
| Downloads per session | 3 | `DEMO_SESSION_DOWNLOAD_LIMIT` |
| Downloads per day (whole pool) | 20 | `DEMO_DAILY_DOWNLOAD_LIMIT` |
| Demo token lifetime | 30 minutes | `DEMO_TOKEN_EXPIRE_MINUTES` |
| Songs per singer | 5 | seeded `HostSettings` |
| Queue mode | instant | seeded `HostSettings` |

The daily budget is sized so ~10 visitors doing 1–2 songs each fit comfortably,
while a leaked credential can't run up unbounded separation jobs. The numeric
limits live as constants in `backend/app/services/demo_service.py`.

## Configuration

Set the alias credentials in your `.env`. When either is unset, the feature is
off and these credentials behave like any other invalid login.

```bash
# Public demo alias (published on your portfolio)
DEMO_LOGIN_USERNAME=demo
DEMO_LOGIN_PASSWORD=change-me-to-something-public
```

The pool accounts each also have their own private password (set when you seed
them). Those still work for individual login and are useful for testing — the
alias is simply the public front door.

## Seeding the pool

Pool accounts are created with the `manage_users` script. The `--demo` flag
implies `--host` and seeds a matching `HostSettings` row (15-minute sessions,
instant queue, 5 songs per singer).

```bash
cd backend
source venv/bin/activate

# Create three pool accounts with strong, private passwords
python scripts/manage_users.py create --username demo-pool-1 --password "$(openssl rand -hex 12)" --demo
python scripts/manage_users.py create --username demo-pool-2 --password "$(openssl rand -hex 12)" --demo
python scripts/manage_users.py create --username demo-pool-3 --password "$(openssl rand -hex 12)" --demo

# Confirm — the Host and Demo columns should both read "Yes"
python scripts/manage_users.py list
```

The pool size is however many `is_demo` accounts you seed; three is a sensible
default. The pool accounts' private passwords are never published — only the
alias is.

::: tip Migration
The `is_demo` / job-attribution columns ship in an Alembic migration. Make sure
you've run `alembic upgrade head` before seeding.
:::

## What a visitor experiences

1. They log in with the published alias and immediately land in a live,
   15-minute session on a free pool account.
2. They can browse the library, queue existing songs freely, and download up to
   3 new songs into their session.
3. On the 4th download they get: *"Demo limit: 3 new songs per session. You can
   still queue anything already in the library."*
4. When the pool's shared daily budget is spent, new downloads return: *"The
   demo's daily download budget is used up — existing library songs still work."*
5. If everyone's busy at login time, they see the "demo is busy" message and can
   retry shortly.

These messages are surfaced verbatim in the login form and the add-song toast —
no frontend changes are needed to adopt the feature.

## Guardrails

Because demo accounts are real logins, a few actions are blocked so a visitor
(or a leaked credential) can't degrade the pool:

- **Can't change host settings.** Otherwise a visitor could widen their session
  to 24 hours and squat a pool slot all day.
- **Can't modify the account.** No changing the pool account's password or
  display name.
- **Short-lived tokens.** Demo JWTs expire after 30 minutes, so a saved token
  can't keep minting fresh sessions and budgets for days.
- **Quota is enforced before anything is created.** The add-song flow creates a
  library record and *then* requests the download; the quota is checked at both
  steps, so an over-quota visitor never leaves an orphaned, track-less song
  behind.

## Operations & troubleshooting

- **A slot seems stuck.** Sessions expire lazily — a pool account frees up as
  soon as its `expires_at` passes; there is no cleanup job to wait on. If a slot
  won't free, check the account's active `karaoke_sessions` row.
- **Give it more headroom.** Seed more `--demo` accounts (more concurrent
  visitors) or adjust the constants in `backend/app/services/demo_service.py`
  (per-session / daily download caps, token lifetime).
- **Change session length.** Update the seeded account's
  `HostSettings.session_duration_hours` (it's a float — `0.25` = 15 minutes).
- **Turn the feature off.** Unset `DEMO_LOGIN_USERNAME` / `DEMO_LOGIN_PASSWORD`.
  Existing pool accounts remain but are no longer reachable via the alias.
- **Attribution.** Every job records the `session_id` and `user_id` that started
  it, which is what the quota counts against and is generally useful for
  debugging who downloaded what.

## Portfolio copy

A one-liner to publish alongside the alias credentials:

> **Try it live** — log in with `demo` / `<password>`. Sessions last 15 minutes
> and allow 3 new song downloads; everything else is the real app.

## Not included

- No CAPTCHA or IP throttling on the alias — the quotas already bound worst-case
  compute. Revisit only if abused.
- No demo-mode banner or watermark — it's the real application by design.
