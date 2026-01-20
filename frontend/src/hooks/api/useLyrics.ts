import { useState } from "react";

export type LyricsProvider = "lrclib" | "syncedlyrics";

export interface LyricsOption {
  id: string;
  source: string;
  trackName?: string;
  artistName?: string;
  plainLyrics?: string;
  syncedLyrics?: string;
  preview?: string;
  duration?: number;
  albumName?: string;
  name?: string;
  instrumental?: boolean;
}

export interface LyricsSearchRequest {
  title: string;
  artist: string;
  album?: string;
  provider?: LyricsProvider;
}

/**
 * Simple hook to search for lyrics using the lyrics API
 * Supports automatic fallback: syncedlyrics -> LRCLIB if no results
 */
export function useLyricsSearch() {
  const [data, setData] = useState<LyricsOption[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [actualProvider, setActualProvider] = useState<LyricsProvider | null>(null);

  const search = async (params: LyricsSearchRequest, skipFallback = false) => {
    setLoading(true);
    setError(null);
    setData(null); // Clear previous results immediately to prevent race conditions

    try {
      // Determine endpoint based on provider
      const endpoint = params.provider === "syncedlyrics"
        ? "/api/lyrics/search-synced"
        : "/api/lyrics/search";

      const queryString = new URLSearchParams({
        track_name: params.title,
        artist_name: params.artist,
        ...(params.album ? { album_name: params.album } : {}),
      }).toString();
      let response;
      try {
        response = await fetch(`${endpoint}?${queryString}`);
      } catch (fetchError) {
        const errorMessage = fetchError instanceof Error ? fetchError.message : String(fetchError);
        throw new Error(`Network error: ${errorMessage}`);
      }
      if (!response.ok) throw new Error("Failed to fetch lyrics");
      const result = await response.json();

      // Check if we got results
      const hasResults = Array.isArray(result) && result.length > 0;

      // Automatic fallback: if syncedlyrics returns no results and fallback not disabled
      if (!hasResults && params.provider === "syncedlyrics" && !skipFallback) {
        console.log("🎵 No results from syncedlyrics, falling back to LRCLIB...");
        // Retry with LRCLIB, but skip further fallback to avoid infinite loop
        await search({ ...params, provider: "lrclib" }, true);
        return;
      }

      setData(result);
      setActualProvider(params.provider || "lrclib");
    } catch (err) {
      console.error(
        `🎵 Lyrics search failed for: ${params.artist} - ${params.title}`,
        err,
      );
      setError(err as Error);
      setActualProvider(null);
    } finally {
      setLoading(false);
    }
  };

  return { data, loading, error, search, actualProvider };
}
