/**
 * LyricsDisplay - Pure component for rendering synced/unsynced lyrics
 * Handles scrolling, highlighting, and different sizes
 * Optimized for performance with smooth scrolling and proper accessibility
 */

import React, { memo } from 'react';
import { Lrc } from 'react-lrc';
import type { LyricsSize } from '../KaraokePlayer.types';

interface LyricsDisplayProps {
  lyrics: string;
  isSync: boolean;
  currentTime: number;        // in milliseconds
  lyricsSize: LyricsSize;
  lyricsOffset: number;       // in milliseconds
  className?: string;
  'aria-label'?: string;
}

const LyricsDisplay: React.FC<LyricsDisplayProps> = memo(({
  lyrics,
  isSync,
  currentTime,
  lyricsSize,
  lyricsOffset,
  className = "",
  'aria-label': ariaLabel = "Song lyrics",
}) => {
  const lyricsSizeClass =
    lyricsSize === "small"
      ? "text-base"
      : lyricsSize === "large"
        ? "text-3xl"
        : "text-xl";

  const activeLyricsSizeClass =
    lyricsSize === "small"
      ? "text-lg"
      : lyricsSize === "large"
        ? "text-4xl"
        : "text-2xl";

  if (isSync) {
    return (
      <Lrc
        lrc={lyrics}
        currentMillisecond={currentTime + lyricsOffset}
        verticalSpace={true}
        lineRenderer={({ active, line }) => (
          <div
            className={`py-2 px-2 transition-all duration-500 text-center ${
              active
                ? `text-background font-bold ${activeLyricsSizeClass} text-shadow`
                : `text-background/50 opacity-70 ${lyricsSizeClass}`
            }`}
            role={active ? "status" : undefined}
            aria-live={active ? "polite" : undefined}
          >
            {line.content}
          </div>
        )}
        className={`lrc h-full w-full overflow-y-scroll scrollbar-hide pb-20 mask-image-fade-bottom ${className}`}
        role="region"
        aria-label={ariaLabel}
      />
    );
  }

  return (
    <div 
      className={`w-full h-full overflow-y-auto scrollbar-hide ${className}`}
      role="region"
      aria-label={ariaLabel}
    >
      {lyrics ? (
        <div
          className={`text-2xl font-semibold text-background whitespace-pre-line text-center ${lyricsSizeClass}`}
          role="document"
        >
          {lyrics}
        </div>
      ) : (
        <div className="text-gray-400" role="status">
          No lyrics available
        </div>
      )}
    </div>
  );
});

LyricsDisplay.displayName = 'LyricsDisplay';

export default LyricsDisplay;