import { useEffect, useRef } from "react";

import { useApiQuery } from "@/hooks/api/useApi";
import type { InstrumentalInterval, WordTimestamp } from "@/utils/lrcParser";

interface AlignmentData {
  words: WordTimestamp[];
  instrumental_intervals?: InstrumentalInterval[];
  language: string;
  aligned_at: string;
  word_count: number;
  line_count: number;
  mean_score?: number;
}

interface AlignmentResponse {
  alignment: AlignmentData | null;
}

/**
 * Fetch stored word-level alignment data for a song.
 * Returns null if no alignment has been run yet.
 */
export function useLyricsAlignment(songId: string | undefined) {
  const pollingStartedAt = useRef<number | null>(null);

  useEffect(() => {
    // Reset polling window when switching songs.
    pollingStartedAt.current = null;
  }, [songId]);

  const query = useApiQuery<AlignmentResponse, readonly unknown[]>(
    ["lyrics", songId, "alignment"] as const,
    `lyrics/songs/${songId}/alignment`,
    {
      enabled: !!songId,
      staleTime: 30 * 1000,
      // Newly imported songs may return alignment=null until async job finishes.
      // Poll for up to 10 minutes; use slower cadence after warmup to avoid excess traffic.
      refetchInterval: (state) => {
        const data = state.state.data as AlignmentResponse | undefined;
        if (data?.alignment) return false;
        if (pollingStartedAt.current === null) {
          pollingStartedAt.current = Date.now();
        }
        const elapsedMs = Date.now() - pollingStartedAt.current;
        if (elapsedMs > 10 * 60_000) return false;
        return elapsedMs < 2 * 60_000 ? 5000 : 15000;
      },
      refetchOnWindowFocus: true,
      retry: false,
    },
  );

  return {
    words: query.data?.alignment?.words ?? null,
    instrumentalIntervals:
      query.data?.alignment?.instrumental_intervals ?? null,
    meanScore: query.data?.alignment?.mean_score ?? null,
    isLoading: query.isLoading,
    error: query.error,
  };
}
