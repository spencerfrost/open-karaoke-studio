import { useCallback } from 'react';
import { useApiQuery, useApiMutation, uploadFile } from './useApi';
import { Song, SongProcessingStatus } from '../types/Song';
import { useQueryClient, UseMutationResult } from '@tanstack/react-query';

// Query keys for React Query
const QUERY_KEYS = {
  songs: ['songs'] as const,
  song: (id: string) => ['songs', id] as const,
  songStatus: (id: string) => ['songs', id, 'status'] as const,
  songLyrics: (id: string) => ['songs', id, 'lyrics'] as const,
  musicbrainz: ['musicbrainz', 'search'] as const,
};

// Helper function to replace URL parameters
const formatUrl = (url: string, params: Record<string, string>) => {
  let formattedUrl = url;
  Object.entries(params).forEach(([key, value]) => {
    formattedUrl = formattedUrl.replace(`:${key}`, value);
  });
  return formattedUrl;
};

/**
 * Hook for interacting with song-related API endpoints
 */
export function useSongs() {
  const queryClient = useQueryClient();

  // ===== Queries =====

  /**
   * Get all songs in the library
   */
  const useAllSongs = (options = {}) => {
    return useApiQuery<Song[], typeof QUERY_KEYS.songs>(QUERY_KEYS.songs, 'songs', options);
  };

  /**
   * Get a specific song by ID
   */
  const useSong = (id: string, options = {}) => {
    return useApiQuery<Song, ReturnType<typeof QUERY_KEYS.song>>(
      QUERY_KEYS.song(id), 
      `songs/${id}`, 
      {
        enabled: !!id,
        ...options,
      }
    );
  };

  /**
   * Get song processing status
   */
  const useSongStatus = (id: string, options = {}) => {
    return useApiQuery<SongProcessingStatus, ReturnType<typeof QUERY_KEYS.songStatus>>(
      QUERY_KEYS.songStatus(id),
      `status/${id}`,
      {
        enabled: !!id,
        refetchInterval: (data) => 
          data && data.status === 'processing' || data?.status === 'queued' ? 2000 : false,
        ...options,
      }
    );
  };

  /**
   * Get song lyrics
   */
  const useSongLyrics = (songId: string, options = {}) => {
    return useApiQuery<
      { plainLyrics: string; syncedLyrics: string; duration: number },
      ReturnType<typeof QUERY_KEYS.songLyrics>
    >(
      QUERY_KEYS.songLyrics(songId), 
      `songs/${songId}/lyrics`, 
      {
        enabled: !!songId,
        ...options,
      }
    );
  };

  // ===== Mutations =====

  /**
   * Update a song
   */
  const useUpdateSong = () => {
    return useApiMutation<
      Song, 
      Partial<Song> & { id: string }
    >(
      'songs/:id',
      'put',
      {
        onMutate: async (variables) => {
          const { id, ...updates } = variables;
          await queryClient.cancelQueries({ queryKey: QUERY_KEYS.song(id) });
          
          // Save previous song
          const previousSong = queryClient.getQueryData<Song>(QUERY_KEYS.song(id));
          
          // Optimistically update the song
          if (previousSong) {
            queryClient.setQueryData<Song>(
              QUERY_KEYS.song(id),
              { ...previousSong, ...updates }
            );
            
            // Also update the song in the list of all songs
            const previousSongs = queryClient.getQueryData<Song[]>(QUERY_KEYS.songs);
            if (previousSongs) {
              queryClient.setQueryData<Song[]>(
                QUERY_KEYS.songs,
                previousSongs.map(song => 
                  song.id === id ? { ...song, ...updates } : song
                )
              );
            }
          }
          
          return { previousSong };
        },
        onError: (_err, variables, context: any) => {
          // If the mutation fails, roll back to the previous song
          if (context?.previousSong) {
            queryClient.setQueryData(
              QUERY_KEYS.song(variables.id), 
              context.previousSong
            );
          }
        },
        onSettled: (_data, _error, variables) => {
          // Refetch to ensure server state
          queryClient.invalidateQueries({ queryKey: QUERY_KEYS.song(variables.id) });
          queryClient.invalidateQueries({ queryKey: QUERY_KEYS.songs });
        },
        mutationFn: async (data) => {
          const { id, ...updates } = data;
          const url = formatUrl('songs/:id', { id });
          const response = await fetch(`/api/${url}`, {
            method: 'PUT',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(updates),
            credentials: 'include',
          });
          
          if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `Failed to update song: ${response.status}`);
          }
          
          return response.json();
        },
      }
    );
  };

  /**
   * Update song metadata
   */
  const useUpdateSongMetadata = () => {
    return useApiMutation<
      Song, 
      { id: string } & Partial<Song>
    >(
      'songs/:id/metadata',
      'patch',
      {
        onMutate: async (variables) => {
          const { id, ...metadata } = variables;
          await queryClient.cancelQueries({ queryKey: QUERY_KEYS.song(id) });
          
          // Save previous song
          const previousSong = queryClient.getQueryData<Song>(QUERY_KEYS.song(id));
          
          // Optimistically update the song
          if (previousSong) {
            queryClient.setQueryData<Song>(
              QUERY_KEYS.song(id),
              { ...previousSong, ...metadata }
            );
            
            // Also update the song in the list of all songs
            const previousSongs = queryClient.getQueryData<Song[]>(QUERY_KEYS.songs);
            if (previousSongs) {
              queryClient.setQueryData<Song[]>(
                QUERY_KEYS.songs,
                previousSongs.map(song => 
                  song.id === id ? { ...song, ...metadata } : song
                )
              );
            }
          }
          
          return { previousSong };
        },
        onError: (_err, variables, context: any) => {
          // If the mutation fails, roll back to the previous song
          if (context?.previousSong) {
            queryClient.setQueryData(
              QUERY_KEYS.song(variables.id), 
              context.previousSong
            );
          }
        },
        onSettled: (_data, _error, variables) => {
          // Refetch to ensure server state
          queryClient.invalidateQueries({ queryKey: QUERY_KEYS.song(variables.id) });
          queryClient.invalidateQueries({ queryKey: QUERY_KEYS.songs });
        },
        mutationFn: async (data) => {
          const { id, ...metadata } = data;
          const url = formatUrl('songs/:id/metadata', { id });
          const response = await fetch(`/api/${url}`, {
            method: 'PATCH',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(metadata),
            credentials: 'include',
          });
          
          if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `Failed to update metadata: ${response.status}`);
          }
          
          return response.json();
        },
      }
    );
  };

  /**
   * Delete a song
   */
  const useDeleteSong = (): UseMutationResult<{ success: boolean }, Error, string, unknown> => {
    return useApiMutation<{ success: boolean }, string>(
      'songs/:id',
      'delete',
      {
        // Skip all the optimistic update logic for now, just focus on successful deletion
        onSuccess: () => {
          queryClient.invalidateQueries({ queryKey: QUERY_KEYS.songs });
        },
        mutationFn: async (id) => {
          console.log('Deleting song with ID:', id); // Debug log
          const url = formatUrl('songs/:id', { id });
          console.log('Delete URL:', `/api/${url}`); // Debug log
          
          const response = await fetch(`/api/${url}`, {
            method: 'DELETE',
            credentials: 'include',
          });
          
          if (!response.ok) {
            const errorText = await response.text();
            console.error('Delete error response:', errorText); // Debug log
            
            let errorMessage = `Failed to delete song: ${response.status}`;
            try {
              const errorData = JSON.parse(errorText);
              errorMessage = errorData.error || errorMessage;
            } catch (e) {
              // If parsing fails, just use the error text
              errorMessage = errorText || errorMessage;
            }
            
            throw new Error(errorMessage);
          }
          
          // If the server returned no content
          if (response.status === 204) {
            return { success: true };
          }
          
          return response.json();
        },
      }
    );
  };

  /**
   * Toggle favorite status of a song
   */
  const useToggleFavorite = () => {
    return useApiMutation<
      Song, 
      { id: string; isFavorite: boolean }
    >(
      'songs/:id',
      'put',
      {
        onMutate: async (variables) => {
          const { id, isFavorite } = variables;
          await queryClient.cancelQueries({ queryKey: QUERY_KEYS.song(id) });
          
          // Save previous song
          const previousSong = queryClient.getQueryData<Song>(QUERY_KEYS.song(id));
          
          // Optimistically update the song
          if (previousSong) {
            queryClient.setQueryData<Song>(
              QUERY_KEYS.song(id),
              { ...previousSong, favorite: isFavorite }
            );
            
            // Also update the song in the list of all songs
            const previousSongs = queryClient.getQueryData<Song[]>(QUERY_KEYS.songs);
            if (previousSongs) {
              queryClient.setQueryData<Song[]>(
                QUERY_KEYS.songs,
                previousSongs.map(song => 
                  song.id === id ? { ...song, favorite: isFavorite } : song
                )
              );
            }
          }
          
          return { previousSong };
        },
        onError: (_err, variables, context: any) => {
          // If the mutation fails, roll back to the previous song
          if (context?.previousSong) {
            queryClient.setQueryData(
              QUERY_KEYS.song(variables.id), 
              context.previousSong
            );
          }
        },
        onSettled: (_data, _error, variables) => {
          // Refetch to ensure server state
          queryClient.invalidateQueries({ queryKey: QUERY_KEYS.song(variables.id) });
          queryClient.invalidateQueries({ queryKey: QUERY_KEYS.songs });
        },
        mutationFn: async (data) => {
          const { id, isFavorite } = data;
          const url = formatUrl('songs/:id', { id });
          const response = await fetch(`/api/${url}`, {
            method: 'PUT',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ favorite: isFavorite }),
            credentials: 'include',
          });
          
          if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `Failed to toggle favorite: ${response.status}`);
          }
          
          return response.json();
        },
      }
    );
  };

  /**
   * Search MusicBrainz for song metadata
   */
  const useSearchMusicBrainz = () => {
    return useApiMutation<
      Array<Partial<Song>>,
      { title?: string; artist?: string }
    >('musicbrainz/search', 'post');
  };
  
  // ===== Utility Functions =====

  /**
   * Get a playback URL for a given song track type
   */
  const getAudioUrl = useCallback(
    (songId: string, trackType: 'vocals' | 'instrumental' | 'original'): string => {
      return `/api/songs/${songId}/download/${trackType}`;
    },
    []
  );

  /**
   * Upload a song file for processing
   */
  const uploadSong = useCallback(
    async (file: File, metadata?: Record<string, unknown>) => {
      return uploadFile<Song>('songs/upload', file, metadata);
    },
    []
  );

  /**
   * Download vocal track
   */
  const downloadVocals = useCallback(async (songId: string, filename?: string) => {
    const url = `/api/songs/${songId}/download/vocals`;
    await downloadFile(url, filename ?? `vocals-${songId}.mp3`);
  }, []);

  /**
   * Download instrumental track
   */
  const downloadInstrumental = useCallback(async (songId: string, filename?: string) => {
    const url = `/api/songs/${songId}/download/instrumental`;
    await downloadFile(url, filename ?? `instrumental-${songId}.mp3`);
  }, []);

  /**
   * Download original track
   */
  const downloadOriginal = useCallback(async (songId: string, filename?: string) => {
    const url = `/api/songs/${songId}/download/original`;
    await downloadFile(url, filename ?? `original-${songId}.mp3`);
  }, []);

  /**
   * Fetch an audio file as an ArrayBuffer for Web Audio API
   */
  const fetchAudioBuffer = useCallback(async (url: string): Promise<ArrayBuffer> => {
    const response = await fetch(url);
    if (!response.ok) throw new Error("Failed to fetch audio file");
    return await response.arrayBuffer();
  }, []);

  return {
    // Queries
    useAllSongs,
    useSong,
    useSongStatus,
    useSongLyrics,
    
    // Mutations
    useUpdateSong,
    useUpdateSongMetadata,
    useDeleteSong,
    useToggleFavorite,
    useSearchMusicBrainz,
    
    // Utility functions
    getAudioUrl,
    uploadSong,
    downloadVocals,
    downloadInstrumental,
    downloadOriginal,
    fetchAudioBuffer,
  };
}

/**
 * Helper function to download a file
 */
async function downloadFile(endpoint: string, filename: string): Promise<void> {
  try {
    const response = await fetch(endpoint, {
      method: "GET",
      credentials: "include",
    });

    if (!response.ok) {
      throw new Error(`Download failed with status ${response.status}`);
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  } catch (error) {
    console.error("Download error:", error);
    throw error;
  }
}
