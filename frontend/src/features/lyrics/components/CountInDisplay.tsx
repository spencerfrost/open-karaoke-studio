/**
 * CountInDisplay - Visual count-in animations for karaoke player
 * Displays progress-bar and lead-in highlight styles before upcoming lyric lines
 */

import React, { useMemo } from "react";
import type { CountInTrigger } from "@/utils/lrcUtils";

interface CountInDisplayProps {
  trigger: CountInTrigger;
  currentTime: number; // seconds

  // Boolean flags for the supported styles
  showProgressBar?: boolean;
  showLeadInHighlight?: boolean;

  // Position/styling
  lyricsSize: "small" | "medium" | "large";
  upcomingLineContent?: string;
}

const CountInDisplay: React.FC<CountInDisplayProps> = ({
  trigger,
  currentTime,
  showProgressBar = false,
  showLeadInHighlight = false,
  lyricsSize,
  upcomingLineContent,
}) => {
  const currentTimeMs = currentTime * 1000;

  // Check if count-in is active
  const isActive = useMemo(() => {
    return (
      currentTimeMs >= trigger.countInStart &&
      currentTimeMs < trigger.countInEnd
    );
  }, [currentTimeMs, trigger.countInStart, trigger.countInEnd]);

  // Calculate progress (0-1)
  const progress = useMemo(() => {
    const elapsed = currentTimeMs - trigger.countInStart;
    const duration = trigger.countInEnd - trigger.countInStart;
    return Math.max(0, Math.min(1, elapsed / duration));
  }, [currentTimeMs, trigger.countInStart, trigger.countInEnd]);

  const overlayTextSize = useMemo(() => {
    switch (lyricsSize) {
      case "small":
        return "text-lg"; // 1.125rem
      case "large":
        return "text-3xl"; // 1.875rem
      default:
        return "text-2xl"; // 1.5rem
    }
  }, [lyricsSize]);

  if (!isActive) return null;

  return (
    <div className="absolute inset-0 pointer-events-none">
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
          <div className={`font-semibold text-background/70 ${overlayTextSize}`}>
            {upcomingLineContent}
          </div>
        </div>
      )}
    </div>
  );
};

export default React.memo(CountInDisplay);
