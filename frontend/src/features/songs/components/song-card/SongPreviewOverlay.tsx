import React from "react";
import { cn } from "@/lib/utils";

interface SongPreviewOverlayProps {
  isPreviewing: boolean;
  isLoading: boolean;
  /** 0–1 through the preview window. */
  progress: number;
}

const BAR_DELAYS = ["0ms", "180ms", "360ms"];
const BAR_HEIGHTS = ["h-2", "h-3.5", "h-2.5"];

/**
 * Ambient "this card is playing" chrome: an equalizer badge and a progress bar
 * along the bottom of the artwork.
 *
 * Sits at z-20 after the play overlay in DOM order so it paints above it while
 * still losing to the processing overlay at z-30. Decorative throughout — the
 * preview is announced by the toggle button, not by these.
 */
export const SongPreviewOverlay: React.FC<SongPreviewOverlayProps> = ({
  isPreviewing,
  isLoading,
  progress,
}) => {
  if (!isPreviewing && !isLoading) return null;

  return (
    <>
      <div
        aria-hidden
        className="absolute top-2 left-2 z-20 flex h-6 items-end gap-0.5 rounded-full bg-overlay/60 px-2 py-1.5 backdrop-blur-sm"
      >
        {isLoading ? (
          // A pulse reads as "warming up"; a spinner over artwork reads as broken.
          <span className="h-2 w-4 animate-pulse rounded-full bg-accent" />
        ) : (
          BAR_DELAYS.map((delay, i) => (
            <span
              key={delay}
              className={cn(
                "eq-bar w-0.5 rounded-full bg-accent",
                BAR_HEIGHTS[i],
              )}
              style={{ animationDelay: delay }}
            />
          ))
        )}
      </div>

      {isPreviewing && (
        <div
          aria-hidden
          className="absolute inset-x-0 bottom-0 z-20 h-1 bg-overlay/40"
        >
          <div
            className="h-full bg-primary motion-safe:transition-[width] motion-safe:duration-200"
            style={{ width: `${Math.min(progress * 100, 100)}%` }}
          />
        </div>
      )}
    </>
  );
};
