/**
 * SongProcessingTracker - one song's progress, inline under the search result
 * that just added it, so a phone user sees it start without leaving the page.
 *
 * Until the song shows up in the jobs feed (or after it has left it, on a
 * device with no session to own it) the library's own status fills in.
 */

import React from "react";
import { useSongs } from "@/hooks/api/useSongs";
import { JOB_STEPS } from "@/types/Song";
import type { TrackerRow } from "./jobTimeline";
import { ProcessingTrackerRow } from "./ProcessingTrackerRow";
import { useJobTracker } from "./useJobTracker";

interface SongProcessingTrackerProps {
  songId: string;
  className?: string;
}

export const SongProcessingTracker: React.FC<SongProcessingTrackerProps> = ({
  songId,
  className,
}) => {
  const rows = useJobTracker();
  const tracked = rows.find((r) => r.songId === songId);
  const { useSong } = useSongs();
  const { data: song } = useSong(tracked ? "" : songId);

  const row: TrackerRow = tracked ?? {
    songId,
    title: song?.title,
    artist: song?.artist,
    isMine: false,
    phase:
      song?.status === "processed" || song?.status === "error"
        ? "finished"
        : "waiting",
    step: null,
    stepNumber: null,
    stepCount: JOB_STEPS.length,
    progress: 0,
    ahead: 0,
  };

  return (
    <div aria-live="polite">
      <ProcessingTrackerRow row={row} hideTitle className={className} />
    </div>
  );
};
