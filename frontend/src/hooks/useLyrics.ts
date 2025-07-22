import { useState } from "react";

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
}

/**
 * Simple hook to search for lyrics using the lyrics API
 */
export function useLyricsSearch() {
  const [data, setData] = useState<LyricsOption[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const search = async (params: LyricsSearchRequest) => {
    setLoading(true);
    setError(null);
    try {
      const queryString = new URLSearchParams({
        track_name: params.title,
        artist_name: params.artist,
        ...(params.album ? { album_name: params.album } : {}),
      }).toString();
      const response = await fetch(`/api/lyrics/search?${queryString}`);
      if (!response.ok) throw new Error("Failed to fetch lyrics");
      const result = await response.json();
      setData(result);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  };

  return { data, loading, error, search };
}
