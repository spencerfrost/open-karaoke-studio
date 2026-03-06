import React from "react";
import { cn } from "@/lib/utils";
import type { ChordEvent } from "@/types/Song";

interface ChordCarouselProps {
  chords: ChordEvent[];
  currentTime: number;
  className?: string;
}

const WINDOW_RADIUS = 2;

function findActiveChordIndex(chords: ChordEvent[], timeSeconds: number): number {
  if (chords.length === 0) return -1;
  if (timeSeconds < chords[0].time) return 0;

  let left = 0;
  let right = chords.length - 1;

  while (left <= right) {
    const mid = Math.floor((left + right) / 2);
    const midTime = chords[mid].time;

    if (midTime <= timeSeconds) {
      left = mid + 1;
    } else {
      right = mid - 1;
    }
  }

  return Math.max(0, right);
}

const ChordCarousel: React.FC<ChordCarouselProps> = ({
  chords,
  currentTime,
  className,
}) => {
  const displayTime = React.useMemo(
    () => Math.floor(currentTime * 10) / 10,
    [currentTime],
  );

  const activeIndex = React.useMemo(
    () => findActiveChordIndex(chords, displayTime),
    [chords, displayTime],
  );

  const visibleChords = React.useMemo(() => {
    const result: Array<{ slot: number; event: ChordEvent | null }> = [];

    for (let offset = -WINDOW_RADIUS; offset <= WINDOW_RADIUS; offset += 1) {
      const index = activeIndex + offset;
      result.push({
        slot: offset,
        event: index >= 0 && index < chords.length ? chords[index] : null,
      });
    }

    return result;
  }, [activeIndex, chords]);

  if (chords.length === 0) {
    return (
      <div
        className={cn(
          "pointer-events-none absolute top-20 left-1/2 -translate-x-1/2 z-20",
          className,
        )}
      >
        <div className="rounded-full border border-white/15 bg-black/40 px-5 py-2 text-sm text-white/45 backdrop-blur-sm">
          Chords unavailable
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "pointer-events-none absolute top-20 left-1/2 -translate-x-1/2 z-20",
        className,
      )}
      aria-live="polite"
      aria-label="Current and upcoming chords"
    >
      <div className="rounded-full border border-white/10 bg-black/35 px-4 py-2 backdrop-blur-sm">
        <div className="flex items-center justify-center gap-3 sm:gap-4">
          {visibleChords.map(({ slot, event }) => {
            const isCurrent = slot === 0;
            return (
              <div
                key={`${slot}-${event?.time ?? "empty"}`}
                className={cn(
                  "w-16 text-center transition-all duration-200 sm:w-20",
                  isCurrent
                    ? "scale-110 text-2xl font-bold text-orange-peel sm:text-3xl"
                    : "text-lg text-white/50 sm:text-xl",
                )}
                aria-current={isCurrent ? "true" : undefined}
              >
                {event?.chord ?? "·"}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default React.memo(ChordCarousel);
