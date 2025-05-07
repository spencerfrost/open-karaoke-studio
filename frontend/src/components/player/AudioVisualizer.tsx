import React, { useEffect, useRef, useState } from "react";
import { useWebAudioKaraokeStore } from "@/stores/useWebAudioKaraokeStore";
import vintageTheme from "../../utils/theme";

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
  const isPlaying = useWebAudioKaraokeStore((s) => s.isPlaying);
  const isReady = useWebAudioKaraokeStore((s) => s.isReady);
  const getWaveformData = useWebAudioKaraokeStore((s) => s.getWaveformData);
  const error = useWebAudioKaraokeStore((s) => s.error);
  const [audioData, setAudioData] = useState<number[]>([]);
  const animationRef = useRef<number | null>(null);
  const colors = vintageTheme.colors;

  // Animation loop for real waveform data
  useEffect(() => {
    if (isReady && isPlaying && getWaveformData) {
      const animate = () => {
        const waveform = getWaveformData();
        if (waveform) {
          // Downsample or interpolate to barCount
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
          setAudioData(bars);
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
      setAudioData(Array(barCount).fill(0.1));
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
        animationRef.current = null;
      }
    }
  }, [isPlaying, isReady, getWaveformData, barCount]);

  if (error) {
    return <div className="text-red-500">Audio error: {error}</div>;
  }
  if (!audioData.length) {
    return null;
  }

  return (
    <div
      className={`w-full flex items-center justify-center space-x-1 ${className}`}
      style={{ height: `${height}px` }}
    >
      {audioData.map((value, index) => {
        const barHeight = value * height;
        const hueRotation = (index / barCount) * 60;
        return (
          <div
            key={index}
            className="w-2 rounded-t"
            style={{
              height: `${barHeight}px`,
              backgroundColor:
                index % 2 === 0 ? colors.darkCyan : colors.orangePeel,
              opacity: 0.7,
              transform: `translateY(${(height - barHeight) / 2}px)`,
              transition: isPlaying ? "none" : "height 0.5s",
              filter: `hue-rotate(${hueRotation}deg)`,
            }}
          />
        );
      })}
    </div>
  );
};

export default AudioVisualizer;
