import { useMemo } from "react";
import { useJobTrackerStore } from "@/stores/jobTrackerStore";
import { useSessionStore } from "@/stores/sessionStore";
import { buildTrackerRows, type TrackerRow } from "./jobTimeline";

/**
 * The processing list as this device's session sees it: everyone's songs in
 * the job queue, with this session's marked as theirs and kept once finished.
 */
export function useJobTracker(): TrackerRow[] {
  const ownerTag = useSessionStore((s) => s.sessionInfo?.owner_tag ?? null);
  const songs = useJobTrackerStore((s) => s.songs);
  return useMemo(() => buildTrackerRows(songs, ownerTag), [songs, ownerTag]);
}
