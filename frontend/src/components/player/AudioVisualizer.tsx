import React, { useEffect, useRef, useState } from "react";
import { usePlayer } from "../../context/PlayerContext";
import vintageTheme from "../../utils/theme";

interface AudioVisualizerProps {
  height?: number;
  barCount?: number;
  className?: string;
}

const AudioVisualizer: React.FC<AudioVisualizerProps> = ({
  height = 120,
  barCount = 32,
  className = "",
}) => {
  const { state: playerState } = usePlayer();
  const [audioData, setAudioData] = useState<number[]>([]);
  const animationRef = useRef<number | null>(null);
  const colors = vintageTheme.colors;

  // Generate random audio data for visual effect
  // In a real implementation, this would use Web Audio API to analyze actual audio
  useEffect(() => {
    if (playerState.status === "playing") {
      const generateData = () => {
        const newData = Array.from({ length: barCount }, (_, i) => {
          // Create a pseudo-random yet somewhat consistent pattern based on time and position
          const offset = Math.sin((Date.now() + i * 100) / 500) * 0.3;
          const baseHeight = 0.2 + ((Math.sin(i * 0.2) + 1) / 2) * 0.6; // 0.2 to 0.8
          return Math.max(0.1, Math.min(1, baseHeight + offset));
        });

        setAudioData(newData);
        animationRef.current = requestAnimationFrame(generateData);
      };

      generateData();

      return () => {
        if (animationRef.current) {
          cancelAnimationFrame(animationRef.current);
        }
      };
    } else {
      // When not playing, either show flat line or gentle wave
      if (playerState.status === "paused") {
        const pausedData = Array.from(
          { length: barCount },
          (_, i) => 0.1 + Math.sin(i * 0.5) * 0.05,
        );
        setAudioData(pausedData);
      } else {
        setAudioData(Array(barCount).fill(0.1)); // Flat line when idle
      }

      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
        animationRef.current = null;
      }
    }
  }, [playerState.status, barCount]);

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

        // Create a gradient effect across the visualization
        const hueRotation = (index / barCount) * 60; // Subtle color variation

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
              transition:
                playerState.status === "playing" ? "none" : "height 0.5s",
              filter: `hue-rotate(${hueRotation}deg)`,
            }}
          />
        );
      })}
    </div>
  );
};

export default AudioVisualizer;
