import { create } from "zustand";
import { sessionWebSocketService } from "../services/sessionWebSocketService";

// Extend window interface for cleanup storage
declare global {
  interface Window {
    __playerWebSocketCleanup?: (() => void)[];
  }
}

// Import types from sessionWebSocketService
type ControlValue = number | string | boolean;

interface PerformanceState {
  vocal_volume: number;
  instrumental_volume: number;
  lyrics_size: "small" | "medium" | "large";
  lyrics_offset: number;
  current_time: number;
  duration: number;
  is_playing: boolean;
  current_song_id?: string | null;
  is_ready?: boolean;
}

// Mini-player position interface
interface MiniPlayerPosition {
  x: number;
  y: number;
}

interface KaraokePlayerState {
  // Audio/track info
  songId: string | null;
  instrumentalUrl: string;
  vocalUrl: string;
  isReady: boolean;
  isLoading: boolean;
  duration: number; // seconds (float) - canonical unit
  error: string | null;

  // Song metadata for display
  songTitle: string | null;
  songArtist: string | null;

  // Playback state
  isPlaying: boolean;
  currentTime: number;
  songEnded: boolean; // True when song has finished playing (not just paused)

  // Controls
  vocalVolume: number;
  instrumentalVolume: number;
  lyricsSize: "small" | "medium" | "large";
  lyricsOffset: number;
  autoScrollEnabled: boolean;

  // Connection state (managed by unified service)
  connected: boolean;

  // Mini-player state
  miniPlayerEnabled: boolean;
  miniPlayerPosition: MiniPlayerPosition;
  miniPlayerDismissed: boolean; // User explicitly closed it for current song

  // Actions
  connect: () => void;
  disconnect: () => void;
  setSongId: (id: string, duration?: number) => void;
  setSongAndLoad: (id: string, duration?: number, title?: string, artist?: string) => Promise<void>;
  load: () => Promise<void>;
  play: () => void;
  pause: () => void;
  userPlay: () => void;
  userPause: () => void;
  seek: (time: number) => void;
  resetSongEnded: () => void;
  setVocalVolume: (volume: number) => void;
  setInstrumentalVolume: (volume: number) => void;
  setLyricsSize: (size: "small" | "medium" | "large") => void;
  setLyricsOffset: (offset: number) => void;
  setAutoScrollEnabled: (enabled: boolean) => void;
  cleanup: () => void;
  getWaveformData: () => number[] | null;
  // Mini-player actions
  setMiniPlayerEnabled: (enabled: boolean) => void;
  setMiniPlayerPosition: (position: MiniPlayerPosition) => void;
  dismissMiniPlayer: () => void;
  // Method to update from WebSocket
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  updateFromWebSocket: (data: any) => void;
}

export const useKaraokePlayerStore = create<KaraokePlayerState>((set, get) => {
  // --- Web Audio API internals (not exposed to UI) ---
  let audioContext: AudioContext | null = null;
  let instrumentalBuffer: AudioBuffer | null = null;
  let vocalBuffer: AudioBuffer | null = null;
  let instrumentalSource: AudioBufferSourceNode | null = null;
  let vocalSource: AudioBufferSourceNode | null = null;
  let instrumentalGain: GainNode | null = null;
  let vocalGain: GainNode | null = null;
  let analyser: AnalyserNode | null = null;
  let animationFrameId: number | null = null;
  let websocketInterval: NodeJS.Timeout | null = null;

  let playbackStartTime: number | null = null; // audioContext.currentTime when playback started
  let playbackOffset: number = 0; // seconds into the track when playback started

  // Add a variable to store song duration in seconds
  let songDuration: number | undefined = undefined;

  // Flag to prevent WebSocket interference during song loading
  let isLoadingNewSong: boolean = false;

  // Track local updates to prevent WebSocket echoes
  const lastLocalUpdate: { [key: string]: { value: unknown; timestamp: number } } = {};
  const LOCAL_UPDATE_DEBOUNCE_MS = 1000; // Ignore WebSocket updates for 1 second after local change

  // --- Audio graph helpers ---
  function setupAnalyser() {
    if (!analyser && audioContext) {
      analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
    }
  }

  function syncGainValues() {
    if (vocalGain) vocalGain.gain.value = get().vocalVolume;
    if (instrumentalGain)
      instrumentalGain.gain.value = get().instrumentalVolume;
  }

  function clearIntervals() {
    if (animationFrameId) cancelAnimationFrame(animationFrameId);
    if (websocketInterval) clearInterval(websocketInterval);
    animationFrameId = null;
    websocketInterval = null;
  }

  function socketEmit(messageType: string, data?: Record<string, unknown>) {
    // Use the appropriate public method based on message type
    if (messageType === "update_performance_control") {
      sessionWebSocketService.updatePerformanceControl(
        (data?.control as string) || "",
        data?.value as ControlValue
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
        (data?.duration as number) || 0
      );
    } else if (messageType === "song_ready") {
      sessionWebSocketService.songReady(
        (data?.songId as string) || "",
        (data?.duration as number) || 0
      );
    }
  }

  function setupAudioGraph(startTime: number, offset?: number) {
    // Clean up any previous sources
    if (instrumentalSource) instrumentalSource.stop();
    if (vocalSource) vocalSource.stop();
    if (!audioContext || !instrumentalBuffer || !vocalBuffer) return;
    // Create new sources and connect them to the audio graph
    instrumentalSource = audioContext.createBufferSource();
    instrumentalSource.buffer = instrumentalBuffer;
    vocalSource = audioContext.createBufferSource();
    vocalSource.buffer = vocalBuffer;
    // Create gain nodes for volume control
    instrumentalGain = audioContext.createGain();
    instrumentalGain.gain.value = get().instrumentalVolume;
    vocalGain = audioContext.createGain();
    vocalGain.gain.value = get().vocalVolume;
    // Create or reuse the analyser node
    setupAnalyser();
    // Connect the graph
    instrumentalSource.connect(instrumentalGain).connect(analyser!);
    vocalSource.connect(vocalGain).connect(analyser!);
    analyser!.connect(audioContext.destination);
    
    // Handle playback end - use instrumental track as the reference
    // Only trigger once when playback naturally ends (not when stopped manually)
    instrumentalSource.onended = () => {
      // Check if we're still playing (wasn't manually stopped)
      const { isPlaying, duration } = get();
      if (isPlaying && playbackStartTime !== null && audioContext) {
        const currentTime = playbackOffset + (audioContext.currentTime - playbackStartTime);
        // Only auto-stop if we're near or past the end of the song
        if (currentTime >= duration - 0.5) {
          clearIntervals();
          playbackStartTime = null;
          playbackOffset = duration; // Set to exact duration
          set({ currentTime: duration, isPlaying: false, songEnded: true });
          socketEmit("update_player_state", {
            isPlaying: false,
            currentTime: duration,
            duration,
          });
        }
      }
    };
    
    // Start the sources in sync
    if (typeof offset === "number") {
      instrumentalSource.start(startTime, offset);
      vocalSource.start(startTime, offset);
    } else {
      instrumentalSource.start(startTime);
      vocalSource.start(startTime);
    }
    // Set the playback start time
    syncGainValues();
  }

  function resetAudioNodes() {
    if (instrumentalSource) instrumentalSource.stop();
    if (vocalSource) vocalSource.stop();
    if (audioContext) audioContext.close();
    audioContext = null;
    instrumentalBuffer = null;
    vocalBuffer = null;
    instrumentalSource = null;
    vocalSource = null;
    instrumentalGain = null;
    vocalGain = null;
    analyser = null;
    clearIntervals();
    playbackStartTime = null;
    playbackOffset = 0;
  }

  function startTimeUpdate() {
    // Cancel any existing animation frame and websocket interval
    if (animationFrameId) cancelAnimationFrame(animationFrameId);
    if (websocketInterval) clearInterval(websocketInterval);
    if (!audioContext) return;

    // High-frequency currentTime updates using requestAnimationFrame (~60Hz)
    const updateCurrentTime = () => {
      const { isReady, isPlaying } = get();
      if (!isReady || !isPlaying) {
        animationFrameId = null;
        return;
      }

      let currentTime = playbackOffset;
      if (isPlaying && playbackStartTime !== null && audioContext) {
        currentTime =
          playbackOffset + (audioContext.currentTime - playbackStartTime);
      }
      set({ currentTime });

      // Continue animation loop
      animationFrameId = requestAnimationFrame(updateCurrentTime);
    };

    // Start the animation frame loop
    animationFrameId = requestAnimationFrame(updateCurrentTime);

    // Separate low-frequency WebSocket broadcasts (300ms interval)
    websocketInterval = setInterval(() => {
      const { isReady, isPlaying, currentTime, duration } = get();
      if (isReady && isPlaying && audioContext) {
        socketEmit("update_player_state", {
          isPlaying: true,
          currentTime,
          duration,
        });
      }
    }, 300);
  }

  // --- Synced state update helpers ---
  function updatePlayerState(
    updates: Partial<
      Pick<
        KaraokePlayerState,
        | "isPlaying"
        | "currentTime"
        | "duration"
        | "songId"
        | "isReady"
        | "isLoading"
        | "error"
      >
    >,
  ) {
    // Track currentTime updates to prevent seek flickering
    if (updates.currentTime !== undefined) {
      lastLocalUpdate["current_time"] = {
        value: updates.currentTime,
        timestamp: Date.now(),
      };
    }

    set(updates);
    socketEmit("update_player_state", updates);
  }

  function updatePerformanceControl(
    control:
      | "vocalVolume"
      | "instrumentalVolume"
      | "lyricsSize"
      | "lyricsOffset",
    value: unknown,
  ) {
    // Track this as a local update to prevent WebSocket echo
    const backendControl = control.replace(
      /[A-Z]/g,
      (letter) => "_" + letter.toLowerCase(),
    );
    lastLocalUpdate[backendControl] = {
      value,
      timestamp: Date.now(),
    };

    console.log('Sending performance control update:', backendControl, '=', value);
    set({ [control]: value });

    socketEmit("update_performance_control", {
      control: backendControl,
      value,
    });
  }

  // Helper to check if a WebSocket update should be ignored
  function shouldIgnoreWebSocketUpdate(control: string, value: unknown): boolean {
    const localUpdate = lastLocalUpdate[control];
    if (!localUpdate) return false;

    const timeSinceLocalUpdate = Date.now() - localUpdate.timestamp;
    const isWithinDebounceWindow = timeSinceLocalUpdate < LOCAL_UPDATE_DEBOUNCE_MS;

    // For currentTime, allow small differences due to precision/timing
    if (control === "current_time" && typeof value === "number" && typeof localUpdate.value === "number") {
      const timeDifference = Math.abs(value - localUpdate.value);
      const isSimilarTime = timeDifference < 0.5; // Within 0.5 seconds
      return isSimilarTime && isWithinDebounceWindow;
    }

    // For other controls, require exact value match
    const isSameValue = localUpdate.value === value;
    return isSameValue && isWithinDebounceWindow;
  }

  return {
    songId: null,
    instrumentalUrl: "",
    vocalUrl: "",
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
    instrumentalVolume: 1.0,
    lyricsSize: "medium",
    lyricsOffset: 0,
    autoScrollEnabled: true,
    connected: false,
    miniPlayerEnabled: true,
    miniPlayerPosition: { x: 24, y: 24 }, // Bottom-right with 24px margin
    miniPlayerDismissed: false,

    // Actions
    connect: () => {
      // Don't set connected immediately - wait for session_connected event
      // This prevents showing connected state before WebSocket is actually ready
      console.log('[KaraokePlayerStore] Setting up WebSocket listeners');

      // Set up listeners for performance events
      const cleanupPerformanceState = sessionWebSocketService.on("performance_state", (data) => {
        if (data && typeof data === 'object' && 'state' in data) {
          const state = (data as { state: PerformanceState }).state;
          get().updateFromWebSocket(state);
        }
      });

      const cleanupControlUpdated = sessionWebSocketService.on("control_updated", (data) => {
        if (data && typeof data === 'object' && 'control' in data && 'value' in data) {
          const { control, value } = data as { control: string; value: unknown };
          get().updateFromWebSocket({ [control]: value });
        }
      });

      const cleanupPlaybackPlay = sessionWebSocketService.on("playback_play", () => {
        get().play();
      });

      const cleanupPlaybackPause = sessionWebSocketService.on("playback_pause", () => {
        get().pause();
      });

      // Add listener for session connection status - this is THE signal that we're ready
      const cleanupSessionConnected = sessionWebSocketService.on("session_connected", (data) => {
        console.log('[KaraokePlayerStore] Received session_connected event', data);
        set({ connected: true });
      });

      // Also listen for session_error to handle connection failures
      const cleanupSessionError = sessionWebSocketService.on("session_error", (data) => {
        console.error('[KaraokePlayerStore] Session error:', data);
        set({ connected: false });
      });

      // Listen for session_ended to clean up when session terminates
      const cleanupSessionEnded = sessionWebSocketService.on("session_ended", (data) => {
        console.log('[KaraokePlayerStore] Session ended:', data);
        set({ connected: false });
      });

      // Store cleanup functions for later
      window.__playerWebSocketCleanup = [
        cleanupPerformanceState,
        cleanupControlUpdated,
        cleanupPlaybackPlay,
        cleanupPlaybackPause,
        cleanupSessionConnected,
        cleanupSessionError,
        cleanupSessionEnded,
      ];

      // Check if already connected (for immediate feedback if connection already exists)
      if (sessionWebSocketService.isConnectionActive()) {
        console.log('[KaraokePlayerStore] WebSocket already connected');
        set({ connected: true });
      }
    },

    disconnect: () => {
      // Clean up event listeners
      if (window.__playerWebSocketCleanup) {
        window.__playerWebSocketCleanup.forEach((cleanup: () => void) => cleanup());
        delete window.__playerWebSocketCleanup;
      }

      set({ connected: false });
    },

    setSongId: (id: string, duration?: number) => {
      // Accept duration from the backend if available
      songDuration = duration;
      // Reset playback state when changing songs
      playbackOffset = 0;
      playbackStartTime = null;
      set({
        songId: id,
        instrumentalUrl: `/api/songs/${id}/download/instrumental`,
        vocalUrl: `/api/songs/${id}/download/vocals`,
        isReady: false,
        error: null,
        duration: duration || 0,
        currentTime: 0,
        isPlaying: false,
        miniPlayerDismissed: false, // Reset dismissed state for new song
      });
    },

    setSongAndLoad: async (id: string, duration?: number, title?: string, artist?: string) => {
      // Set loading flag to prevent WebSocket interference
      isLoadingNewSong = true;

      get().cleanup(); // This will reset audio nodes and state
      get().setSongId(id, duration); // This will set new song and reset playback position
      
      // Set song metadata for mini-player display and reset songEnded state
      set({
        songTitle: title || null,
        songArtist: artist || null,
        songEnded: false,
      });

      // Tell the backend we're loading a new song so it can reset performance state
      socketEmit("song_loaded", {
        songId: id,
        duration: duration || 0,
        currentTime: 0,
        isPlaying: false
      });

      await get().load();

      // Re-enable WebSocket updates after a short delay to allow backend reset to propagate
      setTimeout(() => {
        isLoadingNewSong = false;
        // Clear any stale local update tracking to ensure clean sync
        Object.keys(lastLocalUpdate).forEach(key => delete lastLocalUpdate[key]);
        console.log('Re-enabled WebSocket performance state updates');
      }, 500);
    },

    load: async () => {
      set({ isLoading: true });
      try {
        const { instrumentalUrl, vocalUrl } = get();
        if (!instrumentalUrl || !vocalUrl) {
          set({
            error: "Missing instrumental or vocal URL.",
            isLoading: false,
          });
          return;
        }
        const tempContext = new window.AudioContext();
        const [instArr, vocArr] = await Promise.all([
          fetch(instrumentalUrl, { cache: "reload" }).then((r) => {
            if (!r.ok) throw new Error(`fetch failed with status ${r.status}`);
            return r.arrayBuffer();
          }),
          fetch(vocalUrl, { cache: "reload" }).then((r) => {
            if (!r.ok) throw new Error(`fetch failed with status ${r.status}`);
            return r.arrayBuffer();
          }),
        ]);
        const [instBuf, vocBuf] = await Promise.all([
          tempContext.decodeAudioData(instArr.slice(0)),
          tempContext.decodeAudioData(vocArr.slice(0)),
        ]);
        instrumentalBuffer = instBuf;
        vocalBuffer = vocBuf;
        // Prefer songDuration from backend, otherwise use decoded buffer duration
        const durationSeconds =
          songDuration !== undefined
            ? songDuration
            : instBuf.duration;
        set({
          duration: durationSeconds,
          isReady: true,
          error: null,
        });

        // Confirm to backend that song is loaded and ready with final duration
        socketEmit("song_ready", {
          songId: get().songId,
          duration: durationSeconds,
          currentTime: 0,
          isPlaying: false,
          isReady: true
        });

        tempContext.close();
      } catch {
        set({ error: "Failed to load or decode audio." });
      } finally {
        set({ isLoading: false });
      }
    },

    play: () => {
      if (!audioContext) {
        audioContext = new window.AudioContext();
      }
      if (!instrumentalBuffer || !vocalBuffer) return;
      clearIntervals();

      // Reset songEnded flag when starting playback
      set({ songEnded: false });

      setupAudioGraph(audioContext.currentTime, playbackOffset);
      playbackStartTime = audioContext.currentTime;
      updatePlayerState({ isPlaying: true });

      startTimeUpdate();
    },

    pause: () => {
      if (instrumentalSource) instrumentalSource.stop();
      if (vocalSource) vocalSource.stop();
      clearIntervals();
      if (audioContext && playbackStartTime !== null) {
        // Calculate how much time has elapsed since playback started
        const elapsed = audioContext.currentTime - playbackStartTime;
        playbackOffset = playbackOffset + elapsed;
        playbackStartTime = null;
        updatePlayerState({ currentTime: playbackOffset, isPlaying: false });
      } else {
        updatePlayerState({ isPlaying: false });
      }
    },

    userPlay: () => {
      socketEmit("playback_play", {});
      get().play();
    },

    userPause: () => {
      socketEmit("playback_pause", {});
      get().pause();
    },

    // Accepts seconds as canonical unit
    seek: (timeSeconds: number) => {
      if (!audioContext || !instrumentalBuffer || !vocalBuffer) return;
      clearIntervals();
      playbackOffset = timeSeconds;
      
      // Reset songEnded flag when seeking
      set({ songEnded: false });
      
      if (get().isPlaying) {
        setupAudioGraph(audioContext.currentTime, timeSeconds);
        playbackStartTime = audioContext.currentTime;
        startTimeUpdate();
        updatePlayerState({ currentTime: timeSeconds });
      } else {
        playbackStartTime = null;
        updatePlayerState({ currentTime: timeSeconds, isPlaying: false });
      }
    },

    resetSongEnded: () => {
      set({ songEnded: false });
    },

    setVocalVolume: (volume: number) => {
      const normalized = Math.max(0, Math.min(1, volume));
      updatePerformanceControl("vocalVolume", normalized);
      if (vocalGain) vocalGain.gain.value = normalized;
    },

    setInstrumentalVolume: (volume: number) => {
      const normalized = Math.max(0, Math.min(1, volume));
      updatePerformanceControl("instrumentalVolume", normalized);
      if (instrumentalGain) instrumentalGain.gain.value = normalized;
    },

    setLyricsSize: (size: "small" | "medium" | "large") => {
      updatePerformanceControl("lyricsSize", size);
    },

    setLyricsOffset: (offset: number) => {
      updatePerformanceControl("lyricsOffset", offset);
    },

    setAutoScrollEnabled: (enabled: boolean) => {
      // Auto-scroll is a local-only setting, no need to sync via WebSocket
      set({ autoScrollEnabled: enabled });
    },

    cleanup: () => {
      resetAudioNodes();
      // Clear any pending local update tracking to avoid stale state
      Object.keys(lastLocalUpdate).forEach(key => delete lastLocalUpdate[key]);
      // Note: We don't reset the store state here as it causes infinite loops
      // State should only be reset when explicitly loading a new song
    },

    getWaveformData: () => {
      if (!analyser) return null;
      const array = new Uint8Array(analyser.frequencyBinCount);
      analyser.getByteTimeDomainData(array);
      return Array.from(array);
    },

    // Mini-player actions
    setMiniPlayerEnabled: (enabled: boolean) => {
      set({ miniPlayerEnabled: enabled });
    },

    setMiniPlayerPosition: (position: MiniPlayerPosition) => {
      set({ miniPlayerPosition: position });
    },

    dismissMiniPlayer: () => {
      set({ miniPlayerDismissed: true });
    },

    updateFromWebSocket: (data: any) => {
      // Ignore updates during song loading to prevent interference
      if (isLoadingNewSong) {
        console.log('Ignoring WebSocket update during song loading');
        return;
      }

      const updates: Partial<KaraokePlayerState> = {};

      // Handle performance state updates
      if (data.vocal_volume !== undefined && !shouldIgnoreWebSocketUpdate("vocal_volume", data.vocal_volume)) {
        updates.vocalVolume = data.vocal_volume as number;
        if (vocalGain) vocalGain.gain.value = data.vocal_volume as number;
      }
      if (data.instrumental_volume !== undefined && !shouldIgnoreWebSocketUpdate("instrumental_volume", data.instrumental_volume)) {
        updates.instrumentalVolume = data.instrumental_volume as number;
        if (instrumentalGain) instrumentalGain.gain.value = data.instrumental_volume as number;
      }
      if (data.lyrics_size !== undefined && !shouldIgnoreWebSocketUpdate("lyrics_size", data.lyrics_size)) {
        updates.lyricsSize = data.lyrics_size as "small" | "medium" | "large";
      }
      if (data.lyrics_offset !== undefined && !shouldIgnoreWebSocketUpdate("lyrics_offset", data.lyrics_offset)) {
        updates.lyricsOffset = data.lyrics_offset as number;
      }

      // Handle player state updates
      if (data.is_playing !== undefined) {
        updates.isPlaying = data.is_playing as boolean;
      }
      if (data.current_time !== undefined && !shouldIgnoreWebSocketUpdate("current_time", data.current_time)) {
        updates.currentTime = data.current_time as number;
      }
      if (data.duration !== undefined) {
        updates.duration = data.duration as number;
      }

      if (Object.keys(updates).length > 0) {
        set(updates);
      }
    },
  };
});
