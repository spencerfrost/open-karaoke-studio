# Theme Token Migration & Theme Presets

## Context

Goal: user-selectable theme presets ("cyberpunk", "pastel/catppuccin", "legacy", "arcade", …) and eventually custom user palettes. The current vintage theme (russet/rust gradient, orange-peel, lemon-chiffon) is **not** the long-term default — it becomes the "legacy" preset. The likely future default is a dark theme with neon/glow accents.

The blocker is that component styling is inconsistent: most elements are individually styled with raw palette colors at various transparencies. The target state is that **no component references a color by name — only by role** — so a theme is just a block of CSS variables.

### Current state (audited 2026-07-19)

[index.css](../../frontend/src/index.css) already defines the shadcn semantic tokens (`--background`, `--primary`, `--card`, …) mapped to the vintage palette via Tailwind v4 `@theme inline`. But the token layer is dishonest: `--background` is lemon-chiffon and `--foreground` is black, while the actual page is a dark russet→rust gradient painted onto `body`. Four styling dialects coexist as a result:

1. **Correct semantic usage** — mostly in `components/ui/` primitives (`text-muted-foreground` alone has 247 uses). Healthy; needs no edits.
2. **Inverted semantic usage** — ~60 instances of `text-background(/xx)` meaning "light text on the dark page" (e.g. [NavBar.tsx:38](../../frontend/src/components/layout/NavBar.tsx#L38)).
3. **Raw palette classes** — ~400 instances across ~51 files: `text-orange-peel` (51×), `border-orange-peel` (26×), `text-lemon-chiffon` (21×), `bg-russet`, and transparency variants (`bg-orange-peel/20`, `text-lemon-chiffon/60`, …). These exist because `@theme` exposes the raw palette as utilities.
4. **Untokenized ad-hoc colors** — the glass/overlay dialect (`bg-white/10`, `border-white/20`, `bg-black/40`–`/80`, ~80 instances); stock Tailwind status colors (`bg-yellow-500`, `bg-blue-500` in [ProcessingIndicator.tsx](../../frontend/src/features/songs/components/song-card/ProcessingIndicator.tsx)); hardcoded hex in [AudioVisualizer.tsx](../../frontend/src/features/player/components/subcomponents/AudioVisualizer.tsx) and [QRCodeDisplay.tsx](../../frontend/src/features/queue/components/QRCodeDisplay.tsx); palette hexes baked into the sunburst pattern in index.css (which references a `theme.ts` that no longer exists).

**Gotcha:** index.css remaps `--color-white` to lemon-chiffon, so today's `text-white` (26×) and `bg-white/*` (~40×) are secretly cream-tinted. When tokenized, legacy keeps the cream tint and other themes get true white — the correct outcome, but expect it during review.

### Why Tailwind v4 makes this work

- `@theme inline` references live CSS variables, so swapping `:root`/`[data-theme]` variables rethemes everything instantly, no rebuild.
- v4 opacity modifiers (`bg-primary/20`) work on var-based colors via `color-mix`, so the existing transparency habit survives tokenization.
- `--font-*` and `--shadow-*` are first-class theme namespaces, so fonts and glows can be tokens too.

### Ground rule

Stages 1–4 are **pixel-identical refactors** against the current (legacy) look. Pixel-identical is the only kind of refactor verifiable screen-by-screen without design judgment on every PR. Do **not** design the new default theme mid-migration — once the app is token-driven, building the neon theme is an afternoon in one CSS file.

## Token vocabulary

Roles, not colors. Everything shadcn-compatible keeps its name so `components/ui/` primitives need zero edits. Legacy values shown to ground it:

| Role | Meaning | Legacy value |
|---|---|---|
| `background` / `foreground` | The page itself + text sitting directly on it | dark russet base / lemon-chiffon |
| `card` / `card-foreground` | Raised opaque surface | lemon-chiffon / near-black |
| `popover`, `input`, `border`, `ring` | shadcn standard, unchanged | as today |
| `primary` / `primary-foreground` | Brand/action color | orange-peel / lemon-chiffon |
| `secondary` | Second-tier emphasis | rust |
| `accent` | Highlights, active states | dark-cyan |
| `muted` / `muted-foreground` | De-emphasized surface/text | pale beige / softened black |
| `glass` / `glass-border` | Translucent panels on the page bg | white/10, white/20 |
| `overlay` | Scrims behind modals/covers (used with `/40`–`/80`) | black |
| `success`, `warning`, `info`, `destructive` | Status colors | replaces stock yellow-500 etc. |
| `glow-primary`, `glow-accent` | Shadow/glow effect tokens | `none`/subtle (neon themes light up) |
| `page-bg` | Full body `background` value (gradient or flat) | the russet→rust gradient |
| `font-display`, `font-body`, `font-accent` | Typography | Syne / Manrope / VT323 |

Notes:

- `page-bg` holds the *entire* background value so themes can choose gradient vs. flat without extra tokens.
- Decorative pattern utilities (`.vintage-sunburst-pattern`, `.vintage-texture-overlay`) are legacy's personality, not the app's — scope them under `[data-theme="legacy"]`. Each theme owns its own flair.
- Glows must be tokens from day one; per-component `shadow-[0_0_12px_…]` is the same disease being cured. The existing `.text-shadow` utility (hardcoded warm glow) is the first customer.

## Stages

### Stage 1 — Make the token layer honest (one PR, zero visual change)

- Restructure [index.css](../../frontend/src/index.css) around the vocabulary above, with legacy as the reference theme: flip `--background`/`--foreground` to describe reality; keep `--card` as the cream surface.
- Add the missing tokens: `glass`, `glass-border`, `overlay`, `success`/`warning`/`info`, `glow-*`, `page-bg`, `font-*`.
- Mechanically rewrite the ~60 `text-background(/xx)` → `text-foreground(/xx)` uses in the same PR (they break the moment the flip lands).
- `body` uses `background: var(--page-bg)`.

This is the keystone PR — small, and everything after it is mechanical.

### Stage 2 — Tokenize the ad-hoc dialects (~15–20 files, grep-driven)

- `bg-white/10` → `bg-glass`, `border-white/20` → `border-glass-border`, `bg-black/60` → `bg-overlay/60`, etc.
- Stock status colors (`bg-yellow-500`, `bg-blue-500`, `bg-red-500`, `bg-gray-*`) → `warning`/`info`/`destructive`/`muted`.
- Add the ESLint guardrail now: `no-restricted-syntax` in [eslint.config.js](../../frontend/eslint.config.js) banning raw palette class names (`orange-peel|lemon-chiffon|rust|russet|dark-cyan`), `text-background`, and `bg-white|bg-black` in `className`, so new code can't regress while Stage 3 is in flight.

### Stage 3 — Retire raw palette classes, screen by screen (~51 files)

- `text-orange-peel` → `text-primary`, `text-lemon-chiffon` → `text-foreground`, `bg-russet` → the appropriate surface token, etc. Mapping is usually obvious per-site; when it isn't, that's a real design decision worth a moment of thought.
- One feature per PR, verified by eyeballing the screen. Suggested order: layout + queue first (small, proves the pattern), player last (biggest).
- **Enforcement endgame:** when the last usage dies, delete `--color-orange-peel` and friends from `@theme` — the utilities stop compiling, so regression becomes impossible.

### Stage 4 — Runtime and CSS stragglers

- [AudioVisualizer.tsx](../../frontend/src/features/player/components/subcomponents/AudioVisualizer.tsx) and [QRCodeDisplay.tsx](../../frontend/src/features/queue/components/QRCodeDisplay.tsx) read colors via `getComputedStyle(document.documentElement).getPropertyValue("--primary")` instead of hardcoded hex.
- Rebuild sunburst/texture patterns from tokens with `color-mix` so decorations retheme (or stay legacy-scoped, per the vocabulary notes).
- Scrollbar colors in index.css → tokens.

### Stage 5 — The theming feature itself

By now it's small:

- Presets are named CSS-variable blocks: `:root` holds the default theme, `[data-theme="legacy"]` etc. override.
- A small ThemeProvider sets `data-theme` on `<html>` and persists the choice (localStorage; per-user backend later if wanted).
- Custom user palettes = an injected `<style>` with variable overrides on top of a base preset.
- Fonts: currently Google-hosted `@import`s. Themeable fonts mean self-hosting the font files — decide then whether presets share a font set or each ships its own.
- Design the new default (dark + neon) theme here, as pure CSS, with zero component changes.

## Effort estimate

Stages 1–2 are a weekend and immediately stop the bleeding — every new component from then on has honest tokens to reach for. Stage 3 is the long tail but is parallelizable and verifiable per-screen. Stages 4–5 are small.
