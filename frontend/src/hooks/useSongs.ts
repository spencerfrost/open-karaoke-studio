import { useCallback } from 'react';
import { useApiQuery, useApiMutation, uploadFile } from './useApi';
import { Song, SongProcessingStatus } from '../types/Song';
import { useQueryClient } from '@tanstack/react-query';

// Query keys for React Query
const QUERY_KEYS = {
  songs: ['songs'] as const,
  song: (id: string) => ['songs', id] as const,
  songStatus: (id: string) => ['songs', id, 'status'] as const,
  songLyrics: (id: string) => ['songs', id, 'lyrics'] as const,
  metadata: ['metadata', 'search'] as const,
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
        refetchInterval: (query) =>
          query.state.data && (query.state.data.status === 'processing' || query.state.data.status === 'queued') ? 2000 : false,
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
        onError: (_err, variables, context: unknown) => {
          const ctx = context as { previousSong?: Song } | undefined;
          if (ctx?.previousSong) {
            queryClient.setQueryData(
              QUERY_KEYS.song(variables.id),
              ctx.previousSong
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
            method: 'PATCH',
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
        onError: (_err, variables, context: unknown) => {
          // If the mutation fails, roll back to the previous song
          const typedContext = context as { previousSong?: Song } | undefined;
          if (typedContext?.previousSong) {
            queryClient.setQueryData(
              QUERY_KEYS.song(variables.id), 
              typedContext.previousSong
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
   * Update iTunes metadata for a song
   */
  const useUpdateItunesMetadata = () => {
    return useApiMutation<
      Song, 
      { 
        id: string;
        itunesTrackId?: number;
        itunesArtistId?: number;
        itunesCollectionId?: number;
        trackTimeMillis?: number;
        itunesExplicit?: boolean;
        itunesPreviewUrl?: string;
        itunesArtworkUrls?: {
          60?: string;
          100?: string;
          600?: string;
        };
      }
    >(
      'songs/:id/metadata/itunes',
      'patch',
      {
        onMutate: async (variables) => {
          const { id, ...metadata } = variables;
          await queryClient.cancelQueries({ queryKey: QUERY_KEYS.song(id) });
          
          const previousSong = queryClient.getQueryData<Song>(QUERY_KEYS.song(id));
          
          if (previousSong) {
            queryClient.setQueryData<Song>(
              QUERY_KEYS.song(id),
              { ...previousSong, ...metadata }
            );
          }
          
          return { previousSong };
        },
        onError: (_err, variables, context: unknown) => {
          const ctx = context as { previousSong?: Song } | undefined;
          if (ctx?.previousSong) {
            queryClient.setQueryData(
              QUERY_KEYS.song(variables.id),
              ctx.previousSong
            );
          }
        },
        onSettled: (_data, _error, variables) => {
          queryClient.invalidateQueries({ queryKey: QUERY_KEYS.song(variables.id) });
          queryClient.invalidateQueries({ queryKey: QUERY_KEYS.songs });
        },
        mutationFn: async (data) => {
          const { id, ...metadata } = data;
          const url = formatUrl('songs/:id/metadata/itunes', { id });
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
            throw new Error(errorData.error || `Failed to update iTunes metadata: ${response.status}`);
          }
          
          return response.json();
        },
      }
    );
  };

  /**
   * Update YouTube metadata for a song
   */
  const useUpdateYoutubeMetadata = () => {
    return useApiMutation<
      Song, 
      { 
        id: string;
        youtubeDuration?: number;
        youtubeThumbnailUrls?: {
          default?: string;
          medium?: string;
          high?: string;
          standard?: string;
          maxres?: string;
        };
        youtubeTags?: string[];
        youtubeCategories?: string[];
        youtubeChannelId?: string;
        youtubeChannelName?: string;
      }
    >(
      'songs/:id/metadata/youtube',
      'patch',
      {
        onMutate: async (variables) => {
          const { id, ...metadata } = variables;
          await queryClient.cancelQueries({ queryKey: QUERY_KEYS.song(id) });
          
          const previousSong = queryClient.getQueryData<Song>(QUERY_KEYS.song(id));
          
          if (previousSong) {
            queryClient.setQueryData<Song>(
              QUERY_KEYS.song(id),
              { ...previousSong, ...metadata }
            );
          }
          
          return { previousSong };
        },
        onError: (_err, variables, context: unknown) => {
          const ctx = context as { previousSong?: Song } | undefined;
          if (ctx?.previousSong) {
            queryClient.setQueryData(
              QUERY_KEYS.song(variables.id),
              ctx.previousSong
            );
          }
        },
        onSettled: (_data, _error, variables) => {
          queryClient.invalidateQueries({ queryKey: QUERY_KEYS.song(variables.id) });
          queryClient.invalidateQueries({ queryKey: QUERY_KEYS.songs });
        },
        mutationFn: async (data) => {
          const { id, ...metadata } = data;
          const url = formatUrl('songs/:id/metadata/youtube', { id });
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
            throw new Error(errorData.error || `Failed to update YouTube metadata: ${response.status}`);
          }
          
          return response.json();
        },
      }
    );
  };

  /**
   * Delete a song
   */
  const useDeleteSong = () => {
    return useApiMutation<
      void, 
      { id: string }
    >(
      'songs/:id',
      'delete',
      {
        onMutate: async (variables) => {
          await queryClient.cancelQueries({ queryKey: QUERY_KEYS.songs });
          
          // Save previous songs list
          const previousSongs = queryClient.getQueryData<Song[]>(QUERY_KEYS.songs);
          
          // Optimistically remove the song from the list
          if (previousSongs) {
            queryClient.setQueryData<Song[]>(
              QUERY_KEYS.songs,
              previousSongs.filter(song => song.id !== variables.id)
            );
          }
          
          return { previousSongs };
        },
        onError: (_err, _variables, context: unknown) => {
          // If the mutation fails, restore the previous songs list
          const ctx = context as { previousSongs?: Song[] } | undefined;
          if (ctx?.previousSongs) {
            queryClient.setQueryData(QUERY_KEYS.songs, ctx.previousSongs);
          }
        },
        onSuccess: (_data, variables) => {
          // Remove the specific song from cache
          queryClient.removeQueries({ queryKey: QUERY_KEYS.song(variables.id) });
        },
        onSettled: () => {
          // Refetch to ensure server state
          queryClient.invalidateQueries({ queryKey: QUERY_KEYS.songs });
        },
        mutationFn: async (data) => {
          const url = formatUrl('songs/:id', { id: data.id });
          const response = await fetch(`/api/${url}`, {
            method: 'DELETE',
            credentials: 'include',
          });
          
          if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `Failed to delete song: ${response.status}`);
          }
          
          return;
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
      { id: string; favorite: boolean }
    >(
      'songs/:id/favorite',
      'patch',
      {
        onMutate: async (variables) => {
          const { id, favorite } = variables;
          await queryClient.cancelQueries({ queryKey: QUERY_KEYS.song(id) });
          
          // Save previous song
          const previousSong = queryClient.getQueryData<Song>(QUERY_KEYS.song(id));
          
          // Optimistically update the song
          if (previousSong) {
            queryClient.setQueryData<Song>(
              QUERY_KEYS.song(id),
              { ...previousSong, favorite }
            );
            
            // Also update the song in the list of all songs
            const previousSongs = queryClient.getQueryData<Song[]>(QUERY_KEYS.songs);
            if (previousSongs) {
              queryClient.setQueryData<Song[]>(
                QUERY_KEYS.songs,
                previousSongs.map(song => 
                  song.id === id ? { ...song, favorite } : song
                )
              );
            }
          }
          
          return { previousSong };
        },
        onError: (_err, variables, context: unknown) => {
          const ctx = context as { previousSong?: Song } | undefined;
          if (ctx?.previousSong) {
            queryClient.setQueryData(
              QUERY_KEYS.song(variables.id),
              ctx.previousSong
            );
          }
        },
        onSettled: (_data, _error, variables) => {
          // Refetch to ensure server state
          queryClient.invalidateQueries({ queryKey: QUERY_KEYS.song(variables.id) });
          queryClient.invalidateQueries({ queryKey: QUERY_KEYS.songs });
        },
        mutationFn: async (data) => {
          const { id, favorite } = data;
          const url = formatUrl('songs/:id/favorite', { id });
          const response = await fetch(`/api/${url}`, {
            method: 'PATCH',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ favorite }),
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
   * Get rich metadata for a song (includes all iTunes/YouTube metadata)
   */
  const useRichSongMetadata = (id: string, options = {}) => {
    return useApiQuery<
      Song & {
        metadataQuality?: {
          hasItunes: boolean;
          hasYoutube: boolean;
          hasArtwork: boolean;
          hasThumbnails: boolean;
          completeness: number; // 0-100
        };
      },
      ReturnType<typeof QUERY_KEYS.song>
    >(
      QUERY_KEYS.song(id), 
      `songs/${id}?include_metadata=true`, 
      {
        enabled: !!id,
        ...options,
      }
    );
  };

  // ===== Utility Functions =====

  /**
   * Get the best available artwork URL for a song with priority fallbacks
   */
  const getArtworkUrl = useCallback((song: Song, size: 'small' | 'medium' | 'large' = 'medium'): string | null => {
    // Priority: Downloaded thumbnail > iTunes artwork > YouTube thumbnail URLs
    // This fixes the issue where new songs have coverArt pointing to non-existent files
    
    // First priority: Downloaded thumbnail (works for both old and new songs)
    if (song.thumbnail) {
      return `/api/songs/${song.id}/thumbnail`;
    }
    
    // Second priority: iTunes artwork URLs (external)
    if (song.itunesArtworkUrls) {
      switch (size) {
        case 'large':
          if (song.itunesArtworkUrls[600]) return song.itunesArtworkUrls[600];
          if (song.itunesArtworkUrls[100]) return song.itunesArtworkUrls[100];
          if (song.itunesArtworkUrls[60]) return song.itunesArtworkUrls[60];
          break;
        case 'medium':
          if (song.itunesArtworkUrls[100]) return song.itunesArtworkUrls[100];
          if (song.itunesArtworkUrls[600]) return song.itunesArtworkUrls[600];
          if (song.itunesArtworkUrls[60]) return song.itunesArtworkUrls[60];
          break;
        case 'small':
          if (song.itunesArtworkUrls[60]) return song.itunesArtworkUrls[60];
          if (song.itunesArtworkUrls[100]) return song.itunesArtworkUrls[100];
          if (song.itunesArtworkUrls[600]) return song.itunesArtworkUrls[600];
          break;
      }
    }
    
    // Third priority: YouTube thumbnail URLs (external)
    if (song.youtubeThumbnailUrls) {
      switch (size) {
        case 'large':
          if (song.youtubeThumbnailUrls.maxres) return song.youtubeThumbnailUrls.maxres;
          if (song.youtubeThumbnailUrls.standard) return song.youtubeThumbnailUrls.standard;
          if (song.youtubeThumbnailUrls.high) return song.youtubeThumbnailUrls.high;
          if (song.youtubeThumbnailUrls.medium) return song.youtubeThumbnailUrls.medium;
          if (song.youtubeThumbnailUrls.default) return song.youtubeThumbnailUrls.default;
          break;
        case 'medium':
          if (song.youtubeThumbnailUrls.high) return song.youtubeThumbnailUrls.high;
          if (song.youtubeThumbnailUrls.medium) return song.youtubeThumbnailUrls.medium;
          if (song.youtubeThumbnailUrls.standard) return song.youtubeThumbnailUrls.standard;
          if (song.youtubeThumbnailUrls.default) return song.youtubeThumbnailUrls.default;
          break;
        case 'small':
          if (song.youtubeThumbnailUrls.medium) return song.youtubeThumbnailUrls.medium;
          if (song.youtubeThumbnailUrls.default) return song.youtubeThumbnailUrls.default;
          if (song.youtubeThumbnailUrls.high) return song.youtubeThumbnailUrls.high;
          break;
      }
    }
    
    // Last resort: Try cover art path (but this probably won't work due to missing backend endpoint)
    if (song.coverArt) {
      // NOTE: This URL pattern doesn't exist in the backend - coverArt files aren't served
      // We should either add a backend endpoint or remove this fallback
      return `/api/songs/${song.id}/cover`;
    }
    
    return null;
  }, []);

  /**
   * Calculate metadata quality score for a song
   */
  const getMetadataQuality = useCallback((song: Song) => {
    let score = 0;
    let maxScore = 0;
    
    // Core metadata (always required)
    maxScore += 30;
    if (song.title) score += 10;
    if (song.artist) score += 10;
    if (song.album || song.releaseTitle) score += 10;
    
    // iTunes metadata
    maxScore += 25;
    if (song.itunesTrackId) score += 5;
    if (song.itunesArtworkUrls && Object.keys(song.itunesArtworkUrls).length > 0) score += 10;
    if (song.itunesPreviewUrl) score += 5;
    if (song.trackTimeMillis) score += 5;
    
    // YouTube metadata
    maxScore += 20;
    if (song.videoId) score += 5;
    if (song.youtubeThumbnailUrls && Object.keys(song.youtubeThumbnailUrls).length > 0) score += 5;
    if (song.youtubeTags && song.youtubeTags.length > 0) score += 5;
    if (song.youtubeChannelName) score += 5;
    
    // Additional metadata
    maxScore += 25;
    if (song.genre) score += 8;
    if (song.language) score += 7;
    if (song.lyrics || song.syncedLyrics) score += 10;
    
    return {
      score,
      maxScore,
      percentage: Math.round((score / maxScore) * 100),
      hasItunes: !!(song.itunesTrackId || song.itunesArtworkUrls),
      hasYoutube: !!(song.videoId || song.youtubeThumbnailUrls),
      hasArtwork: !!(song.itunesArtworkUrls || song.coverArt),
      hasThumbnails: !!(song.youtubeThumbnailUrls || song.thumbnail),
      hasLyrics: !!(song.lyrics || song.syncedLyrics),
    };
  }, []);

  /**
   * Get display name for album field with backwards compatibility
   */
  const getAlbumName = useCallback((song: Song): string => {
    return song.album || song.releaseTitle || 'Unknown Album';
  }, []);

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
    useRichSongMetadata,
    
    // Mutations
    useUpdateSong,
    useUpdateSongMetadata,
    useUpdateItunesMetadata,
    useUpdateYoutubeMetadata,
    useDeleteSong,
    useToggleFavorite,
    
    // Utility functions
    getAudioUrl,
    uploadSong,
    downloadVocals,
    downloadInstrumental,
    downloadOriginal,
    fetchAudioBuffer,
    getArtworkUrl,
    getMetadataQuality,
    getAlbumName,
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
