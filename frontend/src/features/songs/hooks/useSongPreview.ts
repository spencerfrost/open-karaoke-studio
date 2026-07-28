import { useCallback, useEffect, useRef } from "react";
import { useHoverCapable } from "@/hooks/useHoverCapable";
import { useProcessingIndicators } from "@/stores/processingIndicatorsStore";
import { useSettingsStore } from "@/stores/useSettingsStore";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import {
  HOVER_INTENT_MS,
  useSongPreviewStore,
} from "@/stores/useSongPreviewStore";
import { Song } from "@/types/Song";

interface UseSongPreviewOptions {
  enabled?: boolean;
}

interface SongPreviewHoverHandlers {
  onPointerEnter: (e: React.PointerEvent) => void;
  onPointerLeave: () => void;
}

/**
 * Per-card wiring for the shared hover preview.
 *
 * Owns the hover-intent delay so sweeping the cursor across a grid never fires
 * a request, plus every gate that decides whether this song may preview at all.
 */
export function useSongPreview(
  song: Song,
  options: UseSongPreviewOptions = {},
) {
  const { enabled = true } = options;

  const hoverCapable = useHoverCapable();
  const previewsEnabled = useSettingsStore(
    (state) => state.display.songPreviewsEnabled ?? true,
  );
  const karaokeIsPlaying = useKaraokePlayerStore((state) => state.isPlaying);
  const processingStatus = useProcessingIndicators((state) =>
    state.getStatus(song.id),
  );
  const isBlockingProcessing =
    !!processingStatus && processingStatus.engineType !== "lyrics_alignment";

  const previewSongId = useSongPreviewStore((state) => state.previewSongId);
  const status = useSongPreviewStore((state) => state.status);
  const storeProgress = useSongPreviewStore((state) => state.progress);
  const start = useSongPreviewStore((state) => state.start);
  const stop = useSongPreviewStore((state) => state.stop);

  const isCurrent = previewSongId === song.id;
  const isPreviewing = isCurrent && status === "playing";
  const isLoading = isCurrent && status === "loading";
  const progress = isCurrent ? storeProgress : 0;

  const canPreview =
    enabled &&
    previewsEnabled &&
    song.status === "processed" &&
    !isBlockingProcessing &&
    !karaokeIsPlaying;

  const timerRef = useRef<number | null>(null);

  const cancelPending = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const onPointerEnter = useCallback(
    (e: React.PointerEvent) => {
      // pointerType also filters the phantom enter a tap produces on hybrid
      // touchscreen laptops, which the media query alone would let through.
      if (!hoverCapable || e.pointerType !== "mouse" || !canPreview) return;

      cancelPending();
      timerRef.current = window.setTimeout(() => {
        timerRef.current = null;
        window.removeEventListener("scroll", cancelPending, true);
        start(song);
      }, HOVER_INTENT_MS);

      // Scrolling past a card should abandon a preview that hasn't started, but
      // must not interrupt one already playing — pointerleave handles that.
      window.addEventListener("scroll", cancelPending, {
        capture: true,
        passive: true,
        once: true,
      });
    },
    [hoverCapable, canPreview, cancelPending, start, song],
  );

  const stopPreview = useCallback(() => {
    cancelPending();
    stop(song.id);
  }, [cancelPending, stop, song.id]);

  const onPointerLeave = stopPreview;

  const togglePreview = useCallback(() => {
    cancelPending();
    if (isCurrent) {
      stop(song.id);
    } else if (canPreview) {
      start(song);
    }
  }, [cancelPending, isCurrent, canPreview, stop, start, song]);

  useEffect(() => {
    return () => {
      cancelPending();
      window.removeEventListener("scroll", cancelPending, true);
      // Scoped to this song so a late unmount can't kill a newer preview.
      useSongPreviewStore.getState().stop(song.id);
    };
  }, [cancelPending, song.id]);

  const hoverHandlers: SongPreviewHoverHandlers = {
    onPointerEnter,
    onPointerLeave,
  };

  return {
    canPreview,
    isPreviewing,
    isLoading,
    progress,
    hoverHandlers,
    togglePreview,
    stopPreview,
  };
}
