/**
 * useSongSuggestions - Hook for fetching song suggestions
 * 
 * Currently suggests songs by the same artist, but designed to be
 * extended with more sophisticated recommendation algorithms in the future.
 */

import { useMemo } from 'react';
import { useSongs } from '@/hooks/api/useSongs';
import type { Song } from '@/types/Song';

export interface SuggestionContext {
  /** The song that just finished playing */
  currentSong: Song;
  /** Optional: Limit the number of suggestions */
  limit?: number;
}

export interface SongSuggestion {
  song: Song;
  /** Reason for the suggestion (for future UI enhancements) */
  reason: 'same_artist' | 'similar_genre' | 'popular' | 'random';
  /** Relevance score (higher = more relevant) */
  score: number;
}

export interface UseSongSuggestionsResult {
  suggestions: SongSuggestion[];
  isLoading: boolean;
  error: Error | null;
}

/**
 * Get song suggestions based on the current song context
 * 
 * Future improvements could include:
 * - Similar genre matching
 * - Recently added songs
 * - Popular songs in the library
 * - Songs the current user hasn't sung yet
 * - Tempo/mood matching
 */
export function useSongSuggestions(
  context: SuggestionContext | null
): UseSongSuggestionsResult {
  const { useSongs: useSongsQuery } = useSongs();
  const limit = context?.limit ?? 6;
  
  // Fetch songs by the same artist if we have a current song
  const artistQuery = context?.currentSong?.artist;
  const { 
    data: artistSongs, 
    isLoading, 
    error 
  } = useSongsQuery(
    artistQuery ? { q: artistQuery, limit: limit + 1 } : {},
    { enabled: !!artistQuery }
  );

  const suggestions = useMemo((): SongSuggestion[] => {
    if (!context?.currentSong || !artistSongs) {
      return [];
    }

    const currentSongId = context.currentSong.id;
    
    // Filter out the current song and map to suggestions
    const sameArtistSuggestions = artistSongs
      .filter((song: Song) => song.id !== currentSongId)
      // Prioritize exact artist matches
      .filter((song: Song) => 
        song.artist?.toLowerCase() === context.currentSong.artist?.toLowerCase()
      )
      .slice(0, limit)
      .map((song: Song, index: number): SongSuggestion => ({
        song,
        reason: 'same_artist',
        // Score decreases with position (for potential future sorting)
        score: 100 - index * 10,
      }));

    return sameArtistSuggestions;
  }, [context, artistSongs, limit]);

  return {
    suggestions,
    isLoading,
    error: error as Error | null,
  };
}

/**
 * Utility to get the display text for a suggestion reason
 */
export function getSuggestionReasonText(reason: SongSuggestion['reason']): string {
  switch (reason) {
    case 'same_artist':
      return 'More from this artist';
    case 'similar_genre':
      return 'Similar style';
    case 'popular':
      return 'Popular in your library';
    case 'random':
      return 'You might like';
    default:
      return 'Suggested';
  }
}
