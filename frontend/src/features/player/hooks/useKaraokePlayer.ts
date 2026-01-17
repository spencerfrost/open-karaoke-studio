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
    songEnded,
    duration,
    error: storeError,
    isLoading: isAudioLoading,
    vocalVolume,
    instrumentalVolume,
    lyricsSize,
    lyricsOffset,
    cleanup,
    seek: storeSeek,
    setSongAndLoad,
    load,
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
    isLoading: isMetadataLoading,
    error: songError 
  } = useSong(songId ?? '');

  // Combined loading state: either fetching metadata OR downloading/decoding audio
  const isLoading = isMetadataLoading || isAudioLoading;

  // Connection management
  // Note: We do NOT cleanup on unmount - audio state persists in Zustand store
  // for mini-player functionality. Cleanup only happens when loading a new song.
  useEffect(() => {
    connect();
    return () => {
      // Don't cleanup or disconnect - let the audio continue for mini-player
      // The store state persists and mini-player can control playback
    };
  }, [connect]);

  // Song loading and lifecycle management
  // Note: We only cleanup when loading a DIFFERENT song, not on unmount
  useEffect(() => {
    if (song && songId && songId !== currentSongId) {
      const duration = getSongDuration(song);
      // Pass song metadata for mini-player display
      setSongAndLoad(song.id, duration, song.title, song.artist);
    } else if (
      // If the store already has this songId but audio wasn't loaded yet,
      // trigger a load to avoid getting stuck with disabled controls.
      song &&
      songId &&
      songId === currentSongId &&
      !isReady &&
      !isAudioLoading
    ) {
      // Fire and forget; store will update isReady/isLoading accordingly.
      void load();
    }
    // Don't cleanup on unmount - mini-player needs the audio to keep playing
  }, [song, songId, currentSongId, setSongAndLoad, isReady, isAudioLoading, load]);

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

  // Replay from the beginning
  const replay = useCallback(() => {
    if (isReady) {
      storeSeek(0);
      userPlay();
    }
  }, [isReady, storeSeek, userPlay]);

  // Reload functionality
  const reload = useCallback(async () => {
    if (song) {
      cleanup();
      const duration = getSongDuration(song);
      await setSongAndLoad(song.id, duration, song.title, song.artist);
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

  return {
    // State
    song: song || null,
    isLoading,
    isReady,
    isPlaying,
    songEnded,
    currentTime: currentTime, // Pass in seconds
    duration: durationSeconds,
    error,
    connectionStatus,
    
    // Playback controls
    play,
    pause,
    togglePlay,
    seek,
    replay,
    
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