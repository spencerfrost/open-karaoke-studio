import React from "react";
import { Easing, interpolate, useCurrentFrame } from "remotion";
import { color } from "../theme";

export interface Point {
  x: number;
  y: number;
}

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

/** Point on the quadratic curve from `a` to `b` bending through `c`. */
const bezier = (a: Point, c: Point, b: Point, t: number): Point => ({
  x: (1 - t) ** 2 * a.x + 2 * (1 - t) * t * c.x + t ** 2 * b.x,
  y: (1 - t) ** 2 * a.y + 2 * (1 - t) * t * c.y + t ** 2 * b.y,
});

interface PulseProps {
  from: Point;
  to: Point;
  start: number;
  duration: number;
  /** How far the arc bows upward, in stage pixels. */
  lift?: number;
}

/**
 * A glowing comet from a phone to the TV: the song "travelling" into the
 * queue. Drawn in stage coordinates, inside the camera group.
 */
export const Pulse: React.FC<PulseProps> = ({ from, to, start, duration, lift = 260 }) => {
  const frame = useCurrentFrame();
  const t = frame - start;
  if (t < 0 || t > duration + 20) return null;

  const p = interpolate(t, [0, duration], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
  const ctrl = { x: (from.x + to.x) / 2, y: Math.min(from.y, to.y) - lift };
  const d = `M ${from.x} ${from.y} Q ${ctrl.x} ${ctrl.y} ${to.x} ${to.y}`;
  const tailStart = Math.max(0, p - 0.4);
  const head = bezier(from, ctrl, to, p);
  const arrived = t >= duration;
  const burst = interpolate(t - duration, [0, 18], [0, 1], clamp);
  const trailFade = interpolate(t - duration, [0, 10], [1, 0], clamp);

  return (
    <svg
      width={1920}
      height={1080}
      style={{ position: "absolute", left: 0, top: 0, overflow: "visible", pointerEvents: "none" }}
    >
      <defs>
        <filter id={`pulse-glow-${start}`} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="8" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <path
        d={d}
        pathLength={1}
        fill="none"
        stroke={color.magenta}
        strokeWidth={6}
        strokeLinecap="round"
        strokeDasharray={`${p - tailStart} 2`}
        strokeDashoffset={-tailStart}
        opacity={trailFade}
        filter={`url(#pulse-glow-${start})`}
      />
      {!arrived && (
        <>
          <circle cx={head.x} cy={head.y} r={18} fill={color.magenta} opacity={0.5} filter={`url(#pulse-glow-${start})`} />
          <circle cx={head.x} cy={head.y} r={8} fill="#fff" />
        </>
      )}
      {arrived && (
        <circle
          cx={to.x}
          cy={to.y}
          r={10 + burst * 70}
          fill="none"
          stroke={color.magenta}
          strokeWidth={4 * (1 - burst) + 1}
          opacity={1 - burst}
        />
      )}
    </svg>
  );
};
