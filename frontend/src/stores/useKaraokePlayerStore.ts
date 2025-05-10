import { getAudioUrl } from "@/services/songService";
import { create } from "zustand";
import { io, Socket } from "socket.io-client";

const BASE_URL = import.meta.env.VITE_BACKEND_URL ?? "http://localhost:5000";

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

  function setupAudioGraph(startTime: number, offset?: number) {
    if (instrumentalSource) instrumentalSource.stop();
    if (vocalSource) vocalSource.stop();
    if (!audioContext || !instrumentalBuffer || !vocalBuffer) return;
    instrumentalSource = audioContext.createBufferSource();
    instrumentalSource.buffer = instrumentalBuffer;
    vocalSource = audioContext.createBufferSource();
    vocalSource.buffer = vocalBuffer;
    instrumentalGain = audioContext.createGain();
    instrumentalGain.gain.value = get().instrumentalVolume;
    vocalGain = audioContext.createGain();
    vocalGain.gain.value = get().vocalVolume;
    setupAnalyser();
    instrumentalSource.connect(instrumentalGain).connect(analyser!);
    vocalSource.connect(vocalGain).connect(analyser!);
    analyser!.connect(audioContext.destination);
    if (typeof offset === "number") {
      instrumentalSource.start(startTime, offset);
      vocalSource.start(startTime, offset);
    } else {
      instrumentalSource.start(startTime);
      vocalSource.start(startTime);
    }
    syncGainValues();
  }

  function startTimeInterval() {
    if (interval) clearInterval(interval);
    if (!audioContext) return;
    interval = setInterval(() => {
      const { isReady, socket, isPlaying, duration } = get();
      if (!isReady) return;
      if (socket?.connected && audioContext && isPlaying) {
        socket.emit("update_player_state", {
          isPlaying: true,
          currentTime: audioContext.currentTime,
          duration,
        });
      }
    }, 300);
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
        socket.on("playback_play", () => {
          console.log("playback_play");
          get().play();
        });
        socket.on("playback_pause", () => {
          console.log("playback_pause");
          get().pause();
        });
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

      const offset = get().currentTime;
      setupAudioGraph(audioContext.currentTime, offset);
      set({ isPlaying: true, currentTime: offset });

      startTimeInterval();
    },
    pause: () => {
      if (instrumentalSource) instrumentalSource.stop();
      if (vocalSource) vocalSource.stop();
      clearIntervals();
      if (audioContext && playbackStartTime !== null) {
        const elapsed = audioContext.currentTime - playbackStartTime;
        const newCurrentTime = playbackOffset + elapsed;
        set({ currentTime: newCurrentTime });
        playbackOffset = newCurrentTime;
        playbackStartTime = null;
      }
      set({ isPlaying: false });
    },
    // User actions: emit to backend, then update local state
    userPlay: () => {
      const { socket } = get();
      if (socket?.connected) {
        socket.emit("playback_play");
      }
      get().play();
    },
    userPause: () => {
      const { socket } = get();
      if (socket?.connected) {
        socket.emit("playback_pause");
      }
      get().pause();
    },
    seek: (time: number) => {
      // --- Web Audio API seek logic ---
      if (!audioContext || !instrumentalBuffer || !vocalBuffer) return;
      clearIntervals();
      setupAudioGraph(audioContext.currentTime, time);
      playbackOffset = time;
      playbackStartTime = audioContext.currentTime;
      set({ currentTime: time });
      // Emit seek event to backend
      const { socket } = get();
      if (socket?.connected) {
        socket.emit("playback_seek", { time });
      }
    },
    setVocalVolume: (volume: number) => {
      const { socket } = get();
      const normalized = Math.max(0, Math.min(1, volume));
      set({ vocalVolume: normalized });
      if (socket?.connected) {
        socket.emit("update_performance_control", {
          control: "vocal_volume",
          value: normalized,
        });
      }
      if (vocalGain) vocalGain.gain.value = normalized;
    },
    setInstrumentalVolume: (volume: number) => {
      const { socket } = get();
      const normalized = Math.max(0, Math.min(1, volume));
      set({ instrumentalVolume: normalized });
      if (socket?.connected) {
        socket.emit("update_performance_control", {
          control: "instrumental_volume",
          value: normalized,
        });
      }
      if (instrumentalGain) instrumentalGain.gain.value = normalized;
    },
    setLyricsSize: (size: "small" | "medium" | "large") => {
      const { socket } = get();
      set({ lyricsSize: size });
      if (socket?.connected) {
        socket.emit("update_performance_control", {
          control: "lyrics_size",
          value: size,
        });
      }
    },
    setLyricsOffset: (offset: number) => {
      const { socket } = get();
      set({ lyricsOffset: offset });
      if (socket?.connected) {
        socket.emit("update_performance_control", {
          control: "lyrics_offset",
          value: offset,
        });
      }
    },
    cleanup: () => {
      // Stop and disconnect all audio nodes
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
      // Reset state
      set({
        isReady: false,
        isLoading: false,
        error: null,
        currentTime: 0,
        isPlaying: false,
      });
      // Emit reset state to backend/other clients
      const { socket } = get();
      if (socket?.connected) {
        socket.emit("reset_player_state");
      }
    },
    getWaveformData: () => {
      if (!analyser || !waveformArray) return null;
      analyser.getByteTimeDomainData(waveformArray);
      return waveformArray;
    },
  };
});
