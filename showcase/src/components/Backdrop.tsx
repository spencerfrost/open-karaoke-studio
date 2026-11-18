import React from "react";
import { AbsoluteFill } from "remotion";
import { useTheme } from "../themes";

/** The page behind every shot, in the current theme. */
export const Backdrop: React.FC = () => {
  const theme = useTheme();
  return (
    <AbsoluteFill style={{ background: theme.page }}>
      {theme.id === "cyberpunk" && (
        <AbsoluteFill
          style={{
            opacity: 0.18,
            background:
              "linear-gradient(rgba(122,4,235,0.6) 1px, transparent 1px) 0 0 / 64px 64px, linear-gradient(90deg, rgba(122,4,235,0.6) 1px, transparent 1px) 0 0 / 64px 64px",
            maskImage: "radial-gradient(ellipse at center, black 20%, transparent 75%)",
          }}
        />
      )}
      {theme.id === "retro" && (
        // Retro's faint sunburst (.theme-pattern)
        <AbsoluteFill
          style={{
            opacity: 0.5,
            background:
              "repeating-conic-gradient(from 0deg at 50% 60%, rgba(8,7,5,0.18) 0deg 6deg, transparent 6deg 12deg)",
            maskImage: "radial-gradient(circle at 50% 60%, black 10%, transparent 70%)",
          }}
        />
      )}
    </AbsoluteFill>
  );
};

/** The theme's texture and a vignette over every shot. */
export const Overlay: React.FC = () => {
  const theme = useTheme();
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {theme.texture === "scanlines" && (
        <AbsoluteFill
          style={{
            backgroundImage: "repeating-linear-gradient(to bottom, rgba(255,255,255,0.025) 0 1px, transparent 1px 3px)",
          }}
        />
      )}
      {theme.texture === "grain" && (
        // Retro's pixel-grain texture (.theme-texture), scaled up for 1080p
        <AbsoluteFill
          style={{
            backgroundImage:
              "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='4' height='4' viewBox='0 0 4 4'%3E%3Cpath fill='%23ffffff' fill-opacity='0.06' d='M1 3h1v1H1V3zm2-2h1v1H3V1z'%3E%3C/path%3E%3C/svg%3E\")",
            backgroundSize: "8px 8px",
          }}
        />
      )}
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,0.5))" }} />
    </AbsoluteFill>
  );
};
