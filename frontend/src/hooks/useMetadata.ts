import { useMutation } from '@tanstack/react-query';
import { Song } from '../types/Song';

/**
 * Hook for metadata-related operations
 */
export const useMetadata = () => {

  /**
   * Search MusicBrainz for song metadata using mutation pattern
   * This is the preferred pattern for triggered searches in React Query
   */
  const useSearchMusicBrainz = () => {
    return useMutation<
      Array<Partial<Song>>,
      Error,
      { title?: string; artist?: string; album?: string }
    >({
      mutationFn: async (params: { title?: string; artist?: string; album?: string }) => {
        const queryParams = new URLSearchParams();
        if (params.title) queryParams.append('title', params.title);
        if (params.artist) queryParams.append('artist', params.artist);
        if (params.album) queryParams.append('album', params.album);
        
        const response = await fetch(`/api/musicbrainz/search?${queryParams.toString()}`, {
          credentials: 'include',
        });
        
        if (!response.ok) {
          let errorMessage = `HTTP error! Status: ${response.status}`;
          try {
            const errorData: { message?: string; error?: string } = await response.json();
            errorMessage = errorData?.message || errorData?.error || errorMessage;
          } catch (jsonError) {
            console.error("Error parsing error response:", jsonError);
          }
          throw new Error(errorMessage);
        }
        
        return await response.json();
      },
      // Optional: Add caching by setting a mutation key
      mutationKey: ['musicbrainz', 'search'],
    });
  };

  return {
    useSearchMusicBrainz,
  };
};
