import { useEffect, useCallback, useMemo } from 'react';
import { useKaraokePlayerStore } from '@/stores/useKaraokePlayerStore';
import { useSongs } from '@/hooks/api/useSongs';
import { getSongDuration } from '@/utils/songUtils';
import type { 
  KaraokePlayerHook, 
  PlayerOptions, 
  PlayerError
} from '../KaraokePlayer.types';

export const useKaraokePlayer = (
  songId?: string, 
  options: PlayerOptions = {}
): KaraokePlayerHook => {
  const { autoPlay = false, preload = false } = options;
  
  // Store state and actions
  const {
    songId: currentSongId,
    connect,
    disconnect,
    connected,
    currentTime,
    isReady,
    isPlaying,
    duration,
    error: storeError,
    vocalVolume,
    instrumentalVolume,
    lyricsSize,
    lyricsOffset,
    cleanup,
    seek: storeSeek,
    setSongAndLoad,
    setVocalVolume,
    setInstrumentalVolume,
    setLyricsSize,
    setLyricsOffset,
    userPlay,
    userPause,
    getWaveformData,
  } = useKaraokePlayerStore();

  // Song data fetching
  const { useSong } = useSongs();
  const { 
    data: song, 
    isLoading,
    error: songError 
  } = useSong(songId ?? '');

  // Connection management
  useEffect(() => {
    connect();
    return () => {
      cleanup();
      disconnect();
    };
  }, [connect, disconnect, cleanup]);

  // Song loading and lifecycle management
  useEffect(() => {
    if (song && songId && songId !== currentSongId) {
      const duration = getSongDuration(song);
      setSongAndLoad(song.id, duration);
    }
    return () => cleanup();
  }, [song, songId, currentSongId, setSongAndLoad, cleanup]);

  // Auto-play functionality
  useEffect(() => {
    if (autoPlay && isReady && !isPlaying && song) {
      userPlay();
    }
  }, [autoPlay, isReady, isPlaying, song, userPlay]);

  // Preload functionality
  const preloadSong = useCallback(async (preloadSongId: string) => {
    // Implementation for preloading songs
    // This would involve fetching song data and potentially preparing audio
    console.log('Preloading song:', preloadSongId);
    // TODO: Implement actual preloading logic
  }, []);

  // Preload effect
  useEffect(() => {
    if (preload && songId) {
      preloadSong(songId);
    }
  }, [preload, songId, preloadSong]);

  // Player controls
  const play = useCallback(() => {
    if (isReady) {
      userPlay();
    }
  }, [isReady, userPlay]);

  const pause = useCallback(() => {
    if (isReady) {
      userPause();
    }
  }, [isReady, userPause]);

  const togglePlay = useCallback(() => {
    if (!isReady) return;
    if (isPlaying) {
      pause();
    } else {
      play();
    }
  }, [isReady, isPlaying, play, pause]);

  const seek = useCallback((timeSeconds: number) => {
    if (isReady) {
      // Store now expects seconds
      storeSeek(timeSeconds);
    }
  }, [isReady, storeSeek]);

  // Reload functionality
  const reload = useCallback(async () => {
    if (song) {
      cleanup();
      const duration = getSongDuration(song);
      await setSongAndLoad(song.id, duration);
    }
  }, [song, cleanup, setSongAndLoad]);

  // Error handling
  const error: PlayerError | null = useMemo(() => {
    if (storeError) {
      return {
        code: 'PLAYER_ERROR',
        message: storeError,
      };
    }
    if (songError) {
      return {
        code: 'SONG_ERROR',
        message: songError instanceof Error ? songError.message : 'Failed to load song',
        details: songError,
      };
    }
    return null;
  }, [storeError, songError]);

  // Lyrics processing
  const lyrics = useMemo(() => {
    if (!song) return '';
    return song.syncedLyrics || song.plainLyrics || '';
  }, [song]);

  const isLyricsSync = useMemo(() => {
    return !!(song?.syncedLyrics);
  }, [song]);

  // Connection status
  const connectionStatus = useMemo(() => {
    if (connected) return 'connected';
    return 'disconnected'; // TODO: Add 'connecting' state detection
  }, [connected]) as 'connected' | 'disconnected' | 'connecting';

  // Waveform data
  const waveformData = useMemo(() => {
    return getWaveformData();
  }, [getWaveformData]);

  // Duration in seconds (consistent with new interface)
  const durationSeconds = useMemo(() => {
    return song ? getSongDuration(song) : duration;
  }, [song, duration]);

  // Current time in seconds (consistent with new interface)
  const currentTimeSeconds = useMemo(() => {
    return currentTime;
  }, [currentTime]);

  return {
    // State
    song: song || null,
    isLoading,
    isReady,
    isPlaying,
    currentTime: currentTimeSeconds,
    duration: durationSeconds,
    error,
    connectionStatus,
    
    // Playback controls
    play,
    pause,
    togglePlay,
    seek,
    
    // Audio controls
    setVocalVolume,
    setInstrumentalVolume,
    vocalVolume,
    instrumentalVolume,
    
    // Lyrics and display
    lyrics,
    isLyricsSync,
    lyricsSize,
    lyricsOffset,
    setLyricsSize,
    setLyricsOffset,
    
    // Visualizer
    waveformData,
    
    // Advanced
    reload,
    preload: preloadSong,
  };
};