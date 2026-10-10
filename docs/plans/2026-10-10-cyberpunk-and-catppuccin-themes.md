# Cyberpunk and Catppuccin themes

Follows [the retro roles plan](2026-10-10-retro-style-pass.md), which added the surface ladder,
text tiers and decoration colors, and the [theme token migration](2026-07-19-theme-token-migration.md)'s
theme switching.

**Status:** ready to start. Cyberpunk exists as a rough block; Catppuccin isn't started.

## The rule

A role name says what something is for; each theme decides what it looks like. Nothing about a
role requires a solid color or a tint. Retro keeps its look by filling the roles with the tints
it already used. Don't change retro's values or restyle components toward one theme's look to
make another theme work. Give the new theme different values instead.

## What a theme controls

A theme is a `[data-theme="<id>"]` block in [index.css](../../frontend/src/index.css), plus an
entry in [themes.ts](../../frontend/src/lib/themes.ts) so Settings offers it. The block sets:

- **Page:** `--background`, `--foreground`, and `--page-bg` (a gradient or a flat color).
- **Text tiers:** `--foreground-dim` (counts, descriptions, subtitles) and
  `--foreground-faint` (column headings, durations, placeholder icons).
- **Surface ladder:** `--surface-sunk` (inputs and wells inside a panel), `--surface` (nav bars
  and panels), `--surface-raised` (headers and blocks inside a panel), `--surface-hover`
  (hovered or selected rows), and `--border` for lines.
- **Card, popover, muted:** `--card`, `--popover`, `--muted` and their `-foreground`s.
- **Brand:** `--primary` (the one thing that matters on screen), `--secondary`, `--accent`
  (default Button, focus ring, select and dropdown highlights, toggle on, scrollbar, slider fill,
  "Live" and preview status) and `--ring`, each with a readable `-foreground`.
- **Status:** `--destructive`, `--success`, `--warning`, `--info`, each with `-foreground`
  (text on the fill) and `-strong` (text on the card, popover and muted surfaces).
- **Decoration colors:** `--decor-1` to `--decor-4`, art rather than UI. The audio visualizer
  cycles through all four, and the progress bar and the wheel's glow use `decor-1` and
  `decor-2`. This is where a big palette shows off.
- **Glass and overlay:** `--glass` and `--glass-border` (tint bases for panels over album art and
  the stage backdrop; components add the opacity) and `--overlay` (scrims).
- **Effects and type:** `--glow-primary`, `--glow-accent`, `--radius`, `--display-font`,
  `--body-font`, `--accent-font`. Fonts load from the Google `@import`s at the top of index.css.
- **Decoration:** its own `.theme-pattern` and `.theme-texture` (selectors scoped to the theme),
  or none.

Things a block of variables can't do, like angled corners, glitch animations or a different
layout, would need per-theme component code and aren't part of this plan.

### Filling the roles on a dark page

Both themes here have a dark page, so the page is the bottom step and the ladder steps up from it
in solid colors:

- `card` is `surface`, `popover` and `muted` are `surface-raised`, and `card-foreground`,
  `popover-foreground` and `surface-foreground` are the theme's text color.
- `muted-foreground` is `foreground-dim`.
- `input` is `border`, so fields keep their outline.
- `-strong` status colors are lighter than the base, not darker (retro darkens them because
  its cards are cream).
- `primary-foreground` and `accent-foreground` must read on their fills. Neon and pastel fills
  usually want dark text.

## Cyberpunk

The rough block is in index.css and pickable in Settings: near-black page with a violet glow from
below, magenta primary, cyan accent, violet secondary, solid ladder, strong glows, 0.125rem
radius, Orbitron / Rajdhani / Share Tech Mono, a cyan grid for the pattern and scanlines for the
texture. Decoration colors are cyan, magenta, yellow, violet.

What's left is making it look good: tune the ladder steps so panels separate from the page,
check the glows aren't overwhelming on the stage, and decide whether the grid and scanlines
stay.

## Catppuccin (Mocha)

Mocha is Catppuccin's darkest flavor. Its palette is fixed and already comes as a ladder, so this
is mostly mapping:

| Role | Mocha color |
|---|---|
| `background` / `page-bg` | Base `#1e1e2e` (or a Mantle → Base gradient) |
| `foreground`, `card-foreground`, `popover-foreground` | Text `#cdd6f4` |
| `foreground-dim`, `muted-foreground` | Subtext 0 `#a6adc8` |
| `foreground-faint` | Overlay 1 `#7f849c` |
| `surface-sunk` | Mantle `#181825` |
| `surface`, `card` | Surface 0 `#313244` |
| `surface-raised`, `popover`, `muted` | Surface 1 `#45475a` |
| `surface-hover` | Surface 2 `#585b70` |
| `border`, `input` | Overlay 0 `#6c7086` |
| `primary` | Mauve `#cba6f7` |
| `secondary` | Lavender `#b4befe` (barely used; any accent works) |
| `accent`, `ring` | Pink `#f5c2e7` or Peach `#fab387` |
| `success` / `warning` / `info` / `destructive` | Green `#a6e3a1` / Yellow `#f9e2af` / Blue `#89b4fa` / Red `#f38ba8` |
| `decor-1` to `decor-4` | Four of its accents, e.g. Teal `#94e2d5`, Mauve, Peach, Pink |
| `glass` | Text |
| `overlay` | Crust `#11111b` |

Text on the pastel fills (`primary-foreground` and the other `-foreground`s) is Crust or Base.
Pick the decoration colors and the accent by looking at the visualizer and the stage.

## What a theme can't reach yet

These spots ignore the theme and may look off. Fix them as part of this work if they do:

- **Slider thumb shadows** are fixed warm colors (`rgba(255,200,100,…)` in
  [slider.tsx](../../frontend/src/components/ui/slider.tsx)'s `performance` variant).
- **`text-secondary` used as text** in
  [SongInfo](../../frontend/src/features/songs/components/song-card/SongInfo.tsx) and
  [WebsocketStatus](../../frontend/src/features/session/components/WebsocketStatus.tsx), and the
  `outline-dark` Button. It's weak on any dark page.
- **Glass opacities** are fixed in components (`bg-glass/5`, `bg-overlay/85` and so on). A
  theme sets the base color but not how strong the tint is. Fine for dark themes.
- **Orange-tinted extras.** 53 uses of `primary` at an opacity (`bg-primary/20`, etc.) follow
  the theme's primary, which may be more than a neon or pastel theme wants.
- **The shadcn `dark:` styles never apply,** because nothing sets `.dark` on the page. A dark
  theme could set it from `useApplyTheme`, but that changes buttons, inputs, tabs and checkboxes
  at once. Decide by trying it.

## Checks for each theme

- Walk every page in it: the stage, library, add song, player, performance controls, admin and
  settings, plus lyrics on the TV from across the room. Opening `/stage` as the host in a
  headless browser takes over the live session, so walk it in a real browser.
- Switch themes while a song plays: the visualizer re-reads its colors.
- The QR code still scans (it sits on a `foreground`-colored frame, so a dark theme's light text
  color works).
- Status colors read on cards and on the page.
- Retro looks unchanged.

## Later, maybe

A light theme (Catppuccin Latte). The page becomes the lightest step and the ladder steps down
from it, which each theme already decides for itself. What still assumes a dark page: `glass`
is a light tint and `overlay` is a dark scrim, so both flip, and the stage's scrims need a check.
