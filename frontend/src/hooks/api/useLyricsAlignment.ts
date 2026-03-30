import { useApiQuery } from "@/hooks/api/useApi";
import type { WordTimestamp } from "@/utils/lrcParser";

interface AlignmentData {
  words: WordTimestamp[];
  language: string;
  aligned_at: string;
  word_count: number;
  line_count: number;
  mean_score?: number;
  low_confidence?: boolean;
}

interface AlignmentResponse {
  lyricsId?: number;
  isActive?: boolean;
  metadata?: Record<string, unknown>;
  alignment: AlignmentData | null;
}

/**
 * Fetch stored word-level alignment data for a song's active word_synced lyrics.
 * Returns null if no alignment has been run yet.
 * The query is disabled when songId is not provided.
 */
export function useLyricsAlignment(songId: string | undefined) {
  const query = useApiQuery<AlignmentResponse, readonly unknown[]>(
    ["lyrics", songId, "alignment"] as const,
    `lyrics/songs/${songId}/alignment`,
    {
      enabled: !!songId,
      staleTime: 5 * 60 * 1000, // 5 min — alignment data rarely changes
      retry: false,
    },
  );

  return {
    words: query.data?.alignment?.words ?? null,
    meanScore: query.data?.alignment?.mean_score ?? null,
    isActive: query.data?.isActive ?? false,
    isLoading: query.isLoading,
    error: query.error,
  };
}
