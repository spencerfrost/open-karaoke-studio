import { useEffect } from "react";
import { useJobsWebSocket } from "./api/useJobsWebSocket";
import { useProcessingIndicators } from "@/stores/processingIndicatorsStore";

/**
 * Syncs job updates from WebSocket to processing indicators store.
 * Should be used once at app level.
 *
 * IMPORTANT: Jobs have a song_id field that links to the songs table.
 * We key the processing store by song_id (not job_id) so that song cards
 * can efficiently lookup their processing status.
 */
export function useJobsSync() {
  const { jobs } = useJobsWebSocket();
  const setProcessing = useProcessingIndicators((state) => state.setProcessing);
  const removeProcessing = useProcessingIndicators(
    (state) => state.removeProcessing,
  );

  useEffect(() => {
    // Create a set of current job IDs
    const currentJobIds = new Set(jobs.map((job) => job.id));

    // Update store with current jobs, keyed by song_id
    jobs.forEach((job) => {
      // Jobs from WebSocket should include song_id in the response
      const songId = (job as any).song_id;
      if (songId) {
        setProcessing(songId, job);
      }
    });

    // Remove jobs that are no longer in the jobs array
    // This handles cleanup when jobs complete and are removed by useJobsWebSocket
    // Get current state directly to avoid dependency loop
    const currentProcessingSongs = useProcessingIndicators.getState().processingSongs;
    for (const [songId, status] of currentProcessingSongs.entries()) {
      if (!currentJobIds.has(status.id)) {
        removeProcessing(songId);
      }
    }
    // Only depend on jobs - Zustand actions are stable and processingSongs causes infinite loops
  }, [jobs, setProcessing, removeProcessing]);
}
