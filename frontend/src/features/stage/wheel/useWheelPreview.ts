/**
 * useWheelPreview - plays the song the wheel rests on, quietly, after a beat.
 *
 * The same preview as a library card's hover (the shared preview store: the
 * original mix, from 30% in, for 30 seconds), started by the cursor resting
 * rather than by a hover. The delay is long enough that scrolling past songs
 * stays silent; only a song someone stops to look at plays.
 *
 * The store already cuts a preview the moment a performance starts and when
 * the tab is hidden.
 */

import { useEffect } from "react";
import { useCanPreview } from "@/features/songs/hooks/useSongPreview";
import { useSongPreviewStore } from "@/stores/useSongPreviewStore";
import type { Song } from "@/types/Song";

/** How long the cursor rests on a song before its preview starts. */
const WHEEL_PREVIEW_DELAY_MS = 1500;
/** Half volume: under the room's chatter, not over it. */
const WHEEL_PREVIEW_VOLUME = 0.5;

/** `song` is the one to preview, or null for silence. */
export function useWheelPreview(song: Song | null) {
  const canPreview = useCanPreview(song);
  const previewSong = canPreview ? song : null;

  useEffect(() => {
    if (!previewSong) return;
    const timer = window.setTimeout(() => {
      useSongPreviewStore
        .getState()
        .start(previewSong, { volume: WHEEL_PREVIEW_VOLUME });
    }, WHEEL_PREVIEW_DELAY_MS);
    return () => {
      window.clearTimeout(timer);
      // Scoped to this song so a late cleanup can't kill a newer preview.
      useSongPreviewStore.getState().stop(previewSong.id);
    };
    // Keyed on the id: a refetch that hands back a new object for the same
    // song must not restart its preview.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [previewSong?.id]);
}
