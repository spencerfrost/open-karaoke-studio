/**
 * Comprehensive iTunes track metadata from lookup endpoint.
 * This includes all fields from both search and lookup APIs.
 */
export interface ITunesSearchResult {
  // Track identifiers
  trackId: number;
  artistId?: number;
  collectionId?: number;
  
  // Basic metadata
  trackName: string;
  artistName: string;
  collectionName?: string;
  primaryGenreName?: string;
  
  // Artwork URLs
  artworkUrl30?: string;
  artworkUrl60?: string;
  artworkUrl100?: string;
  artworkUrl600?: string;
  
  // Track details
  trackNumber?: number;
  trackCount?: number;
  discNumber?: number;
  discCount?: number;
  trackTimeMillis?: number;
  durationSeconds?: number; // Derived from trackTimeMillis
  
  // Release information
  releaseDate?: string;
  releaseYear?: number;
  releaseDateFormatted?: string;
  
  // Content advisory
  trackExplicitness?: string;
  collectionExplicitness?: string;
  contentAdvisoryRating?: string;
  isExplicit?: boolean;
  
  // Pricing and availability
  trackPrice?: number;
  collectionPrice?: number;
  currency?: string;
  country?: string;
  isStreamable?: boolean;
  
  // URLs
  previewUrl?: string;
  artistViewUrl?: string;
  collectionViewUrl?: string;
  trackViewUrl?: string;
  
  // Censored names
  trackCensoredName?: string;
  collectionCensoredName?: string;
  
  // Additional metadata (from lookup)
  copyright?: string;
  description?: string;
  
  // Genre information
  primaryGenreId?: number;
  genreIds?: number[];
}

export function useItunesSearch() {
  return {
    searchResults: [] as ItunesSearchResult[],
    isLoading: false,
    error: null,
    search: (_query: string) => Promise.resolve([]),
  };
}

export default useItunesSearch;
