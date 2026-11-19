import { loadFont as loadOrbitron } from "@remotion/google-fonts/Orbitron";
import { loadFont as loadRajdhani } from "@remotion/google-fonts/Rajdhani";
import { loadFont as loadShareTechMono } from "@remotion/google-fonts/ShareTechMono";

/** The app's cyberpunk theme (frontend/src/index.css, [data-theme="cyberpunk"]). */
export const color = {
  void: "#07060d",
  sunk: "#0b0918",
  panel: "#17142e",
  raised: "#211d40",
  hover: "#2c2754",
  ink: "#e6f6ff",
  dim: "#b4bde0",
  faint: "#6f7399",
  magenta: "#ff2a6d",
  cyan: "#05d9e8",
  violet: "#7a04eb",
  yellow: "#fcee0a",
  success: "#39ff88",
};

export const font = {
  display: loadOrbitron("normal", { weights: ["700"], subsets: ["latin"] }).fontFamily,
  body: loadRajdhani("normal", { weights: ["500", "700"], subsets: ["latin"] }).fontFamily,
  mono: loadShareTechMono("normal", { weights: ["400"], subsets: ["latin"] }).fontFamily,
};
