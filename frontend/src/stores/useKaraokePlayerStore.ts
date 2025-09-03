import { create } from "zustand";

// WebSocket URL for FastAPI performance controls
// Use relative path so it goes through Vite proxy
const PERFORMANCE_WS_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/performance`;
const INITIAL_STATE = {
  isReady: false,
  isLoading: false,
  error: null,
  currentTime: 0,
  isPlaying: false,
};

// Helper function to get audio URLs
const getAudioUrl = (
  songId: string,
  trackType: "vocals" | "instrumental" | "original",
): string => {
  return `/api/songs/${songId}/download/${trackType}`;
};

interface KaraokePlayerState {
  // Audio/track info
  songId: string | null;
  instrumentalUrl: string;
  vocalUrl: string;
  isReady: boolean;
  isLoading: boolean;
  duration: number; // seconds (float) - canonical unit
  error: string | null;

  // Playback state
  isPlaying: boolean;
  currentTime: number;

  // Controls
  vocalVolume: number;
  instrumentalVolume: number;
  lyricsSize: "small" | "medium" | "large";
  lyricsOffset: number;

  // WebSocket
  connected: boolean;
  websocket: WebSocket | null;

  // Actions
  connect: () => void;
  disconnect: () => void;
  setSongId: (id: string, duration?: number) => void;
  setSongAndLoad: (id: string, duration?: number) => Promise<void>;
  load: () => Promise<void>;
  play: () => void;
  pause: () => void;
  userPlay: () => void;
  userPause: () => void;
  seek: (time: number) => void;
  setVocalVolume: (volume: number) => void;
  setInstrumentalVolume: (volume: number) => void;
  setLyricsSize: (size: "small" | "medium" | "large") => void;
  setLyricsOffset: (offset: number) => void;
  cleanup: () => void;
  getWaveformData: () => number[] | null;
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
  let interval: NodeJS.Timeout | null = null;

  let playbackStartTime: number | null = null; // audioContext.currentTime when playback started
  let playbackOffset: number = 0; // seconds into the track when playback started

  // Add a variable to store song duration in seconds
  let songDuration: number | undefined = undefined;

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
    if (interval) clearInterval(interval);
  }

  function socketEmit(messageType: string, data?: Record<string, unknown>) {
    const { websocket } = get();
    if (websocket && websocket.readyState === WebSocket.OPEN) {
      const message = {
        type: messageType,
        ...(data || {})
      };
      setTimeout(() => {
        websocket.send(JSON.stringify(message));
      }, 5);
    } else {
      console.error('❌ WebSocket not ready:', {
        websocket: !!websocket,
        readyState: websocket?.readyState,
        OPEN: WebSocket.OPEN
      });
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
    // Stat the sources in sync
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

  function startTimeInterval() {
    if (interval) clearInterval(interval);
    if (!audioContext) return;
    interval = setInterval(() => {
      const { isReady, websocket, isPlaying, duration } = get();
      if (!isReady) return;
      let currentTime = playbackOffset;
      if (isPlaying && playbackStartTime !== null && audioContext) {
        currentTime =
          playbackOffset + (audioContext.currentTime - playbackStartTime);
      }
      set({ currentTime });
      if (websocket && websocket.readyState === WebSocket.OPEN && audioContext && isPlaying) {
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
    isPlaying: false,
    currentTime: 0,
    vocalVolume: 0,
    instrumentalVolume: 1.0,
    lyricsSize: "medium",
    lyricsOffset: 0,
    connected: false,
    websocket: null,

    // Actions
    connect: () => {
      const currentState = get();
      
      // Close existing connection if any
      if (currentState.websocket) {
        if (currentState.websocket.readyState === WebSocket.OPEN) {
          return; // Already connected
        }
        currentState.websocket.close();
      }

      console.log('Connecting to WebSocket at:', PERFORMANCE_WS_URL);
      const websocket = new WebSocket(PERFORMANCE_WS_URL);
      
      // Set the websocket in state immediately
      set({ websocket });
      
      websocket.onopen = () => {
        console.log('WebSocket connected successfully');
        set({ connected: true });
        // Join performance controls
        websocket.send(JSON.stringify({
          type: 'join_performance'
        }));
      };

      websocket.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        set({ connected: false, websocket: null });
      };

      websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
        set({ connected: false, websocket: null });
      };

      websocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('WebSocket received:', data);
          
          if (data.type === 'performance_state') {
            // Check if currentTime update should be ignored to prevent seek flickering
            const shouldIgnoreCurrentTime = shouldIgnoreWebSocketUpdate("current_time", data.state.current_time);
            
            set((state) => ({
              isPlaying: data.state.is_playing,
              currentTime: shouldIgnoreCurrentTime ? state.currentTime : data.state.current_time,
              duration: data.state.duration > 0 ? data.state.duration : state.duration,
              vocalVolume: shouldIgnoreWebSocketUpdate("vocal_volume", data.state.vocal_volume) ? state.vocalVolume : data.state.vocal_volume,
              instrumentalVolume: shouldIgnoreWebSocketUpdate("instrumental_volume", data.state.instrumental_volume) ? state.instrumentalVolume : data.state.instrumental_volume,
              lyricsSize: shouldIgnoreWebSocketUpdate("lyrics_size", data.state.lyrics_size) ? state.lyricsSize : data.state.lyrics_size,
              lyricsOffset: shouldIgnoreWebSocketUpdate("lyrics_offset", data.state.lyrics_offset) ? state.lyricsOffset : data.state.lyrics_offset,
            }));
          } else if (data.type === 'control_updated') {
            console.log('Received control update:', data.control, '=', data.value);
            // Check if this is an echo of our own local update
            if (shouldIgnoreWebSocketUpdate(data.control, data.value)) {
              console.log('Ignoring control update (local echo)');
              return; // Ignore this update to prevent flicker
            }

            if (data.control === "vocal_volume") {
              console.log('Updating vocal volume to:', data.value);
              set({ vocalVolume: data.value });
              if (vocalGain) vocalGain.gain.value = data.value;
            } else if (data.control === "instrumental_volume") {
              console.log('Updating instrumental volume to:', data.value);
              set({ instrumentalVolume: data.value });
              if (instrumentalGain) instrumentalGain.gain.value = data.value;
            } else if (data.control === "lyrics_size") {
              set({ lyricsSize: data.value });
            } else if (data.control === "lyrics_offset") {
              set({ lyricsOffset: data.value });
            }
          } else if (data.type === 'playback_play') {
            get().play();
          } else if (data.type === 'playback_pause') {
            get().pause();
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      set({ websocket });
    },
    disconnect: () => {
      const { websocket } = get();
      if (websocket) {
        console.log('Disconnecting WebSocket');
        websocket.close();
      }
      set({ connected: false, websocket: null });
    },
    setSongId: (id: string, duration?: number) => {
      // Accept duration from the backend if available
      songDuration = duration;
      set({
        songId: id,
        instrumentalUrl: getAudioUrl(id, "instrumental"),
        vocalUrl: getAudioUrl(id, "vocals"),
        isReady: false,
        error: null,
        duration: duration || 0,
      });
    },
    setSongAndLoad: async (id: string, duration?: number) => {
      get().setSongId(id, duration);
      get().cleanup();
      await get().load();
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

      setupAudioGraph(audioContext.currentTime, playbackOffset);
      playbackStartTime = audioContext.currentTime;
      set({ isPlaying: true });

      startTimeInterval();
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
        set({ currentTime: playbackOffset });
      }
      set({ isPlaying: false });
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
      if (get().isPlaying) {
        setupAudioGraph(audioContext.currentTime, timeSeconds);
        playbackStartTime = audioContext.currentTime;
        startTimeInterval();
        updatePlayerState({ currentTime: timeSeconds });
      } else {
        playbackStartTime = null;
        updatePlayerState({ currentTime: timeSeconds, isPlaying: false });
      }
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
    cleanup: () => {
      resetAudioNodes();
      updatePlayerState({ ...INITIAL_STATE });
    },
    getWaveformData: () => {
      if (!analyser) return null;
      const array = new Uint8Array(analyser.frequencyBinCount);
      analyser.getByteTimeDomainData(array);
      return Array.from(array);
    },
  };
});
