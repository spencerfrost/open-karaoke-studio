import { useMutation } from '@tanstack/react-query';

export interface ITunesSearchParams {
  artist: string;
  title: string;
  album?: string;
  limit?: number;
}

export interface ITunesSearchResult {
  trackId: number;
  artistId: number;
  collectionId: number;
  trackName: string;
  artistName: string;
  collectionName: string;
  artworkUrl30?: string;
  artworkUrl60?: string;
  artworkUrl100?: string;
  artworkUrl600?: string;
  previewUrl?: string;
  releaseDate?: string;
  primaryGenreName?: string;
  trackTimeMillis?: number;
  trackNumber?: number;
  discNumber?: number;
  country?: string;
  trackPrice?: number;
  trackExplicitness?: string;
  collectionExplicitness?: string;
  isStreamable?: boolean;
  // Additional computed fields
  releaseYear?: number;
  releaseDateFormatted?: string;
  durationSeconds?: number;
}

export interface ITunesApiResponse {
  resultCount: number;
  results: ITunesSearchResult[];
}

/**
 * Hook for iTunes Search API integration
 * Uses the backend's sophisticated search logic for best results
 */
export const useItunesSearch = () => {
  
  /**
   * Search iTunes using the backend's sophisticated search logic
   * Uses mutation pattern for triggered searches
   */
  const useSearchItunes = () => {
    return useMutation<ITunesSearchResult[], Error, ITunesSearchParams>({
      mutationFn: async (params: ITunesSearchParams) => {
        const { artist, title, album, limit = 10 } = params;
        
        // Use backend's metadata search endpoint which includes
        // sophisticated filtering, canonical release prioritization,
        // and compilation avoidance
        const searchParams = new URLSearchParams();
        if (artist) searchParams.append('artist', artist);
        if (title) searchParams.append('title', title);
        if (album) searchParams.append('album', album);
        searchParams.append('limit', limit.toString());
        
        const url = `/api/metadata/search?${searchParams.toString()}`;
        
        const response = await fetch(url, {
          method: 'GET',
          headers: {
            'Accept': 'application/json',
          },
        });
        
        if (!response.ok) {
          throw new Error(`Metadata search error: ${response.status} ${response.statusText}`);
        }
        
        interface MetadataApiResponse {
          results: Array<{
            metadataId: string;
            title: string;
            artist: string;
            album: string;
            releaseDate: string;
            genre: string;
            duration: number;
            trackNumber: number;
            explicit: boolean;
            previewUrl: string;
            artworkUrls: {
              small: string;
              medium: string;
              large: string;
            };
            // Raw iTunes data for compatibility
            rawData: ITunesSearchResult;
          }>;
          searchParams: Record<string, string | number | boolean>;
        }
        
        const data: MetadataApiResponse = await response.json();
        
        // Extract the raw iTunes data which already has backend's sophisticated sorting
        const results: ITunesSearchResult[] = data.results.map((result) => {
          // The backend returns processed metadata, but we want the raw iTunes format
          // for consistency with our existing components
          const rawData = result.rawData || {};
          
          // Build the result by combining processed data with raw iTunes data
          const processedResult: ITunesSearchResult = {
            // Spread raw data first to get all iTunes fields
            ...rawData,
            // Override with processed values where they exist and are more reliable
            trackId: parseInt(result.metadataId) || rawData.trackId || 0,
            trackName: result.title || rawData.trackName || '',
            artistName: result.artist || rawData.artistName || '',
            collectionName: result.album || rawData.collectionName || '',
            artworkUrl30: result.artworkUrls?.small || rawData.artworkUrl30,
            artworkUrl60: result.artworkUrls?.medium || rawData.artworkUrl60,
            artworkUrl100: result.artworkUrls?.large || rawData.artworkUrl100,
            previewUrl: result.previewUrl || rawData.previewUrl,
            releaseDate: result.releaseDate || rawData.releaseDate,
            primaryGenreName: result.genre || rawData.primaryGenreName,
            trackTimeMillis: result.duration ? result.duration * 1000 : rawData.trackTimeMillis,
            durationSeconds: result.duration || rawData.durationSeconds,
            trackNumber: result.trackNumber || rawData.trackNumber,
            trackExplicitness: result.explicit ? 'explicit' : (rawData.trackExplicitness || 'notExplicit'),
          };
          
          return processedResult;
        });
        
        return results;
      },
      mutationKey: ['itunes', 'search', 'backend'],
    });
  };

  return {
    useSearchItunes,
  };
};
