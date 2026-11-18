import React from "react";
import { AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { BeatFrames, evenBeats } from "../beats";
import { Backdrop, Overlay } from "../components/Backdrop";
import { color, font } from "../theme";
import { WAVE } from "./SplitShot";

/**
 * FIND: the proof of "any song". A search types itself, one result comes up,
 * Add is pressed, and while it's "Getting it ready…" the cover breaks into
 * slices that fly into place as the song's waveform: the exact frame SPLIT
 * opens on. Wording from the app's add-song screen.
 */
export const FIND_SHOT_BEATS = 4;

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const snap = Easing.bezier(0.6, 0, 0.15, 1);

const QUERY = "don't blink";
const COVER_HUES: [number, number] = [330, 270];

// The result card, centred; its thumbnail is what breaks into the waveform.
const CARD = { x: 460, y: 400, w: 1000, h: 176 };
const THUMB = { x: CARD.x + 20, y: CARD.y + 20, w: 240, h: 136 };
const SLICES = WAVE.levels.length;

/** Height of waveform bar `i` on SPLIT's first frame (same shimmer formula). */
const barHeight = (i: number) => Math.max(6, WAVE.levels[i] * WAVE.maxH * (1 + Math.sin(i * 0.7) * 0.06));

const SearchField: React.FC<{ typed: number; caret: boolean; out: number }> = ({ typed, caret, out }) => (
  <div
    style={{
      position: "absolute",
      left: CARD.x,
      top: 250,
      width: CARD.w,
      height: 96,
      display: "flex",
      alignItems: "center",
      gap: 22,
      padding: "0 30px",
      background: color.sunk,
      border: `2px solid ${color.magenta}`,
      boxShadow: "0 0 28px rgba(255,42,109,0.35)",
      opacity: 1 - out,
      transform: `translateY(${out * -60}px)`,
    }}
  >
    {/* magnifier */}
    <div style={{ position: "relative", width: 34, height: 34, flexShrink: 0 }}>
      <div style={{ position: "absolute", left: 0, top: 0, width: 24, height: 24, borderRadius: 12, border: `4px solid ${color.dim}` }} />
      <div
        style={{
          position: "absolute",
          left: 21,
          top: 22,
          width: 14,
          height: 4,
          borderRadius: 2,
          background: color.dim,
          transform: "rotate(45deg)",
          transformOrigin: "left center",
        }}
      />
    </div>
    <div style={{ fontFamily: font.body, fontWeight: 500, fontSize: 44, color: typed > 0 ? color.ink : color.faint, display: "flex", alignItems: "center" }}>
      {typed > 0 ? QUERY.slice(0, typed) : "Song or artist"}
      {caret && <span style={{ width: 3, height: 46, background: color.ink, marginLeft: 3 }} />}
    </div>
  </div>
);

export const FindShot: React.FC<{ beats?: BeatFrames }> = ({ beats = evenBeats() }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const B = beats;
  const typeEnd = B[1] + 4;
  const typed = Math.round(interpolate(frame, [1, typeEnd], [0, QUERY.length], clamp));
  const caret = frame < typeEnd + 2 || Math.floor(frame / 7) % 2 === 0;
  const result = spring({ frame: frame - B[1] - 6, fps, config: { damping: 13, stiffness: 220 } });
  const tap = B[2];
  const pressed = frame >= tap;
  const press = interpolate(frame - tap, [0, 3, 8], [1, 0.9, 1], clamp);
  const ripple = interpolate(frame - tap, [0, 14], [0, 1], clamp);
  const morphStart = B[3];
  const morphEnd = B[4] - 2;
  // Everything but the cover clears away as the cover breaks up.
  const out = interpolate(frame, [morphStart, morphStart + 8], [0, 1], { ...clamp, easing: snap });
  const label = frame >= morphStart ? "Getting it ready…" : pressed ? "Adding" : "Add";

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <Backdrop />
      <SearchField typed={typed} caret={caret} out={out} />
      {/* The result card, without its thumbnail (drawn as slices below) */}
      <div
        style={{
          position: "absolute",
          left: CARD.x,
          top: CARD.y,
          width: CARD.w,
          height: CARD.h,
          background: color.panel,
          border: "2px solid rgba(255,255,255,0.08)",
          opacity: (frame >= B[1] + 6 ? result : 0) * (1 - out),
          transform: `translateY(${(1 - result) * 40 + out * 50}px)`,
        }}
      >
        <div style={{ position: "absolute", left: THUMB.w + 48, top: 34 }}>
          <div style={{ fontFamily: font.body, fontWeight: 700, fontSize: 44, color: color.ink, lineHeight: 1.05 }}>Don't Blink</div>
          <div style={{ fontFamily: font.body, fontWeight: 500, fontSize: 30, color: color.dim, marginTop: 6 }}>Dropical · 3:09</div>
        </div>
        <div
          style={{
            position: "absolute",
            right: 28,
            top: (CARD.h - 76) / 2,
            minWidth: 190,
            height: 76,
            padding: "0 28px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 12,
            background: pressed ? "transparent" : color.magenta,
            border: `2px solid ${pressed ? color.faint : color.magenta}`,
            color: pressed ? color.dim : color.void,
            fontFamily: font.body,
            fontWeight: 700,
            fontSize: 34,
            transform: `scale(${press})`,
            overflow: "hidden",
          }}
        >
          {pressed && (
            <span
              style={{
                width: 26,
                height: 26,
                borderRadius: 13,
                border: `4px solid ${color.faint}`,
                borderTopColor: color.ink,
                transform: `rotate(${frame * 24}deg)`,
              }}
            />
          )}
          {label}
          {pressed && ripple < 1 && (
            <span
              style={{
                position: "absolute",
                left: "50%",
                top: "50%",
                width: 160,
                height: 160,
                marginLeft: -80,
                marginTop: -80,
                borderRadius: 80,
                background: "rgba(255,42,109,0.45)",
                transform: `scale(${ripple * 1.6})`,
                opacity: 1 - ripple,
              }}
            />
          )}
        </div>
      </div>
      {/* The cover: whole until the morph, then slices flying into the waveform */}
      {Array.from({ length: SLICES }).map((_, i) => {
        const sliceW = THUMB.w / SLICES;
        const delay = (i / SLICES) * 6;
        const m = interpolate(frame, [morphStart + delay, morphEnd + delay * 0.3], [0, 1], { ...clamp, easing: snap });
        const appear = frame >= B[1] + 6 ? result : 0;
        const h = barHeight(i);
        const fromX = THUMB.x + i * sliceW;
        const fromY = THUMB.y + (1 - appear) * 40;
        const toX = WAVE.left + i * (WAVE.barW + WAVE.gap);
        const toY = WAVE.y - h / 2;
        const x = fromX + (toX - fromX) * m;
        const yy = fromY + (toY - fromY) * m;
        const w = sliceW + 0.6 + (WAVE.barW - sliceW - 0.6) * m;
        const hh = THUMB.h + (h - THUMB.h) * m;
        // Each slice keeps its part of the cover's gradient, warming to the waveform's pink-violet.
        const p = i / SLICES;
        const hue = COVER_HUES[0] + (COVER_HUES[1] - COVER_HUES[0]) * p;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: x,
              top: yy,
              width: w,
              height: hh,
              borderRadius: (WAVE.barW / 2) * m,
              opacity: appear,
              background:
                m < 0.5
                  ? `linear-gradient(to bottom, hsl(${hue} 90% 58%), hsl(${hue - 40} 85% 32%))`
                  : `linear-gradient(to bottom, #d46bff, ${color.violet})`,
              boxShadow: m > 0.6 ? "0 0 10px rgba(139,61,255,0.5)" : "none",
            }}
          />
        );
      })}
      {/* A play glyph on the cover while it's whole */}
      <div
        style={{
          position: "absolute",
          left: THUMB.x + THUMB.w / 2 - 14,
          top: THUMB.y + THUMB.h / 2 - 20,
          width: 0,
          height: 0,
          borderTop: "20px solid transparent",
          borderBottom: "20px solid transparent",
          borderLeft: "32px solid rgba(255,255,255,0.85)",
          opacity: (frame >= B[1] + 6 ? result : 0) * (1 - out),
        }}
      />
      <Overlay />
    </AbsoluteFill>
  );
};
