// Placeholder iTunes search hook for build compatibility
export interface ItunesSearchResult {
  trackId: number;
  artistId?: number;
  collectionId?: number;
  trackName: string;
  artistName: string;
  collectionName?: string;
  trackTimeMillis?: number;
  isExplicit?: boolean;
  previewUrl?: string;
  artworkUrl100?: string;
  artworkUrl600?: string;
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
