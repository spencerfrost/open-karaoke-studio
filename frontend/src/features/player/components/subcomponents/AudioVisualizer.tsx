import React, { useCallback, useEffect, useMemo, useRef } from "react";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";

interface AudioVisualizerProps {
  height?: number;
  barCount?: number;
  className?: string;
}

// dark-cyan, orange-peel — alternated per bar, then hue-shifted across the row
const BASE_COLORS = ["#01928B", "#FD9A02"];

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
  const barsRef = useRef<Float32Array>(new Float32Array(0));

  // Colors depend only on bar index, not on audio data — compute them once
  // per barCount instead of re-running the hue math for every bar, every frame.
  const barColors = useMemo(
    () =>
      Array.from({ length: barCount }, (_, i) =>
        adjustColorHue(BASE_COLORS[i % 2], (i / barCount) * 60),
      ),
    [barCount],
  );

  useEffect(() => {
    if (barsRef.current.length !== barCount) {
      barsRef.current = new Float32Array(barCount);
    }
  }, [barCount]);

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

    const drawBars = (valueAt: (index: number) => number) => {
      const { width, height: canvasHeight } = sizeRef.current;
      if (!width || !canvasHeight) return;

      ctx.clearRect(0, 0, width, canvasHeight);

      const barWidth = width / barCount;
      const spacing = Math.max(1, barWidth * 0.1); // 10% spacing between bars

      for (let i = 0; i < barCount; i++) {
        const barHeight = valueAt(i) * canvasHeight;
        const x = i * barWidth;
        const y = (canvasHeight - barHeight) / 2;

        ctx.globalAlpha = 0.7;
        ctx.fillStyle = barColors[i];

        // Rounded top effect using arc
        const actualBarWidth = barWidth - spacing;
        const radius = Math.min(4, actualBarWidth / 2);

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

      ctx.globalAlpha = 1.0;
    };

    if (isReady && isPlaying && getFrequencyData) {
      const animate = () => {
        const frequencies = getFrequencyData();
        const bars = barsRef.current;

        if (frequencies && bars.length === barCount) {
          // Downsample frequency bins to barCount
          const step = Math.floor(frequencies.length / barCount) || 1;
          for (let i = 0; i < barCount; i++) {
            let sum = 0;
            let count = 0;
            for (
              let j = i * step;
              j < (i + 1) * step && j < frequencies.length;
              j++
            ) {
              sum += frequencies[j];
              count++;
            }
            const avg = count ? sum / count : 0;
            // getByteFrequencyData is already 0-255 magnitude, no midpoint
            // to subtract — just normalize, with a small floor so quiet
            // bars don't fully vanish.
            bars[i] = Math.max(0.04, avg / 255);
          }
          drawBars((i) => bars[i]);
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
      drawBars(() => 0.1);

      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
        animationRef.current = null;
      }
    }
  }, [isPlaying, isReady, getFrequencyData, barCount, barColors]);

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
