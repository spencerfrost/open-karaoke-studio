import { useRef } from "react";

import { useApiQuery } from "@/hooks/api/useApi";
import type { WordTimestamp } from "@/utils/lrcParser";

interface AlignmentData {
  words: WordTimestamp[];
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

  const query = useApiQuery<AlignmentResponse, readonly unknown[]>(
    ["lyrics", songId, "alignment"] as const,
    `lyrics/songs/${songId}/alignment`,
    {
      enabled: !!songId,
      staleTime: 30 * 1000,
      // Newly imported songs may return alignment=null until async job finishes.
      // Poll for up to 60 seconds, then stop automatically to avoid indefinite traffic.
      refetchInterval: (state) => {
        const data = state.state.data as AlignmentResponse | undefined;
        if (data?.alignment) return false;
        if (pollingStartedAt.current === null) {
          pollingStartedAt.current = Date.now();
        }
        if (Date.now() - pollingStartedAt.current > 60_000) return false;
        return 5000;
      },
      refetchOnWindowFocus: true,
      retry: false,
    },
  );

  return {
    words: query.data?.alignment?.words ?? null,
    meanScore: query.data?.alignment?.mean_score ?? null,
    isLoading: query.isLoading,
    error: query.error,
  };
}
