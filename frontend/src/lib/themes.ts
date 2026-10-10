/**
 * The themes picked in Settings. Each id other than retro needs a matching
 * `[data-theme="<id>"]` block in index.css; retro is `:root`, so it's also
 * what any unknown or missing theme falls back to.
 */
export const THEMES = [{ id: "retro", label: "Retro" }] as const;

export type ThemeName = (typeof THEMES)[number]["id"];

export const DEFAULT_THEME: ThemeName = "retro";

export function isThemeName(value: unknown): value is ThemeName {
  return THEMES.some((theme) => theme.id === value);
}
