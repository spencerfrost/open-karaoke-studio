/**
 * The themes picked in Settings. Each id needs a matching
 * `[data-theme="<id>"]` block in index.css, and the same list in the boot
 * script in index.html. DEFAULT_THEME is what the app applies when nothing
 * (or nothing valid) is saved.
 */
export const THEMES = [
  { id: "cyberpunk", label: "Cyberpunk" },
  { id: "retro", label: "Retro" },
  { id: "vintage", label: "Vintage" },
  { id: "catppuccin", label: "Catppuccin" },
] as const;

export type ThemeName = (typeof THEMES)[number]["id"];

export const DEFAULT_THEME: ThemeName = "cyberpunk";

export function isThemeName(value: unknown): value is ThemeName {
  return THEMES.some((theme) => theme.id === value);
}
