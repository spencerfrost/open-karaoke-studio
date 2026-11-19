import { createContext, useContext } from "react";
import { loadFont as loadJetBrainsMono } from "@remotion/google-fonts/JetBrainsMono";
import { loadFont as loadManrope } from "@remotion/google-fonts/Manrope";
import { loadFont as loadSyne } from "@remotion/google-fonts/Syne";
import { loadFont as loadVT323 } from "@remotion/google-fonts/VT323";
import { color, font } from "./theme";

const syne = loadSyne("normal", { weights: ["700"], subsets: ["latin"] }).fontFamily;
const manrope = loadManrope("normal", { weights: ["400", "600", "700"], subsets: ["latin"] }).fontFamily;
const vt323 = loadVT323("normal", { weights: ["400"], subsets: ["latin"] }).fontFamily;
const jetbrains = loadJetBrainsMono("normal", { weights: ["400", "700"], subsets: ["latin"] }).fontFamily;

/**
 * The app's themes as the video draws them: the tokens from
 * frontend/src/index.css ([data-theme] blocks) that the redrawn screens use.
 */
export interface Theme {
  id: "cyberpunk" | "retro" | "vintage" | "catppuccin";
  label: string;
  /** The page / screen background (CSS background). */
  page: string;
  sunk: string;
  panel: string;
  ink: string;
  dim: string;
  faint: string;
  primary: string;
  /** `primary` as "r,g,b" for glows. */
  primaryRgb: string;
  /** The soft glow colour behind devices, "r,g,b". */
  haloRgb: string;
  display: string;
  body: string;
  mono: string;
  /** VT323 renders small for its size; the app scales it up the same way. */
  monoScale: number;
  radius: number;
  /** How wide the body font runs next to Rajdhani (for line wrapping and tight labels). */
  bodyWidth: number;
  /** Neon text glow (Cyberpunk only). */
  neon: boolean;
  texture: "scanlines" | "grain" | "none";
}

export const CYBERPUNK: Theme = {
  id: "cyberpunk",
  label: "Cyberpunk",
  page: [
    "radial-gradient(ellipse at 20% 100%, rgba(122,4,235,0.35), transparent 55%)",
    "radial-gradient(ellipse at 90% 0%, rgba(255,42,109,0.18), transparent 50%)",
    color.void,
  ].join(", "),
  sunk: color.sunk,
  panel: color.panel,
  ink: color.ink,
  dim: color.dim,
  faint: color.faint,
  primary: color.magenta,
  primaryRgb: "255,42,109",
  haloRgb: "122,4,235",
  display: font.display,
  body: font.body,
  mono: font.mono,
  monoScale: 1,
  radius: 2,
  bodyWidth: 1,
  neon: true,
  texture: "scanlines",
};

export const VINTAGE: Theme = {
  id: "vintage",
  label: "Vintage",
  // --page-bg: russet → rust, with the background mixed half into black.
  page: "radial-gradient(circle at 50% 45%, rgba(253,154,2,0.16), transparent 60%), linear-gradient(135deg, #774320 0%, #b44819 100%)",
  sunk: "rgba(8,7,5,0.35)",
  panel: "#774320",
  ink: "#f5f3c7",
  dim: "rgba(245,243,199,0.68)",
  faint: "rgba(245,243,199,0.45)",
  primary: "#fd9a02",
  primaryRgb: "253,154,2",
  haloRgb: "253,154,2",
  display: syne,
  body: manrope,
  mono: vt323,
  monoScale: 1.4,
  radius: 8,
  bodyWidth: 1.3,
  neon: false,
  texture: "grain",
};

/** Retro: a flat warm near-black page, cream text, orange buttons, no decoration. */
export const RETRO: Theme = {
  id: "retro",
  label: "Retro",
  page: "#121110",
  sunk: "#181614",
  panel: "#1f1d1a",
  ink: "#f5f3c7",
  dim: "rgba(245,243,199,0.7)",
  faint: "rgba(245,243,199,0.45)",
  primary: "#fd9a02",
  primaryRgb: "253,154,2",
  haloRgb: "226,178,74",
  display: syne,
  body: manrope,
  mono: vt323,
  monoScale: 1.4,
  radius: 8,
  bodyWidth: 1.3,
  neon: false,
  texture: "none",
};

export const CATPPUCCIN: Theme = {
  id: "catppuccin",
  label: "Catppuccin",
  page: "#1e1e2e",
  sunk: "#181825",
  panel: "#313244",
  ink: "#cdd6f4",
  dim: "#a6adc8",
  faint: "#7f849c",
  primary: "#cba6f7",
  primaryRgb: "203,166,247",
  haloRgb: "180,190,254",
  display: syne,
  body: manrope,
  mono: jetbrains,
  monoScale: 1,
  radius: 8,
  bodyWidth: 1.3,
  neon: false,
  texture: "none",
};

export const ThemeContext = createContext<Theme>(CYBERPUNK);
export const useTheme = () => useContext(ThemeContext);

/** A text-shadow glow in the theme's primary, or nothing for flat themes. */
export const primaryGlow = (t: Theme, px = 40, alpha = 0.6) =>
  t.neon ? `0 0 ${px}px rgba(${t.primaryRgb},${alpha})` : "none";
