import { getAudioUrl } from "@/services/songService";
import { create } from "zustand";
import { io, Socket } from "socket.io-client";

const BASE_URL = import.meta.env.VITE_BACKEND_URL ?? "http://localhost:5000";
const INITIAL_STATE = {
  isReady: false,
  isLoading: false,
  error: null,
  currentTime: 0,
  isPlaying: false,
};

interface KaraokePlayerState {
  // Audio/track info
  songId: string | null;
  instrumentalUrl: string;
  vocalUrl: string;
  isReady: boolean;
  isLoading: boolean;
  duration: number;
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
  socket: Socket | null;

  // Actions
  connect: () => void;
  disconnect: () => void;
  setSongId: (id: string) => void;
  setSongAndLoad: (id: string) => Promise<void>;
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
  getWaveformData: () => Uint8Array | null;
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
  let waveformArray: Uint8Array | null = null;
  let interval: NodeJS.Timeout | null = null;

  let playbackStartTime: number | null = null; // audioContext.currentTime when playback started
  let playbackOffset: number = 0; // seconds into the track when playback started

  // --- WebSocket helpers ---
  function createSocket(): Socket {
    return io(BASE_URL, {
      autoConnect: false,
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    });
  }

  // --- Audio graph helpers ---
  function setupAnalyser() {
    if (!analyser && audioContext) {
      analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      waveformArray = new Uint8Array(analyser.frequencyBinCount);
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

  function socketEmit(event: string, data: unknown) {
    const { socket } = get();
    if (socket?.connected) {
      socket.emit(event, data);
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
    waveformArray = null;
    clearIntervals();
    playbackStartTime = null;
    playbackOffset = 0;
  }

  function startTimeInterval() {
    if (interval) clearInterval(interval);
    if (!audioContext) return;
    interval = setInterval(() => {
      const { isReady, socket, isPlaying, duration } = get();
      if (!isReady) return;
      let currentTime = playbackOffset;
      if (isPlaying && playbackStartTime !== null && audioContext) {
        currentTime =
          playbackOffset + (audioContext.currentTime - playbackStartTime);
      }
      set({ currentTime });
      if (socket?.connected && audioContext && isPlaying) {
        socket.emit("update_player_state", {
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
    >
  ) {
    set(updates);
    socketEmit("update_player_state", updates);
  }

  function updatePerformanceControl(
    control:
      | "vocalVolume"
      | "instrumentalVolume"
      | "lyricsSize"
      | "lyricsOffset",
    value: unknown
  ) {
    set({ [control]: value });
    // Map camelCase to snake_case for backend
    const backendControl = control.replace(
      /[A-Z]/g,
      (letter) => "_" + letter.toLowerCase()
    );
    socketEmit("update_performance_control", {
      control: backendControl,
      value,
    });
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
    socket: null,

    // Actions
    connect: () => {
      let socket = get().socket;
      if (!socket) {
        socket = createSocket();
        socket.on("connect", () => {
          set({ connected: true });
          socket?.emit("join_performance");
        });
        socket.on("disconnect", () => set({ connected: false }));
        socket.on("performance_state", (data) => {
          set((state) => ({
            isPlaying: data.is_playing,
            currentTime: data.current_time,
            duration: data.duration > 0 ? data.duration : state.duration,
            vocalVolume: data.vocal_volume,
            instrumentalVolume: data.instrumental_volume,
            lyricsSize: data.lyrics_size,
            lyricsOffset: data.lyrics_offset,
          }));
        });
        socket.on("control_updated", (update) => {
          if (update.control === "vocal_volume") {
            set({ vocalVolume: update.value });
            if (vocalGain) vocalGain.gain.value = update.value;
          } else if (update.control === "instrumental_volume") {
            set({ instrumentalVolume: update.value });
            if (instrumentalGain) instrumentalGain.gain.value = update.value;
          } else if (update.control === "lyrics_size") {
            set({ lyricsSize: update.value });
          } else if (update.control === "lyrics_offset") {
            set({ lyricsOffset: update.value });
          }
        });
        socket.on("playback_play", () => get().play());
        socket.on("playback_pause", () => get().pause());
        set({ socket });
      }
      if (!socket.connected) {
        socket.connect();
      }
    },
    disconnect: () => {
      const { socket } = get();
      if (socket?.connected) {
        socket.disconnect();
      }
      set({ connected: false });
    },
    setSongId: (id: string) => {
      set({
        songId: id,
        instrumentalUrl: getAudioUrl(id, "instrumental"),
        vocalUrl: getAudioUrl(id, "vocals"),
        isReady: false,
        error: null,
      });
    },
    setSongAndLoad: async (id: string) => {
      get().setSongId(id);
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
        set({ duration: instBuf.duration, isReady: true, error: null });
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
    seek: (time: number) => {
      if (!audioContext || !instrumentalBuffer || !vocalBuffer) return;
      clearIntervals();
      playbackOffset = time;
      if (get().isPlaying) {
        setupAudioGraph(audioContext.currentTime, time);
        playbackStartTime = audioContext.currentTime;
        startTimeInterval();
        updatePlayerState({ currentTime: time });
      } else {
        playbackStartTime = null;
        updatePlayerState({ currentTime: time, isPlaying: false });
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
      if (!analyser || !waveformArray) return null;
      analyser.getByteTimeDomainData(waveformArray);
      return waveformArray;
    },
  };
});
