# Make the retro style consistent

Follows the [theme token migration](2026-07-19-theme-token-migration.md); needs its Stage 5
(theme switching) for step 1. Leads into [cyberpunk and Catppuccin](2026-10-10-cyberpunk-and-catppuccin-themes.md).

**Status:** done, apart from the accent, which is deferred (step 3). Walking the real pages in
cyberpunk is part of the [themes plan](2026-10-10-cyberpunk-and-catppuccin-themes.md)'s checks.

## Why

Retro's look stays as it is. What changes is how components ask for colors, so other themes can
restyle them: panels and dimmer text get named roles, decoration gets its own colors, and each
theme decides how those look. Retro answers with the tints it already used; dark themes answer
with solid colors.

Retro's page is a mid-tone orange gradient, which is why its panels are tints. Solid panels
only work when the page is the darkest (or lightest) step, and retro's page is neither.

## Steps

1. **A rough cyberpunk theme, to find what breaks.** A quick `[data-theme="cyberpunk"]` block,
   plus a `cyberpunk` entry in [themes.ts](../../frontend/src/lib/themes.ts) to pick it in Settings:
   near-black page, neon primary and accent, glows on, small radius. It doesn't need to look
   good. Walk the stage, library, add song, player, performance controls, admin and settings in
   it and list everything that looks wrong in cyberpunk but fine in retro. Each one is a place
   where a component assumes retro.

   **Found** (shared UI parts screenshotted in both themes, plus a code search). The pages
   themselves haven't been walked in cyberpunk.

   - **`accent-foreground` used as "light text".** The `pill` Button (`bg-primary/20
     text-accent-foreground`) and the focused select item (`focus:bg-primary/20
     focus:text-accent-foreground`). In cyberpunk the text is dark on a dark tint, so it
     disappears. On a cream card, the pill disappears in retro too. *Fixed:* the pill uses
     `text-foreground`, the select item `text-popover-foreground`.
   - **`card-foreground` used as "dark text on orange".** The big play buttons in
     [StageTransport](../../frontend/src/features/player/components/stage/StageTransport.tsx) and
     [PerformanceControlsPanel](../../frontend/src/features/performance/components/PerformanceControlsPanel.tsx)
     are `bg-primary text-card-foreground`, because retro's `primary-foreground` is cream and
     cream on orange is hard to read. The real fault is retro's `primary-foreground`, which
     also makes the `primary` Button and the default Badge hard to read. *Fixed:* retro's
     `primary-foreground` is black and the play buttons use it.
   - **`border-input` is near-black.** That works on russet and nearly vanishes on a black page
     (inputs and the select trigger lose their outline). CreateSessionScreen already overrides
     it for the stage. *Fixed in cyberpunk,* where `input` is the border color.
   - **`muted-foreground` is near-black in retro** because it's text for cream cards. Used on
     the page, it's unreadable. In cyberpunk it's a light dim, and the 215 uses look fine there.
     Text on the page should use the text tiers instead (step 4).
   - **`text-secondary` as text.** Unreadable on the retro page (rust on russet) and weak in
     cyberpunk (violet on black). Used in
     [SongInfo](../../frontend/src/features/songs/components/song-card/SongInfo.tsx) and
     [WebsocketStatus](../../frontend/src/features/session/components/WebsocketStatus.tsx). The
     `outline-dark` Button has the same issue.
   - **Card-colored thumbs and frames.** The slider and switch thumbs and the QR code's frame
     used `bg-card`, which is dark in cyberpunk. *Fixed:* they use `bg-foreground`; the QR code
     needs a light frame to scan.
   - **Warm shadows hard-coded on the slider thumb** (`rgba(255,200,100,…)`,
     `rgba(255,150,50,…)` in [slider.tsx](../../frontend/src/components/ui/slider.tsx)).
   - **The `dark:` variants never apply.** Nothing sets `.dark`, so the shadcn `dark:` classes
     on button, input, tabs, checkbox and others do nothing in either theme.
   - **Glows.** Only the two play buttons, the active lyric line and the wheel row use glow
     tokens, so most of the app looks the same whether glows are on or off.

2. **The surface ladder and text tiers.** Named roles for panels and dimmer text, so a component
   says what something is and each theme decides how it looks.

   | Role | Used for | Retro | Cyberpunk |
   |---|---|---|---|
   | `surface-sunk` | inputs and wells inside a panel | black at 20% | solid, darker than panel |
   | `surface` | nav bars and panels | russet | solid panel |
   | `surface-raised` | headers and blocks inside a panel | cream at 10% | solid, one step up |
   | `surface-hover` | hovered or selected rows | cream at 5% | solid, two steps up |
   | `foreground-dim` | secondary text: counts, descriptions, subtitles | cream at 65% | solid |
   | `foreground-faint` | column headings, durations, placeholder icons | cream at 45% | solid |

   Retro's cream `card` with dark `card-foreground` stays as it is. Themes with a dark page
   (cyberpunk, Catppuccin) use solid steps, and point `card`, `popover` and `muted` at them.

3. **The accent (deferred).** Teal does five jobs: the default Button, interaction states (focus
   ring, highlights, toggle on), chrome (scrollbar, slider fill), status ("Live", preview ring)
   and decoration. Decoration now has its own colors, `decor-1` to `decor-4`: the audio
   visualizer cycles through all four, and the progress bar and the wheel's glow use the first
   two. Retro's are teal, orange, harvest gold and rust, so teal stays in the visualizer whatever
   happens to `accent`. Teal keeps its other four jobs for now.
4. **Components use the roles.** Text on the page uses the tiers instead of
   `text-foreground/xx` (80% and up is plain `foreground`, 55–75% `foreground-dim`, 50% and
   below `foreground-faint`). The library's artist panels and song rows use `surface-raised` and
   `surface-hover`. Glass stays where the art is meant to show through: the stage, performance
   controls, create-session screen and mini player sit over album art, the blurred backdrop or a
   scrim. Glass divider lines stay too, since each theme sets `glass-border`'s color.
