import React from "react";
import { AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { BeatFrames, evenBeats } from "../beats";
import { Backdrop, Overlay } from "../components/Backdrop";
import { color, font } from "../theme";

/**
 * The end card: bunny, name, what it is, where to try it, where to get it. Shot length in
 * beats; the last ones let the song fade out under the card.
 */
export const CLOSE_SHOT_BEATS = 10;

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

const PILLS = ["OPEN SOURCE", "SELF-HOSTED", "FREE"];

export const CloseShot: React.FC<{ beats?: BeatFrames }> = ({ beats = evenBeats() }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const fadeIn = interpolate(frame, [0, 3], [0, 1], clamp);
  const bunny = spring({ frame: frame - beats[0], fps, config: { damping: 10, stiffness: 150 } });
  const word = spring({ frame: frame - beats[1], fps, config: { damping: 14 } });
  const link = spring({ frame: frame - beats[5], fps, config: { damping: 16 } });
  const repo = spring({ frame: frame - beats[6], fps, config: { damping: 16 } });
  const bob = Math.sin(frame / 14) * 4;

  return (
    <AbsoluteFill style={{ opacity: fadeIn }}>
      <Backdrop />
      <AbsoluteFill
        style={{ background: "radial-gradient(ellipse at 50% 45%, rgba(255,42,109,0.18), transparent 55%)" }}
      />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <Img
          src={staticFile("bunny.png")}
          style={{
            width: 300,
            height: 300,
            transform: `translateY(${bob}px) scale(${bunny})`,
            filter: "drop-shadow(0 0 40px rgba(255,42,109,0.35))",
          }}
        />
        <div
          style={{
            marginTop: 10,
            fontFamily: font.display,
            fontSize: 84,
            color: color.magenta,
            textShadow: "0 0 40px rgba(255,42,109,0.6)",
            letterSpacing: 2,
            opacity: word,
            transform: `translateY(${(1 - word) * 30}px)`,
          }}
        >
          OPEN KARAOKE STUDIO
        </div>
        <div style={{ display: "flex", gap: 18, marginTop: 26 }}>
          {PILLS.map((p, i) => {
            const s = spring({ frame: frame - beats[2 + i], fps, config: { damping: 12, stiffness: 180 } });
            return (
              <div
                key={p}
                style={{
                  padding: "10px 22px",
                  border: `2px solid ${color.magenta}`,
                  background: color.sunk,
                  fontFamily: font.mono,
                  fontSize: 30,
                  letterSpacing: 3,
                  color: color.ink,
                  opacity: s,
                  transform: `scale(${1.3 - s * 0.3})`,
                }}
              >
                {p}
              </div>
            );
          })}
        </div>
        <div
          style={{
            marginTop: 40,
            fontFamily: font.body,
            fontWeight: 700,
            fontSize: 44,
            color: color.cyan,
            textShadow: "0 0 24px rgba(5,217,232,0.5)",
            letterSpacing: 1,
            opacity: link,
            transform: `translateY(${(1 - link) * 20}px)`,
          }}
        >
          karaoke.mrspinn.ca
        </div>
        <div
          style={{
            marginTop: 10,
            fontFamily: font.body,
            fontWeight: 500,
            fontSize: 32,
            color: color.dim,
            opacity: repo,
            transform: `translateY(${(1 - repo) * 20}px)`,
          }}
        >
          github.com/spencerfrost/open-karaoke-studio
        </div>
      </AbsoluteFill>
      <Overlay />
    </AbsoluteFill>
  );
};
