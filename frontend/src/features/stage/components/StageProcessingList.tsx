/**
 * StageProcessingList - the songs getting ready, beside the wheel.
 *
 * Compact on purpose: it gets a column of its own beside the wheel, and the
 * wheel shrinks to make room at the TV's ~960×540. It shows every song in the job queue,
 * everyone's, so a guest can see why theirs is still waiting. This session's
 * songs are marked as theirs and stay when finished, turning into "Sing this";
 * other sessions' songs drop off when done. A finished song leaves when it is
 * queued by any route (StageShell watches the queue), when someone taps
 * "Not now", or when it goes untouched past its TTL (see jobTimeline).
 *
 * Reads the stores itself, so the memoized song select screen never re-renders
 * on a progress tick.
 */

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { ItemGroup } from "@/components/ui/item";
import { ProcessingTrackerRow } from "@/features/songs/processing/ProcessingTrackerRow";
import { useJobTracker } from "@/features/songs/processing/useJobTracker";
import { cn } from "@/lib/utils";
import { useJobTrackerStore } from "@/stores/jobTrackerStore";
import type { Song } from "@/types/Song";
import { useSingThis } from "../hooks/useSingThis";

/** Rows before the rest collapse into "and N more". */
const MAX_ROWS = 3;

const SingThisButton: React.FC<{ song: Song; onStarted: () => void }> = ({
  song,
  onStarted,
}) => {
  const start = useSingThis(song);
  const [starting, setStarting] = useState(false);

  const handleClick = async () => {
    setStarting(true);
    try {
      if (await start()) onStarted();
    } finally {
      setStarting(false);
    }
  };

  return (
    <Button
      data-tour="sing-this"
      variant="primary"
      size="sm"
      disabled={starting}
      onClick={handleClick}
    >
      Sing this
    </Button>
  );
};

interface StageProcessingListProps {
  className?: string;
}

const StageProcessingList: React.FC<StageProcessingListProps> = ({
  className,
}) => {
  const rows = useJobTracker();
  const dismiss = useJobTrackerStore((s) => s.dismiss);

  if (rows.length === 0) return null;

  const shown = rows.slice(0, MAX_ROWS);
  const more = rows.length - shown.length;

  return (
    <section
      data-tour="processing-list"
      aria-label="Songs getting ready"
      className={cn(
        "rounded-xl bg-surface/95 p-1.5 shadow-xl ring-1 ring-border/30",
        className,
      )}
    >
      <h2 className="px-3 pb-0.5 pt-1 font-display text-xs uppercase tracking-[0.14em] text-foreground-faint">
        Getting songs ready
      </h2>
      <ItemGroup className="gap-1">
        {shown.map((row) => (
          <ProcessingTrackerRow
            key={row.songId}
            row={row}
            renderReady={(song) => (
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => dismiss(row.songId)}
                >
                  Not now
                </Button>
                <SingThisButton
                  song={song}
                  onStarted={() => dismiss(row.songId)}
                />
              </>
            )}
            renderFailed={() => (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => dismiss(row.songId)}
              >
                OK
              </Button>
            )}
          />
        ))}
      </ItemGroup>
      {more > 0 && (
        <p className="px-3 pb-1 pt-0.5 text-xs text-foreground-faint">
          and {more} more
        </p>
      )}
    </section>
  );
};

export default StageProcessingList;
