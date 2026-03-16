/**
 * Karaoke Player Store - Facade Integration Layer
 *
 * This is a facade that integrates three focused stores:
 * - useAudioControlsStore: Volume and speed controls
 * - usePlaybackStateStore: Playback timing and Web Audio API
 * - useUIPreferencesStore: Display preferences and mini-player
 *
 * It provides a unified API for components (backward-compatible)
 * and handles WebSocket synchronization across all sub-stores.
 */

import { create } from "zustand";
import { sessionWebSocketService } from "../services/sessionWebSocketService";
import { createLogger } from "@/lib/logger";
import { useAudioControlsStore } from "./useAudioControlsStore";
import { usePlaybackStateStore } from "./usePlaybackStateStore";
import { useUIPreferencesStore } from "./useUIPreferencesStore";
import {
  PerformanceState,
  MiniPlayerPosition,
  LocalUpdateTracker,
  ControlValue,
} from "./shared/types";
import {
  shouldIgnoreWebSocketUpdate as shouldIgnore,
  trackLocalUpdate,
  clearLocalUpdates,
  toSnakeCase,
} from "./shared/websocketSync";

const logger = createLogger("store:player");

// Extend window interface for cleanup storage
declare global {
  interface Window {
    __playerWebSocketCleanup?: (() => void)[];
  }
}

interface KaraokePlayerState {
  // Audio/track info (from playbackState)
  songId: string | null;
  instrumentalUrl: string;
  vocalUrl: string;
  backingVocalUrl: string;
  isReady: boolean;
  isLoading: boolean;
  duration: number;
  error: string | null;

  // Song metadata for display (from uiPreferences)
  songTitle: string | null;
  songArtist: string | null;

  // Playback state (from playbackState)
  isPlaying: boolean;
  currentTime: number;
  songEnded: boolean;

  // Controls (from audioControls)
  vocalVolume: number;
  backingVocalVolume: number;
  instrumentalVolume: number;
  playbackSpeed: number;

  // UI preferences (from uiPreferences)
  lyricsSize: "small" | "medium" | "large";
  lyricsOffset: number;
  autoScrollEnabled: boolean;
  showChords: boolean;

  // Connection state
  connected: boolean;

  // Mini-player state (from uiPreferences)
  miniPlayerEnabled: boolean;
  miniPlayerPosition: MiniPlayerPosition;
  miniPlayerDismissed: boolean;

  // Actions
  connect: () => void;
  disconnect: () => void;
  setSongId: (id: string, duration?: number, gainDb?: number) => void;
  setSongAndLoad: (
    id: string,
    duration?: number,
    title?: string,
    artist?: string,
    gainDb?: number,
  ) => Promise<void>;
  load: () => Promise<void>;
  play: () => void;
  pause: () => void;
  userPlay: () => void;
  userPause: () => void;
  seek: (time: number) => void;
  resetSongEnded: () => void;
  setVocalVolume: (volume: number) => void;
  setBackingVocalVolume: (volume: number) => void;
  setInstrumentalVolume: (volume: number) => void;
  setLyricsSize: (size: "small" | "medium" | "large") => void;
  setLyricsOffset: (offset: number) => void;
  setAutoScrollEnabled: (enabled: boolean) => void;
  setShowChords: (enabled: boolean) => void;
  setPlaybackSpeed: (speed: number) => void;
  cleanup: () => void;
  getWaveformData: () => number[] | null;
  setMiniPlayerEnabled: (enabled: boolean) => void;
  setMiniPlayerPosition: (position: MiniPlayerPosition) => void;
  dismissMiniPlayer: () => void;
  updateFromWebSocket: (data: Partial<PerformanceState>) => void;
}

export const useKaraokePlayerStore = create<KaraokePlayerState>((set, get) => {
  // Track local updates to prevent WebSocket echoes
  const lastLocalUpdate: LocalUpdateTracker = {};

  // Flag to prevent WebSocket interference during song loading
  let isLoadingNewSong: boolean = false;

  function socketEmit(messageType: string, data?: Record<string, unknown>) {
    if (messageType === "update_performance_control") {
      sessionWebSocketService.updatePerformanceControl(
        (data?.control as string) || "",
        data?.value as ControlValue,
      );
    } else if (messageType === "update_player_state") {
      sessionWebSocketService.updatePlayerState({
        isPlaying: data?.isPlaying as boolean,
        currentTime: data?.currentTime as number,
        duration: data?.duration as number,
      });
    } else if (messageType === "playback_play") {
      sessionWebSocketService.playback();
    } else if (messageType === "playback_pause") {
      sessionWebSocketService.pause();
    } else if (messageType === "song_loaded") {
      sessionWebSocketService.songLoaded(
        (data?.songId as string) || "",
        (data?.duration as number) || 0,
      );
    } else if (messageType === "song_ready") {
      sessionWebSocketService.songReady(
        (data?.songId as string) || "",
        (data?.duration as number) || 0,
      );
    }
  }

  function updatePerformanceControl(control: string, value: unknown) {
    const backendControl = toSnakeCase(control);
    trackLocalUpdate(lastLocalUpdate, backendControl, value);
    logger.debug(
      "Sending performance control update:",
      backendControl,
      "=",
      value,
    );
    socketEmit("update_performance_control", {
      control: backendControl,
      value,
    });
  }

  function updatePlayerState(
    updates: Partial<
      Pick<KaraokePlayerState, "isPlaying" | "currentTime" | "duration">
    >,
  ) {
    if (updates.currentTime !== undefined) {
      trackLocalUpdate(lastLocalUpdate, "current_time", updates.currentTime);
    }
    socketEmit("update_player_state", updates);
  }

  // Subscribe to child store changes
  useAudioControlsStore.subscribe((state) => {
    set({
      vocalVolume: state.vocalVolume,
      backingVocalVolume: state.backingVocalVolume,
      instrumentalVolume: state.instrumentalVolume,
      playbackSpeed: state.playbackSpeed,
    });
  });

  usePlaybackStateStore.subscribe((state) => {
    set({
      songId: state.songId,
      instrumentalUrl: state.instrumentalUrl,
      vocalUrl: state.vocalUrl,
      backingVocalUrl: state.backingVocalUrl,
      isReady: state.isReady,
      isLoading: state.isLoading,
      duration: state.duration,
      error: state.error,
      isPlaying: state.isPlaying,
      currentTime: state.currentTime,
      songEnded: state.songEnded,
    });
  });

  useUIPreferencesStore.subscribe((state) => {
    set({
      lyricsSize: state.lyricsSize,
      lyricsOffset: state.lyricsOffset,
      autoScrollEnabled: state.autoScrollEnabled,
      showChords: state.showChords,
      songTitle: state.songTitle,
      songArtist: state.songArtist,
      miniPlayerEnabled: state.miniPlayerEnabled,
      miniPlayerPosition: state.miniPlayerPosition,
      miniPlayerDismissed: state.miniPlayerDismissed,
    });
  });

  return {
    // Initial state - aggregated from child stores
    songId: null,
    instrumentalUrl: "",
    vocalUrl: "",
    backingVocalUrl: "",
    isReady: false,
    isLoading: false,
    duration: 0,
    error: null,
    songTitle: null,
    songArtist: null,
    isPlaying: false,
    currentTime: 0,
    songEnded: false,
    vocalVolume: 0,
    backingVocalVolume: 1.0,
    instrumentalVolume: 1.0,
    playbackSpeed: 1.0,
    lyricsSize: "medium",
    lyricsOffset: 0,
    autoScrollEnabled: true,
    showChords: false,
    connected: false,
    miniPlayerEnabled: true,
    miniPlayerPosition: { x: 24, y: 24 },
    miniPlayerDismissed: false,

    connect: () => {
      logger.debug("[KaraokePlayerStore] Setting up WebSocket listeners");

      const cleanupPerformanceState = sessionWebSocketService.on(
        "performance_state",
        (data) => {
          if (data && typeof data === "object" && "state" in data) {
            const state = (data as { state: PerformanceState }).state;
            get().updateFromWebSocket(state);
          }
        },
      );

      const cleanupControlUpdated = sessionWebSocketService.on(
        "control_updated",
        (data) => {
          if (
            data &&
            typeof data === "object" &&
            "control" in data &&
            "value" in data
          ) {
            const { control, value } = data as {
              control: string;
              value: unknown;
            };
            get().updateFromWebSocket({
              [control]: value,
            } as Partial<PerformanceState>);
          }
        },
      );

      const cleanupPlaybackPlay = sessionWebSocketService.on(
        "playback_play",
        () => {
          get().play();
        },
      );

      const cleanupPlaybackPause = sessionWebSocketService.on(
        "playback_pause",
        () => {
          get().pause();
        },
      );

      const cleanupSessionConnected = sessionWebSocketService.on(
        "session_connected",
        (data) => {
          logger.debug(
            "[KaraokePlayerStore] Received session_connected event",
            data,
          );
          set({ connected: true });
        },
      );

      const cleanupSessionError = sessionWebSocketService.on(
        "session_error",
        (data) => {
          logger.error("[KaraokePlayerStore] Session error:", data);
          set({ connected: false });
        },
      );

      const cleanupSessionEnded = sessionWebSocketService.on(
        "session_ended",
        (data) => {
          logger.debug("[KaraokePlayerStore] Session ended:", data);
          set({ connected: false });
        },
      );

      window.__playerWebSocketCleanup = [
        cleanupPerformanceState,
        cleanupControlUpdated,
        cleanupPlaybackPlay,
        cleanupPlaybackPause,
        cleanupSessionConnected,
        cleanupSessionError,
        cleanupSessionEnded,
      ];

      if (sessionWebSocketService.isConnectionActive()) {
        logger.debug("[KaraokePlayerStore] WebSocket already connected");
        set({ connected: true });
      }
    },

    disconnect: () => {
      if (window.__playerWebSocketCleanup) {
        window.__playerWebSocketCleanup.forEach((cleanup: () => void) =>
          cleanup(),
        );
        delete window.__playerWebSocketCleanup;
      }
      set({ connected: false });
    },

    setSongId: (id: string, duration?: number, gainDb?: number) => {
      usePlaybackStateStore.getState().setSongId(id, duration, gainDb);
      useUIPreferencesStore.getState().resetMiniPlayerDismissed();
    },

    setSongAndLoad: async (
      id: string,
      duration?: number,
      title?: string,
      artist?: string,
      gainDb?: number,
    ) => {
      isLoadingNewSong = true;

      get().cleanup();
      get().setSongId(id, duration, gainDb);
      useUIPreferencesStore
        .getState()
        .setSongMetadata(title || null, artist || null);
      usePlaybackStateStore.getState().resetSongEnded();

      socketEmit("song_loaded", {
        songId: id,
        duration: duration || 0,
        currentTime: 0,
        isPlaying: false,
      });

      await get().load();

      setTimeout(() => {
        isLoadingNewSong = false;
        clearLocalUpdates(lastLocalUpdate);
        logger.debug("Re-enabled WebSocket performance state updates");
      }, 500);
    },

    load: async () => {
      await usePlaybackStateStore.getState().load();
      const duration = usePlaybackStateStore.getState().duration;
      socketEmit("song_ready", {
        songId: get().songId,
        duration,
        currentTime: 0,
        isPlaying: false,
        isReady: true,
      });
    },

    play: () => {
      const audioControls = useAudioControlsStore.getState();
      const playbackState = usePlaybackStateStore.getState();

      playbackState.play(audioControls.playbackSpeed, {
        vocal: audioControls.vocalVolume,
        backing: audioControls.backingVocalVolume,
        instrumental: audioControls.instrumentalVolume,
      });

      playbackState.startTimeUpdate(audioControls.playbackSpeed, (state) => {
        updatePlayerState(state);
      });

      updatePlayerState({ isPlaying: true });
    },

    pause: () => {
      const audioControls = useAudioControlsStore.getState();
      const playbackState = usePlaybackStateStore.getState();

      playbackState.pause(audioControls.playbackSpeed);
      playbackState.stopTimeUpdate();
      updatePlayerState({
        currentTime: playbackState.currentTime,
        isPlaying: false,
      });
    },

    userPlay: () => {
      socketEmit("playback_play", {});
      get().play();
    },

    userPause: () => {
      socketEmit("playback_pause", {});
      get().pause();
    },

    seek: (timeSeconds: number) => {
      const audioControls = useAudioControlsStore.getState();
      const playbackState = usePlaybackStateStore.getState();

      playbackState.seek(timeSeconds, audioControls.playbackSpeed, {
        vocal: audioControls.vocalVolume,
        backing: audioControls.backingVocalVolume,
        instrumental: audioControls.instrumentalVolume,
      });

      if (playbackState.isPlaying) {
        playbackState.startTimeUpdate(audioControls.playbackSpeed, (state) => {
          updatePlayerState(state);
        });
      }

      updatePlayerState({ currentTime: timeSeconds });
    },

    resetSongEnded: () => {
      usePlaybackStateStore.getState().resetSongEnded();
    },

    setVocalVolume: (volume: number) => {
      useAudioControlsStore.getState().setVocalVolume(volume);
      updatePerformanceControl("vocalVolume", volume);
    },

    setBackingVocalVolume: (volume: number) => {
      useAudioControlsStore.getState().setBackingVocalVolume(volume);
      updatePerformanceControl("backingVocalVolume", volume);
    },

    setInstrumentalVolume: (volume: number) => {
      useAudioControlsStore.getState().setInstrumentalVolume(volume);
      updatePerformanceControl("instrumentalVolume", volume);
    },

    setLyricsSize: (size: "small" | "medium" | "large") => {
      useUIPreferencesStore.getState().setLyricsSize(size);
      updatePerformanceControl("lyricsSize", size);
    },

    setLyricsOffset: (offset: number) => {
      useUIPreferencesStore.getState().setLyricsOffset(offset);
      updatePerformanceControl("lyricsOffset", offset);
    },

    setAutoScrollEnabled: (enabled: boolean) => {
      useUIPreferencesStore.getState().setAutoScrollEnabled(enabled);
    },

    setShowChords: (enabled: boolean) => {
      useUIPreferencesStore.getState().setShowChords(enabled);
    },

    setPlaybackSpeed: (speed: number) => {
      useAudioControlsStore.getState().setPlaybackSpeed(speed);
      trackLocalUpdate(lastLocalUpdate, "playback_speed", speed);
      socketEmit("update_performance_control", {
        control: "playback_speed",
        value: speed,
      });
    },

    cleanup: () => {
      usePlaybackStateStore.getState().cleanup();
      usePlaybackStateStore.getState().stopTimeUpdate();
      clearLocalUpdates(lastLocalUpdate);
    },

    getWaveformData: () => {
      return usePlaybackStateStore.getState().getWaveformData();
    },

    setMiniPlayerEnabled: (enabled: boolean) => {
      useUIPreferencesStore.getState().setMiniPlayerEnabled(enabled);
    },

    setMiniPlayerPosition: (position: MiniPlayerPosition) => {
      useUIPreferencesStore.getState().setMiniPlayerPosition(position);
    },

    dismissMiniPlayer: () => {
      useUIPreferencesStore.getState().dismissMiniPlayer();
    },

    updateFromWebSocket: (data: Partial<PerformanceState>) => {
      if (isLoadingNewSong) {
        logger.debug("Ignoring WebSocket update during song loading");
        return;
      }

      const audioControls = useAudioControlsStore.getState();
      const uiPreferences = useUIPreferencesStore.getState();

      // Handle audio controls
      if (
        data.vocal_volume !== undefined &&
        !shouldIgnore(lastLocalUpdate, "vocal_volume", data.vocal_volume)
      ) {
        audioControls.setVocalVolume(data.vocal_volume);
      }
      if (
        data.backing_vocal_volume !== undefined &&
        !shouldIgnore(
          lastLocalUpdate,
          "backing_vocal_volume",
          data.backing_vocal_volume,
        )
      ) {
        audioControls.setBackingVocalVolume(data.backing_vocal_volume);
      }
      if (
        data.instrumental_volume !== undefined &&
        !shouldIgnore(
          lastLocalUpdate,
          "instrumental_volume",
          data.instrumental_volume,
        )
      ) {
        audioControls.setInstrumentalVolume(data.instrumental_volume);
      }
      if (
        data.playback_speed !== undefined &&
        !shouldIgnore(lastLocalUpdate, "playback_speed", data.playback_speed)
      ) {
        audioControls.setPlaybackSpeed(data.playback_speed);
      }

      // Handle UI preferences
      if (
        data.lyrics_size !== undefined &&
        !shouldIgnore(lastLocalUpdate, "lyrics_size", data.lyrics_size)
      ) {
        uiPreferences.setLyricsSize(data.lyrics_size);
      }
      if (
        data.lyrics_offset !== undefined &&
        !shouldIgnore(lastLocalUpdate, "lyrics_offset", data.lyrics_offset)
      ) {
        uiPreferences.setLyricsOffset(data.lyrics_offset);
      }

      // Handle playback state
      if (data.is_playing !== undefined) {
        set({ isPlaying: data.is_playing });
      }
      if (
        data.current_time !== undefined &&
        !shouldIgnore(lastLocalUpdate, "current_time", data.current_time)
      ) {
        set({ currentTime: data.current_time });
      }
      if (data.duration !== undefined) {
        set({ duration: data.duration });
      }
    },
  };
});
