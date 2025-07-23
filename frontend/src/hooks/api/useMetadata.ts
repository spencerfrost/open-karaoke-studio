import { useMutation } from "@tanstack/react-query";


export interface MetadataSearchResponse {
  count: number;
  results: MetadataOption[];
  search: {
    album: string;
    artist: string;
    limit: number;
    sort_by: string;
    title: string;
  };
  success: boolean;
}

export interface MetadataOption {
  metadataId: string;
  title: string;
  artist: string;
  artistId: number;
  album?: string;
  albumId?: number;
  releaseYear?: number;
  releaseDate?: string;
  duration?: number;
  discNumber?: number;
  trackNumber?: number;
  genre?: string;
  country?: string;
  artworkUrl?: string;
  previewUrl?: string;
  explicit?: boolean;
  isStreamable?: boolean;
  price?: number;
}

/**
 * Hook for metadata-related operations
 */
export const useMetadata = () => {
  /**
   * Search for song metadata using mutation pattern
   * This is the preferred pattern for triggered searches in React Query
   */
  const useSearchMetadata = () => {
    return useMutation({
      mutationFn: async (params: {
        title?: string;
        artist?: string;
        album?: string;
        sortBy?: string;
      }) => {
        const queryParams = new URLSearchParams();
        if (params.title) queryParams.append("title", params.title);
        if (params.artist) queryParams.append("artist", params.artist);
        if (params.album) queryParams.append("album", params.album);
        if (params.sortBy) queryParams.append("sort_by", params.sortBy);

        const response = await fetch(
          `/api/metadata/search?${queryParams.toString()}`
        );
        if (!response.ok) {
          let errorMessage = `HTTP error! Status: ${response.status}`;
          try {
            const errorData = await response.json();
            errorMessage =
              errorData?.message || errorData?.error || errorMessage;
          } catch {
            throw new Error(errorMessage);
          }
        }
        return await response.json();
      },
    });
  };

  const useSaveMetadata = () => {
    return useMutation({
      mutationFn: async (data: {
        songId: string;
        itunesId?: string;
      }) => {
        const response = await fetch("/api/metadata/save", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(data),
        });
        if (!response.ok) {
          let errorMessage = `HTTP error! Status: ${response.status}`;
          try {
            const errorData = await response.json();
            errorMessage =
              errorData?.message || errorData?.error || errorMessage;
          } catch {
            throw new Error(errorMessage);
          }
        }
        return { success: response.ok };
      },
    });
  };

  return {
    useSearchMetadata,
    useSaveMetadata,
  };
};
