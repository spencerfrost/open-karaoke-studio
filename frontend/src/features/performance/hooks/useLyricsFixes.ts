/**
 * useLyricsFixes - every way a singer can repair the current song's lyrics:
 * swap in a search result, paste their own, keep the timing offset, report.
 *
 * The phone and the TV rail lay these out differently but must save the same
 * way, so the mutations and their toasts live here and both surfaces call it.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import {
  selectCurrentSongId,
  useKaraokePlayerStore,
} from "@/stores/useKaraokePlayerStore";
import { useSongs } from "@/hooks/api/useSongs";
import {
  useReportLyrics,
  type LyricsReportKind,
} from "@/hooks/api/useLyricsReports";
import { applyOffsetToLrc } from "@/utils/lrcUtils";
import type { LyricsResult } from "@/features/lyrics/components/LyricsFetchDialog";
import type { Song } from "@/types/Song";

/** The two report buttons, in order, and what each says once it's sent. */
export const LYRICS_REPORTS: Array<{
  kind: LyricsReportKind;
  label: string;
  thanks: string;
}> = [
  {
    kind: "words",
    label: "Wrong words",
    thanks: "Thanks — looking for better lyrics",
  },
  {
    kind: "timing",
    label: "Out of sync",
    thanks: "Thanks — re-timing the lyrics to the singing",
  },
];

export const useLyricsFixes = () => {
  const songId = useKaraokePlayerStore(selectCurrentSongId);
  const lyricsOffset = useKaraokePlayerStore((state) => state.lyricsOffset);
  const setLyricsOffset = useKaraokePlayerStore(
    (state) => state.setLyricsOffset,
  );

  const { useSong, useUpdateSong } = useSongs();
  const { data: song } = useSong(songId ?? "");
  const updateSongMutation = useUpdateSong();
  const reportLyrics = useReportLyrics();

  const [reported, setReported] = useState<Set<LyricsReportKind>>(new Set());

  // A new song gets fresh report buttons.
  useEffect(() => {
    setReported(new Set());
  }, [songId]);

  /** The shape the search dialog wants. */
  const songForDialog = useMemo<Song | null>(
    () =>
      song
        ? ({
            id: songId,
            title: song.title,
            artist: song.artist,
            album: song.album || "",
            duration: song.duration,
          } as Song)
        : null,
    [songId, song],
  );

  const hasLyrics = !!(song?.syncedLyrics || song?.plainLyrics);
  // Only synced lyrics have timestamps to shift.
  const canSaveOffset = !!song?.syncedLyrics && lyricsOffset !== 0;

  const saveOffset = useCallback(() => {
    if (!songId || !song?.syncedLyrics || lyricsOffset === 0) return;

    updateSongMutation.mutate(
      {
        id: songId,
        syncedLyrics: applyOffsetToLrc(song.syncedLyrics, lyricsOffset),
      },
      {
        onSuccess: () => {
          setLyricsOffset(0); // The LRC carries it now
        },
        onError: (error) => {
          toast.error(`Failed to save: ${error.message}`);
        },
      },
    );
  }, [
    songId,
    song?.syncedLyrics,
    lyricsOffset,
    updateSongMutation,
    setLyricsOffset,
  ]);

  const applySearchResult = useCallback(
    (lyricsResult: LyricsResult, onSaved?: () => void) => {
      if (!songId) {
        toast.error("Cannot update song: missing song ID");
        return;
      }

      updateSongMutation.mutate(
        {
          id: songId,
          plainLyrics: lyricsResult.plainLyrics,
          syncedLyrics: lyricsResult.syncedLyrics,
        },
        {
          onSuccess: () => onSaved?.(),
          onError: (error) => {
            toast.error(`Failed to update lyrics: ${error.message}`);
          },
        },
      );
    },
    [songId, updateSongMutation],
  );

  const applyPaste = useCallback(
    (pastedLyrics: string, onSaved?: () => void) => {
      if (!songId) {
        toast.error("Cannot update song: missing song ID");
        return;
      }

      updateSongMutation.mutate(
        {
          id: songId,
          plainLyrics: pastedLyrics,
          syncedLyrics: undefined, // Clear synced lyrics when pasting plain lyrics
        },
        {
          onSuccess: () => onSaved?.(),
          onError: (error) => {
            toast.error(`Failed to save lyrics: ${error.message}`);
          },
        },
      );
    },
    [songId, updateSongMutation],
  );

  const report = useCallback(
    (kind: LyricsReportKind) => {
      if (!songId) return;
      reportLyrics.mutate(
        { songId, kind },
        {
          onSuccess: () => {
            setReported((previous) => new Set(previous).add(kind));
            const thanks = LYRICS_REPORTS.find((r) => r.kind === kind)?.thanks;
            if (thanks) toast.success(thanks);
          },
          onError: (error) => {
            toast.error(`Couldn't send that: ${error.message}`);
          },
        },
      );
    },
    [songId, reportLyrics],
  );

  return {
    songId,
    song,
    songForDialog,
    hasLyrics,
    canSaveOffset,
    saveOffset,
    isSaving: updateSongMutation.isPending,
    applySearchResult,
    applyPaste,
    report,
    reported,
    isReporting: reportLyrics.isPending,
  };
};

export type LyricsFixes = ReturnType<typeof useLyricsFixes>;
