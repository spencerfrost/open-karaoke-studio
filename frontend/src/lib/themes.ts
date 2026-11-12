/**
 * The themes picked in Settings. Each id other than retro needs a matching
 * `[data-theme="<id>"]` block in index.css; retro is `:root`, so it's what an
 * unknown data-theme value paints. DEFAULT_THEME is what the app applies when
 * nothing (or nothing valid) is saved.
 */
export const THEMES = [
  { id: "retro", label: "Retro" },
  { id: "cyberpunk", label: "Cyberpunk" },
  { id: "catppuccin", label: "Catppuccin" },
] as const;

export type ThemeName = (typeof THEMES)[number]["id"];

export const DEFAULT_THEME: ThemeName = "cyberpunk";

export function isThemeName(value: unknown): value is ThemeName {
  return THEMES.some((theme) => theme.id === value);
}
