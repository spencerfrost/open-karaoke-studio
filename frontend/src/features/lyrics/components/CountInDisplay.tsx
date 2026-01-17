/**
 * CountInDisplay - Visual count-in animations for karaoke player
 * Displays 4 mix-and-match visual styles before upcoming lyric lines
 */

import React, { useMemo } from "react";
import type { CountInTrigger } from "@/utils/lrcUtils";

interface CountInDisplayProps {
  trigger: CountInTrigger;
  currentTime: number; // seconds
  bpm: number;

  // Boolean flags for each style (mix-and-match)
  showCountdownNumbers?: boolean;
  showCountdownIcons?: boolean;
  showProgressBar?: boolean;
  showLeadInHighlight?: boolean;

  // Position/styling
  lyricsSize: "small" | "medium" | "large";
  upcomingLineContent?: string;
}

const CountInDisplay: React.FC<CountInDisplayProps> = ({
  trigger,
  currentTime,
  bpm,
  showCountdownNumbers = false,
  showCountdownIcons = false,
  showProgressBar = false,
  showLeadInHighlight = false,
  lyricsSize,
  upcomingLineContent,
}) => {
  const currentTimeMs = currentTime * 1000;

  // Check if count-in is active
  const isActive = useMemo(() => {
    return currentTimeMs >= trigger.countInStart && currentTimeMs < trigger.countInEnd;
  }, [currentTimeMs, trigger.countInStart, trigger.countInEnd]);

  // Calculate current beat index (0-3 for 4 beats)
  const currentBeatIndex = useMemo(() => {
    const elapsed = currentTimeMs - trigger.countInStart;
    return Math.floor(elapsed / trigger.beatInterval);
  }, [currentTimeMs, trigger.countInStart, trigger.beatInterval]);

  // Calculate progress (0-1)
  const progress = useMemo(() => {
    const elapsed = currentTimeMs - trigger.countInStart;
    const duration = trigger.countInEnd - trigger.countInStart;
    return Math.max(0, Math.min(1, elapsed / duration));
  }, [currentTimeMs, trigger.countInStart, trigger.countInEnd]);

  // Font size based on lyrics size
  const countdownSize = useMemo(() => {
    switch (lyricsSize) {
      case "small":
        return "text-lg"; // 1.125rem
      case "large":
        return "text-3xl"; // 1.875rem
      default:
        return "text-2xl"; // 1.5rem
    }
  }, [lyricsSize]);

  const iconSize = useMemo(() => {
    switch (lyricsSize) {
      case "small":
        return "w-2 h-2"; // 0.5rem
      case "large":
        return "w-4 h-4"; // 1rem
      default:
        return "w-3 h-3"; // 0.75rem
    }
  }, [lyricsSize]);

  if (!isActive) return null;

  return (
    <div className="absolute inset-0 pointer-events-none">
      {/* Numerical Countdown (4 3 2 1) - Left of lyrics */}
      {showCountdownNumbers && (
        <div
          className="absolute top-1/2 -translate-y-1/2 flex gap-2"
          style={{ left: "10%" }}
        >
          {[4, 3, 2, 1].map((num, idx) => (
            <span
              key={num}
              className={`
                font-bold transition-all duration-150
                ${countdownSize}
                ${
                  idx === currentBeatIndex
                    ? "text-orange-peel scale-125 opacity-100"
                    : "text-white/30 scale-100 opacity-70"
                }
              `}
            >
              {num}
            </span>
          ))}
        </div>
      )}

      {/* Countdown Icons (●●●●) - Left of lyrics */}
      {showCountdownIcons && (
        <div
          className="absolute top-1/2 -translate-y-1/2 flex gap-1.5"
          style={{ left: showCountdownNumbers ? "18%" : "10%" }}
        >
          {[0, 1, 2, 3].map((idx) => (
            <div
              key={idx}
              className={`
                rounded-full transition-all duration-100
                ${iconSize}
                ${
                  idx <= currentBeatIndex
                    ? "bg-transparent border-2 border-white/30"
                    : "bg-orange-peel"
                }
              `}
            />
          ))}
        </div>
      )}

      {/* Progress Bar - Centered in gap area */}
      {showProgressBar && (
        <div className="absolute bottom-1/4 left-1/2 -translate-x-1/2 w-3/5 max-w-md">
          <div className="w-full h-1 bg-white/10 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-orange-peel to-amber-500 rounded-full transition-all duration-100 ease-linear"
              style={{ width: `${progress * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* Lead-in Highlight - Glow on upcoming line text */}
      {showLeadInHighlight && upcomingLineContent && (
        <div
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2
                      text-center pointer-events-none transition-all duration-150"
          style={{
            filter: `brightness(${1 + progress * 0.3})`,
            textShadow: `0 0 ${progress * 20}px rgba(255, 107, 53, 0.5)`,
          }}
        >
          <div className={`font-semibold text-background/70 ${countdownSize}`}>
            {upcomingLineContent}
          </div>
        </div>
      )}
    </div>
  );
};

export default CountInDisplay;
