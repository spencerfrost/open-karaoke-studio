import React, { useEffect, useRef } from "react";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";

interface AudioVisualizerProps {
  height?: number;
  barCount?: number;
  className?: string;
}

const AudioVisualizer: React.FC<AudioVisualizerProps> = ({
  height = 120,
  barCount = 120,
  className = "",
}) => {
  const { isReady, isPlaying, error, getWaveformData } =
    useKaraokePlayerStore();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animationRef = useRef<number | null>(null);

  // Animation loop for real waveform data using Canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Set canvas dimensions (accounting for device pixel ratio for sharp rendering)
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    if (isReady && isPlaying && getWaveformData) {
      const animate = () => {
        const waveform = getWaveformData();
        if (waveform && canvas) {
          // Clear canvas
          ctx.clearRect(0, 0, rect.width, rect.height);

          // Downsample waveform data to barCount
          const step = Math.floor(waveform.length / barCount) || 1;
          const bars = Array.from({ length: barCount }, (_, i) => {
            let sum = 0;
            let count = 0;
            for (
              let j = i * step;
              j < (i + 1) * step && j < waveform.length;
              j++
            ) {
              sum += waveform[j];
              count++;
            }
            const avg = count ? sum / count : 128;
            return Math.max(0.1, Math.abs((avg - 128) / 128));
          });

          // Draw bars
          const barWidth = rect.width / barCount;
          const spacing = Math.max(1, barWidth * 0.1); // 10% spacing between bars

          bars.forEach((value, index) => {
            const barHeight = value * rect.height;
            const x = index * barWidth;
            const y = (rect.height - barHeight) / 2;

            // Alternate colors: dark-cyan and orange-peel
            const isEven = index % 2 === 0;
            const baseColor = isEven ? "#01928B" : "#FD9A02";

            // Apply hue rotation effect (simulate CSS hue-rotate)
            const hueShift = (index / barCount) * 60;
            const adjustedColor = adjustColorHue(baseColor, hueShift);

            // Draw bar with opacity
            ctx.globalAlpha = 0.7;
            ctx.fillStyle = adjustedColor;

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
          });

          ctx.globalAlpha = 1.0;
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
      // Draw idle state (minimal bars)
      ctx.clearRect(0, 0, rect.width, rect.height);
      const barWidth = rect.width / barCount;
      const spacing = Math.max(1, barWidth * 0.1);
      const minBarHeight = 0.1 * rect.height;

      for (let i = 0; i < barCount; i++) {
        const x = i * barWidth;
        const y = (rect.height - minBarHeight) / 2;
        const isEven = i % 2 === 0;
        const baseColor = isEven ? "#01928B" : "#FD9A02";
        const hueShift = (i / barCount) * 60;
        const adjustedColor = adjustColorHue(baseColor, hueShift);

        ctx.globalAlpha = 0.7;
        ctx.fillStyle = adjustedColor;

        const actualBarWidth = barWidth - spacing;
        const radius = Math.min(4, actualBarWidth / 2);

        ctx.beginPath();
        ctx.moveTo(x + spacing / 2, y + minBarHeight);
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
        ctx.lineTo(x + actualBarWidth, y + minBarHeight);
        ctx.closePath();
        ctx.fill();
      }

      ctx.globalAlpha = 1.0;

      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
        animationRef.current = null;
      }
    }
  }, [isPlaying, isReady, getWaveformData, barCount, height]);

  if (error) {
    return <div className="text-red-500">Audio error: {error}</div>;
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
