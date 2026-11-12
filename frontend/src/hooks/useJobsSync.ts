import { useEffect } from "react";
import { useJobsWebSocket } from "./api/useJobsWebSocket";
import { useProcessingIndicators } from "@/stores/processingIndicatorsStore";
import { useJobTrackerStore } from "@/stores/jobTrackerStore";
import { primaryJob } from "@/features/songs/processing/jobTimeline";
import type { SongProcessingStatus } from "@/types/Song";

/** How often finished processing rows are checked against their TTL. */
const PRUNE_INTERVAL_MS = 60 * 1000;

/**
 * Syncs job updates from the jobs WebSocket into the two stores that read them.
 * Should be used once at app level.
 *
 * - processingIndicatorsStore: one status per song_id, for song cards. A song
 *   can have two jobs at once (separation, then lyrics alignment starting
 *   before separation ends), so the card gets the earlier step - the one that
 *   decides whether the song can play yet.
 * - jobTrackerStore: the whole timeline per song, for the processing lists.
 *   Finished rows expire on a timer, since the feed can go quiet for hours.
 */
export function useJobsSync() {
  const { jobs } = useJobsWebSocket();
  const setProcessing = useProcessingIndicators((state) => state.setProcessing);
  const removeProcessing = useProcessingIndicators(
    (state) => state.removeProcessing,
  );
  const syncTracker = useJobTrackerStore((state) => state.sync);
  const pruneTracker = useJobTrackerStore((state) => state.prune);

  useEffect(() => {
    const timer = setInterval(pruneTracker, PRUNE_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [pruneTracker]);

  useEffect(() => {
    syncTracker(jobs);

    const bySong = new Map<string, SongProcessingStatus[]>();
    for (const job of jobs) {
      if (!job.song_id) continue;
      const group = bySong.get(job.song_id);
      if (group) group.push(job);
      else bySong.set(job.song_id, [job]);
    }

    for (const [songId, group] of bySong) {
      const job = primaryJob(group);
      if (job) setProcessing(songId, job);
    }

    // Songs whose jobs have all left the feed are done. Read the state directly:
    // depending on processingSongs here would loop.
    const current = useProcessingIndicators.getState().processingSongs;
    for (const songId of current.keys()) {
      if (!bySong.has(songId)) removeProcessing(songId);
    }
    // Zustand actions are stable; only the jobs list drives this.
  }, [jobs, setProcessing, removeProcessing, syncTracker]);
}
