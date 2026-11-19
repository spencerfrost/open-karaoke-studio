import React from "react";
import { AbsoluteFill, Img, interpolate, random, staticFile, useCurrentFrame } from "remotion";
import { BeatFrames } from "../beats";
import { color } from "../theme";
import { Cover } from "./Devices";

/**
 * What runs behind "ANY SONG." in the open. The type stays the same; these
 * are the options for the layer behind it.
 *
 * The real covers come from the app's library via scripts/pick-covers.sh and
 * stay local (gitignored): the labels own them.
 */
export type OpenBackground =
  /** Rows of made-up gradient covers streaming sideways. */
  | "gradient-wall"
  /** The same rows, real album covers in full colour. */
  | "real-wall"
  /** Real covers tinted magenta to violet so none stands out. */
  | "tint-wall"
  /** Tinted, and on every beat a scatter of covers flashes to full colour. */
  | "pop-wall"
  /** Real covers rushing at the camera from a vanishing point, surging on each beat. */
  | "tunnel"
  /** A still tinted grid; on each beat a ripple from the centre flips the covers to new ones. */
  | "mosaic";

export const REAL_COVER_COUNT = 240; // matches COUNT in scripts/pick-covers.sh

const coverSrc = (i: number) =>
  staticFile(`covers/${String(((i % REAL_COVER_COUNT) + REAL_COVER_COUNT) % REAL_COVER_COUNT).padStart(3, "0")}.jpg`);

/** A seeded cover index. */
const pick = (seed: string) => Math.floor(random(seed) * REAL_COVER_COUNT);

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

/**
 * One real cover. `tint` 1 is a magenta→violet duotone (grey image multiplied
 * by the theme gradient, so blacks stay black); 0 is the cover as it is.
 */
const RealCover: React.FC<{ index: number; size: number; radius?: number; tint?: number; style?: React.CSSProperties }> = ({
  index,
  size,
  radius = 8,
  tint = 0,
  style,
}) => (
  <div
    style={{
      position: "relative",
      width: size,
      height: size,
      flexShrink: 0,
      borderRadius: radius,
      overflow: "hidden",
      boxShadow: "inset 0 0 0 1px rgba(255,255,255,0.12)",
      ...style,
    }}
  >
    <Img
      src={coverSrc(index)}
      style={{
        width: "100%",
        height: "100%",
        display: "block",
        filter: tint > 0 ? `grayscale(${tint}) contrast(${1 + tint * 0.2}) brightness(${1 + tint * 0.15})` : undefined,
      }}
    />
    {tint > 0 && (
      <div
        style={{
          position: "absolute",
          inset: 0,
          opacity: tint,
          mixBlendMode: "multiply",
          background: `linear-gradient(135deg, ${color.magenta}, ${color.violet})`,
        }}
      />
    )}
  </div>
);

/** Rise-and-decay of a flash that starts at `start`, 0 before it. */
const flash = (frame: number, start: number, length = 10) =>
  frame < start ? 0 : interpolate(frame - start, [0, 2, length], [0, 1, 0], clamp);

interface Window {
  /** When "ANY SONG." lands. */
  songIn: number;
  end: number;
}

/** Fades the layer in as "ANY SONG." lands and out at the cut. */
const layerOpacity = (frame: number, T: Window, level: number) =>
  interpolate(frame, [T.songIn - 2, T.songIn + 6, T.end - 4, T.end], [0, level, level, 0], clamp);

/** Rows of covers streaming sideways, alternating direction. */
const Wall: React.FC<{ T: Window; beats: BeatFrames; kind: "gradient" | "real" | "tint" | "pop" }> = ({ T, beats, kind }) => {
  const frame = useCurrentFrame();
  const t = frame - T.songIn;
  if (t < -2) return null;
  // Real covers carry more detail than the gradients, so they sit a touch lower.
  const opacity = layerOpacity(frame, T, kind === "gradient" ? 0.4 : kind === "real" ? 0.34 : 0.5);
  const rows = 6;
  const size = 170;
  const gap = 22;
  const popBeats = beats.filter((b) => b >= T.songIn && b < T.end);
  return (
    <AbsoluteFill style={{ opacity, transform: "rotate(-8deg) scale(1.25)" }}>
      {Array.from({ length: rows }).map((_, r) => {
        const dir = r % 2 === 0 ? -1 : 1;
        const speed = 10 + random(`speed-${r}`) * 6;
        // No wrapping: each row is long enough to run the whole shot (under
        // 1,300 px of travel either way) without its end coming into view.
        const offset = dir * t * speed - 1300;
        return (
          <div
            key={r}
            style={{
              position: "absolute",
              top: -60 + r * (size + gap),
              left: offset,
              display: "flex",
              gap,
            }}
          >
            {Array.from({ length: 28 }).map((__, c) => {
              if (kind === "gradient") {
                // Magenta through violet to orange: the theme's warm half, not a rainbow.
                const h = (250 + Math.floor(random(`h-${r}-${c}`) * 150)) % 360;
                return <Cover key={c} hues={[h, (h + 30 + random(`d-${r}-${c}`) * 40) % 360]} size={size} radius={8} />;
              }
              const index = pick(`wall-${r}-${c}`);
              if (kind === "real") return <RealCover key={c} index={index} size={size} />;
              // A cover joins about one beat in seven, so each beat lights a scatter, not the wall.
              const pop =
                kind === "pop"
                  ? Math.max(0, ...popBeats.map((b, k) => (random(`pop-${r}-${c}-${k}`) < 0.14 ? flash(frame, b, 12) : 0)))
                  : 0;
              return (
                <RealCover
                  key={c}
                  index={index}
                  size={size}
                  tint={1 - pop}
                  style={pop > 0 ? { boxShadow: `0 0 ${pop * 40}px rgba(255,42,109,${pop})`, zIndex: 1 } : undefined}
                />
              );
            })}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

/**
 * Covers fly at the camera from a vanishing point behind the words. Distance
 * travelled is summed frame by frame: a steady cruise plus a surge that kicks
 * on every beat and dies away.
 */
const Tunnel: React.FC<{ T: Window; beats: BeatFrames }> = ({ T, beats }) => {
  const frame = useCurrentFrame();
  const t = frame - T.songIn;
  if (t < -2) return null;
  const surges = beats.filter((b) => b >= T.songIn && b < T.end);
  let travelled = 0;
  for (let f = T.songIn; f <= frame; f++) {
    const surge = surges.reduce((s, b) => s + (f >= b ? Math.exp(-(f - b) / 5) : 0), 0);
    travelled += 0.009 + surge * 0.02;
  }
  const count = 110;
  const covers = Array.from({ length: count }, (_, i) => {
    // Depth 0 is the vanishing point, 1 is at the camera; each cover loops through.
    const z = (random(`z-${i}`) + travelled) % 1;
    const angle = random(`a-${i}`) * Math.PI * 2;
    // Keep a clear lane through the middle for the words.
    const lane = 0.55 + random(`r-${i}`) * 0.9;
    const scale = 1 / (1.05 - z);
    return { i, z, angle, lane, scale };
  }).sort((a, b) => a.z - b.z);
  return (
    <AbsoluteFill style={{ opacity: layerOpacity(frame, T, 0.6) }}>
      {covers.map(({ i, z, angle, lane, scale }) => {
        const size = 70 * scale;
        const x = 960 + Math.cos(angle) * lane * 260 * scale - size / 2;
        const y = 540 + Math.sin(angle) * lane * 170 * scale - size / 2;
        // Faded in out of the dark at the back, gone just before it hits the lens.
        const fade = interpolate(z, [0, 0.25, 0.85, 0.97], [0, 1, 1, 0], clamp);
        return (
          <RealCover
            key={i}
            index={pick(`tunnel-${i}`)}
            size={size}
            radius={6}
            style={{
              position: "absolute",
              left: x,
              top: y,
              opacity: fade,
              filter: `brightness(${0.35 + z * 0.75})`,
              transform: `rotate(${(random(`rot-${i}`) - 0.5) * 20}deg)`,
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};

/**
 * A still grid of tinted covers. On each beat a ring spreads from the centre;
 * each cover flips over as it passes, showing a new cover in full colour for a
 * moment before the tint settles back.
 */
const Mosaic: React.FC<{ T: Window; beats: BeatFrames }> = ({ T, beats }) => {
  const frame = useCurrentFrame();
  if (frame < T.songIn - 2) return null;
  const waves = beats.filter((b) => b >= T.songIn && b < T.end);
  const size = 150;
  const gap = 18;
  const cols = 16;
  const rows = 11;
  // A beat is about 18 frames: the ring crosses the grid and every flip lands in ~12, then it holds still.
  const flipFrames = 6;
  return (
    <AbsoluteFill style={{ opacity: layerOpacity(frame, T, 0.5), transform: "rotate(-8deg) scale(1.2)" }}>
      <div
        style={{
          position: "absolute",
          left: 960 - (cols * (size + gap)) / 2,
          top: 540 - (rows * (size + gap)) / 2,
          display: "grid",
          gridTemplateColumns: `repeat(${cols}, ${size}px)`,
          gap,
        }}
      >
        {Array.from({ length: rows * cols }).map((_, n) => {
          const r = Math.floor(n / cols);
          const c = n % cols;
          const dist = Math.hypot(c - (cols - 1) / 2, (r - (rows - 1) / 2) * 1.2);
          // The ring reaches this cover 0.6 frames per unit of distance after the beat.
          const passes = waves.map((b) => b + Math.round(dist * 0.6));
          const done = passes.filter((p) => frame >= p + flipFrames / 2).length;
          const current = passes.filter((p) => frame >= p).pop();
          const turn = current === undefined ? 0 : interpolate(frame, [current, current + flipFrames], [0, 1], clamp);
          // 0→90° shows the old cover's back half, 90→180° the new one coming round.
          const angle = turn < 0.5 ? turn * 180 : turn * 180 - 180;
          const colour = current === undefined ? 0 : interpolate(frame - current, [flipFrames / 2, flipFrames, 16], [1, 1, 0], clamp);
          return (
            <RealCover
              key={n}
              index={pick(`mosaic-${n}-${done}`)}
              size={size}
              tint={1 - colour}
              style={{ transform: `perspective(700px) rotateY(${angle}deg)` }}
            />
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

export const OpenBackgroundLayer: React.FC<{ kind: OpenBackground; T: Window; beats: BeatFrames }> = ({ kind, T, beats }) => {
  switch (kind) {
    case "gradient-wall":
      return <Wall T={T} beats={beats} kind="gradient" />;
    case "real-wall":
      return <Wall T={T} beats={beats} kind="real" />;
    case "tint-wall":
      return <Wall T={T} beats={beats} kind="tint" />;
    case "pop-wall":
      return <Wall T={T} beats={beats} kind="pop" />;
    case "tunnel":
      return <Tunnel T={T} beats={beats} />;
    case "mosaic":
      return <Mosaic T={T} beats={beats} />;
  }
};

export const OPEN_BACKGROUNDS: OpenBackground[] = ["gradient-wall", "real-wall", "tint-wall", "pop-wall", "tunnel", "mosaic"];
