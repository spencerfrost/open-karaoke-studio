import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { apiSend, useApiMutation, useApiQuery } from "@/hooks/api/useApi";

/**
 * How timing the fixed line's words went: "pending" while it runs (the new
 * words sit on the line's old timing meanwhile), "aligned" straight away when
 * only case or punctuation changed, "no_timing" when the song has no word
 * timing to patch (or no vocals to listen to).
 */
export type LineFixAlignStatus = "pending" | "aligned" | "failed" | "no_timing";

export interface LyricsLineFix {
  id: number;
  songId: string;
  /** The line before anyone fixed it. */
  oldText: string;
  newText: string;
  /** The line's LRC time when it was last fixed, in seconds. */
  lineStart: number | null;
  fixedBy: string | null;
  createdAt: string | null;
  updatedAt: string | null;
  alignStatus: LineFixAlignStatus;
  /** False when the lyrics no longer show the fix: its line is gone or was changed. */
  shown: boolean;
}

export interface LostLyricsLineFix extends LyricsLineFix {
  songTitle: string | null;
  songArtist: string | null;
}

interface SaveLineFixResponse {
  /** null when the line was typed back to its first text and the fix removed. */
  fix: LyricsLineFix | null;
  lineIndex: number;
  text: string;
}

export interface SaveLineFixVariables {
  songId: string;
  /** The line as the screen shows it. */
  lineStart: number;
  oldText: string;
  newText: string;
}

const fixesKey = (songId: string) => ["lyrics", songId, "line-fixes"] as const;
const LOST_KEY = ["lyrics", "line-fixes", "lost"] as const;

// A line's words are timed in a few seconds; stop asking after this long.
const PENDING_POLL_MS = 2_000;
const PENDING_POLL_LIMIT_MS = 3 * 60_000;

/** The text and word timing of a song changed: read both again. */
function invalidateSongLyrics(
  queryClient: ReturnType<typeof useQueryClient>,
  songId: string,
) {
  queryClient.invalidateQueries({ queryKey: ["songs", songId] });
  queryClient.invalidateQueries({ queryKey: ["lyrics", songId] });
}

/**
 * A song's line fixes. While a fixed line's words are being timed this
 * polls, and when the timing lands it refreshes the song's word timing so
 * the line lights up word by word again.
 */
export function useLyricsLineFixes(
  songId: string | undefined,
  { enabled = true }: { enabled?: boolean } = {},
) {
  const queryClient = useQueryClient();
  const pendingSince = useRef<number | null>(null);

  const query = useApiQuery<LyricsLineFix[], readonly unknown[]>(
    fixesKey(songId ?? ""),
    `lyrics/songs/${songId}/line-fixes`,
    {
      enabled: enabled && !!songId,
      refetchInterval: (state) => {
        const fixes = state.state.data;
        if (!fixes?.some((fix) => fix.alignStatus === "pending")) {
          pendingSince.current = null;
          return false;
        }
        pendingSince.current ??= Date.now();
        return Date.now() - pendingSince.current < PENDING_POLL_LIMIT_MS
          ? PENDING_POLL_MS
          : false;
      },
    },
  );

  // Pending → done: the line's new words are stored.
  const pendingIds = useRef<Set<number>>(new Set());
  useEffect(() => {
    if (!songId || !query.data) return;
    const nowPending = new Set(
      query.data.filter((f) => f.alignStatus === "pending").map((f) => f.id),
    );
    const finished = [...pendingIds.current].some((id) => !nowPending.has(id));
    pendingIds.current = nowPending;
    if (finished) {
      queryClient.invalidateQueries({
        queryKey: ["lyrics", songId, "alignment"],
      });
    }
  }, [query.data, songId, queryClient]);

  return query;
}

/** Fix one line, as the screen shows it. */
export function useSaveLineFix() {
  const queryClient = useQueryClient();
  return useApiMutation<SaveLineFixResponse, SaveLineFixVariables>(
    "lyrics/songs/:id/line-fixes",
    "post",
    {
      mutationFn: ({ songId, lineStart, oldText, newText }) =>
        apiSend<
          SaveLineFixResponse,
          { line_start: number; old_text: string; new_text: string }
        >(`lyrics/songs/${songId}/line-fixes`, "post", {
          line_start: lineStart,
          old_text: oldText,
          new_text: newText,
        }),
      onSuccess: (_data, { songId }) => {
        invalidateSongLyrics(queryClient, songId);
      },
    },
  );
}

/** Remove a fix, putting the line's first text back while it still shows. */
export function useUndoLineFix() {
  const queryClient = useQueryClient();
  return useApiMutation<
    { restored: boolean; songId: string | null },
    LyricsLineFix
  >("lyrics/line-fixes/:id", "delete", {
    mutationFn: (fix) =>
      apiSend<{ restored: boolean; songId: string | null }, null>(
        `lyrics/line-fixes/${fix.id}`,
        "delete",
      ),
    onSuccess: (_data, fix) => {
      invalidateSongLyrics(queryClient, fix.songId);
      queryClient.invalidateQueries({ queryKey: LOST_KEY });
    },
  });
}

/** Fixes the lyrics no longer show, across the library (admins). */
export function useLostLineFixes() {
  return useApiQuery<LostLyricsLineFix[], typeof LOST_KEY>(
    LOST_KEY,
    "lyrics/line-fixes/lost",
  );
}
