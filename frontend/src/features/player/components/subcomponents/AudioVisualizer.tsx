import React, { useCallback, useEffect, useMemo, useRef } from "react";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";

interface AudioVisualizerProps {
  height?: number;
  barCount?: number;
  className?: string;
}

// dark-cyan, orange-peel — alternated per bar, then hue-shifted across the row
const BASE_COLORS = ["#01928B", "#FD9A02"];

// Auto-leveling: each band scales against its own recently-seen peak rather
// than a fixed 0-255 ceiling, so quiet songs and quiet frequency ranges
// still show real movement instead of sitting near-silent while loud ones
// peg the top. MIN_PEAK stops near-silence from getting amplified into
// visual noise; PEAK_DECAY is how fast the ceiling relaxes back down once
// the audio quiets, so a loud chorus doesn't flatten the following verse.
// Sustained content (bass especially) sits close to its own peak almost
// continuously, so RESPONSE_CURVE punishes anything short of the peak much
// harder than a straight ratio would — "close to peak" should look
// noticeably short, not nearly full, or nothing ever looks like it's moving.
const MIN_PEAK = 24;
// 0.9 decayed the peak ~10%/frame — at 60fps that collapses the "recent
// peak" down to the current value within a couple frames, so avg/peak was
// pinned at ~1 almost constantly (hence maxing out regardless of the curve
// below). This needs a multi-second memory to mean anything.
const PEAK_DECAY = 0.995;
const RESPONSE_CURVE = 4.5;

const AudioVisualizer: React.FC<AudioVisualizerProps> = ({
  height = 120,
  barCount = 120,
  className = "",
}) => {
  const { isReady, isPlaying, error, getFrequencyData } =
    useKaraokePlayerStore();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animationRef = useRef<number | null>(null);
  const sizeRef = useRef({ width: 0, height: 0 });
  // One value per half — the other half is drawn as its mirror, bass-out.
  const halfCount = useMemo(
    () => Math.max(1, Math.round(barCount / 2)),
    [barCount],
  );
  const barsRef = useRef<Float32Array>(new Float32Array(0));
  const peaksRef = useRef<Float32Array>(new Float32Array(0));
  const binPositionsRef = useRef<{
    binCount: number;
    halfCount: number;
    positions: number[];
  } | null>(null);

  // Colors depend only on distance from center, not on audio data — compute
  // them once per halfCount instead of re-running the hue math for every
  // bar, every frame. Both mirrored bars at a given distance share a color.
  const barColors = useMemo(
    () =>
      Array.from({ length: halfCount }, (_, k) =>
        adjustColorHue(BASE_COLORS[k % 2], (k / halfCount) * 60),
      ),
    [halfCount],
  );

  useEffect(() => {
    if (barsRef.current.length !== halfCount) {
      barsRef.current = new Float32Array(halfCount);
    }
    if (peaksRef.current.length !== halfCount) {
      peaksRef.current = new Float32Array(halfCount).fill(MIN_PEAK);
    }
  }, [halfCount]);

  // Frequency bins are linearly spaced, but music's energy is not — bass
  // dominates the first few bins while everything above it trails off, so a
  // linear bar mapping looks lively on one end and dead on the other. Log-
  // spaced sampling gives bass, mids and highs roughly equal visual width.
  //
  // There are only ~128 usable bins, so several consecutive low buckets land
  // on the exact same integer bin if we round to one — that read as chunky,
  // stair-stepped groups of identical bars. Sampling a fractional position
  // and interpolating between its two neighboring bins keeps every bucket
  // distinct, since the interpolation weight still moves smoothly from one
  // bucket to the next even while the underlying bin stays the same.
  const getBinPositions = useCallback(
    (binCount: number): number[] => {
      const cached = binPositionsRef.current;
      if (
        cached &&
        cached.binCount === binCount &&
        cached.halfCount === halfCount
      ) {
        return cached.positions;
      }
      const minBin = 1; // skip the DC bin
      const maxBin = Math.max(minBin + 1, binCount - 1);
      const denom = Math.max(1, halfCount - 1);
      const positions = Array.from(
        { length: halfCount },
        (_, k) => minBin * Math.pow(maxBin / minBin, k / denom),
      );
      binPositionsRef.current = { binCount, halfCount, positions };
      return positions;
    },
    [halfCount],
  );

  // Sets the canvas's backing bitmap to match its current on-screen size.
  // Uses setTransform (absolute) rather than scale (cumulative) so it's safe
  // to call again on every resize without compounding the DPR scale.
  const resizeCanvas = useCallback((canvas: HTMLCanvasElement) => {
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return;
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    canvas.getContext("2d")?.setTransform(dpr, 0, 0, dpr, 0, 0);
    sizeRef.current = { width: rect.width, height: rect.height };
  }, []);

  // Keeps the bitmap in sync with layout changes — e.g. toggling fullscreen,
  // or the stage rails collapsing/expanding around this bar.
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    resizeCanvas(canvas);
    const observer = new ResizeObserver(() => resizeCanvas(canvas));
    observer.observe(canvas);
    return () => observer.disconnect();
  }, [resizeCanvas]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Draws one bar per distance-from-center k, mirrored to both halves —
    // k = 0 (bass) sits at the two center-most bars, k = halfCount - 1
    // (treble) sits at the two outer edges.
    const drawMirroredBars = (valueAt: (k: number) => number) => {
      const { width, height: canvasHeight } = sizeRef.current;
      if (!width || !canvasHeight) return;

      ctx.clearRect(0, 0, width, canvasHeight);

      const totalBars = halfCount * 2;
      const barWidth = width / totalBars;
      const spacing = Math.max(1, barWidth * 0.1); // 10% spacing between bars
      const actualBarWidth = barWidth - spacing;
      const radius = Math.min(4, actualBarWidth / 2);

      for (let k = 0; k < halfCount; k++) {
        const barHeight = valueAt(k) * canvasHeight;
        const y = (canvasHeight - barHeight) / 2;

        ctx.globalAlpha = 0.7;
        ctx.fillStyle = barColors[k];

        for (const barIndex of [halfCount - 1 - k, halfCount + k]) {
          const x = barIndex * barWidth;
          ctx.beginPath();
          ctx.moveTo(x + spacing / 2, y + barHeight);
          ctx.lineTo(x + spacing / 2, y + radius);
          ctx.arc(
            x + spacing / 2 + radius,
            y + radius,
            radius,
            Math.PI,
            1.5 * Math.PI,
          );
          ctx.lineTo(x + actualBarWidth - radius, y);
          ctx.arc(
            x + actualBarWidth - radius,
            y + radius,
            radius,
            1.5 * Math.PI,
            0,
          );
          ctx.lineTo(x + actualBarWidth, y + barHeight);
          ctx.closePath();
          ctx.fill();
        }
      }

      ctx.globalAlpha = 1.0;
    };

    if (isReady && isPlaying && getFrequencyData) {
      const animate = () => {
        const frequencies = getFrequencyData();
        const bars = barsRef.current;
        const peaks = peaksRef.current;

        if (frequencies && bars.length === halfCount) {
          const positions = getBinPositions(frequencies.length);
          for (let k = 0; k < halfCount; k++) {
            const pos = positions[k];
            const i0 = Math.floor(pos);
            const i1 = Math.min(i0 + 1, frequencies.length - 1);
            const frac = pos - i0;
            const avg = frequencies[i0] * (1 - frac) + frequencies[i1] * frac;
            // Auto-level against this band's own recent peak (decaying
            // slowly so it doesn't pump) instead of a fixed 0-255 ceiling,
            // so both quiet songs and quiet bands still show real movement.
            const peak = Math.max(avg, peaks[k] * PEAK_DECAY, MIN_PEAK);
            peaks[k] = peak;
            const level = Math.pow(Math.min(1, avg / peak), RESPONSE_CURVE);
            bars[k] = Math.max(0.04, level);
          }
          drawMirroredBars((k) => bars[k]);
        }

        animationRef.current = requestAnimationFrame(animate);
      };
      animate();

      return () => {
        if (animationRef.current) {
          cancelAnimationFrame(animationRef.current);
        }
      };
    } else {
      // Idle state: minimal flat bars
      drawMirroredBars(() => 0.1);

      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
        animationRef.current = null;
      }
    }
  }, [
    isPlaying,
    isReady,
    getFrequencyData,
    halfCount,
    barColors,
    getBinPositions,
  ]);

  if (error) {
    return <div className="text-destructive">Audio error: {error}</div>;
  }

  return (
    <canvas
      ref={canvasRef}
      className={`w-full ${className}`}
      style={{ height: `${height}px` }}
    />
  );
};

// Helper function to simulate CSS hue-rotate filter
function adjustColorHue(hexColor: string, hueShift: number): string {
  // Convert hex to RGB
  const r = parseInt(hexColor.slice(1, 3), 16) / 255;
  const g = parseInt(hexColor.slice(3, 5), 16) / 255;
  const b = parseInt(hexColor.slice(5, 7), 16) / 255;

  // Convert RGB to HSL
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;
  let h = 0;
  let s = 0;

  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);

    switch (max) {
      case r:
        h = ((g - b) / d + (g < b ? 6 : 0)) / 6;
        break;
      case g:
        h = ((b - r) / d + 2) / 6;
        break;
      case b:
        h = ((r - g) / d + 4) / 6;
        break;
    }
  }

  // Apply hue shift (convert degrees to 0-1 range)
  h = (h + hueShift / 360) % 1;

  // Convert HSL back to RGB
  const hue2rgb = (p: number, q: number, t: number) => {
    if (t < 0) t += 1;
    if (t > 1) t -= 1;
    if (t < 1 / 6) return p + (q - p) * 6 * t;
    if (t < 1 / 2) return q;
    if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
    return p;
  };

  let nr, ng, nb;
  if (s === 0) {
    nr = ng = nb = l;
  } else {
    const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    const p = 2 * l - q;
    nr = hue2rgb(p, q, h + 1 / 3);
    ng = hue2rgb(p, q, h);
    nb = hue2rgb(p, q, h - 1 / 3);
  }

  // Convert back to hex
  const toHex = (x: number) =>
    Math.round(x * 255)
      .toString(16)
      .padStart(2, "0");
  return `#${toHex(nr)}${toHex(ng)}${toHex(nb)}`;
}

export default React.memo(AudioVisualizer);
