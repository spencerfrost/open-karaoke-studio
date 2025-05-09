import { getAudioUrl } from "@/services/songService";
import { usePerformanceControlsStore } from "./usePerformanceControlsStore";
import { create } from "zustand";

interface WebAudioKaraokeState {
  songId: string | null;
  error: string | null;
  instrumentalUrl: string;
  vocalUrl: string;

  isReady: boolean;
  isPlaying: boolean;
  currentTime: number;
  duration: number;

  vocalVolume: number;
  instrumentalVolume: number;

  isLoading: boolean;

  setSongId: (id: string) => void;
  setSongAndLoad: (id: string) => Promise<void>;
  load: () => Promise<void>;
  play: () => void;
  pause: () => void;
  seek: (time: number) => void;
  cleanup: () => void;
  getWaveformData: () => Uint8Array | null;
}

export const useWebAudioKaraokeStore = create<WebAudioKaraokeState>(
  (set, get) => {
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
    let stateInterval: NodeJS.Timeout | null = null;

    usePerformanceControlsStore.subscribe((state, prevState) => {
      const { vocalVolume, instrumentalVolume } = state;
      const {
        vocalVolume: prevVocalVolume,
        instrumentalVolume: prevInstrumentalVolume,
      } = prevState;
      if (vocalVolume !== prevVocalVolume && vocalGain) {
        vocalGain.gain.value = vocalVolume;
      }
      if (instrumentalVolume !== prevInstrumentalVolume && instrumentalGain) {
        instrumentalGain.gain.value = instrumentalVolume;
      }
    });

    const emitPlayerState = () => {
      const perfStore = usePerformanceControlsStore.getState();
      const { isPlaying, currentTime, duration } = get();
      const { socket } = perfStore;
      if (socket?.connected) {
        socket.emit("update_player_state", {
          isPlaying,
          currentTime,
          duration,
        });
      }
    };

    // --- Helper Functions ---
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
      if (stateInterval) clearInterval(stateInterval);
    }

    function setupAudioGraph(startTime: number, offset?: number) {
      // Clean up any previous sources
      if (instrumentalSource) instrumentalSource.stop();
      if (vocalSource) vocalSource.stop();
      if (!audioContext || !instrumentalBuffer || !vocalBuffer) return;
      // Create sources
      instrumentalSource = audioContext.createBufferSource();
      instrumentalSource.buffer = instrumentalBuffer;
      vocalSource = audioContext.createBufferSource();
      vocalSource.buffer = vocalBuffer;
      // Create gain nodes
      instrumentalGain = audioContext.createGain();
      instrumentalGain.gain.value = get().instrumentalVolume;
      vocalGain = audioContext.createGain();
      vocalGain.gain.value = get().vocalVolume;
      // Create or reuse analyser node
      setupAnalyser();
      // Connect graph
      instrumentalSource.connect(instrumentalGain).connect(analyser!);
      vocalSource.connect(vocalGain).connect(analyser!);
      analyser!.connect(audioContext.destination);
      // Start in sync
      if (typeof offset === "number") {
        instrumentalSource.start(startTime, offset);
        vocalSource.start(startTime, offset);
      } else {
        instrumentalSource.start(startTime);
        vocalSource.start(startTime);
      }
      // Sync gain nodes in case volume changed before play
      syncGainValues();
    }

    function startTimeInterval() {
      if (interval) clearInterval(interval);
      if (!audioContext) return;
      interval = setInterval(() => {
        set({ currentTime: audioContext!.currentTime });
      }, 100);
    }

    function startStateInterval(emitPlayerState: () => void) {
      if (stateInterval) clearInterval(stateInterval);
      stateInterval = setInterval(() => {
        emitPlayerState();
      }, 500);
    }

    return {
      songId: null,
      instrumentalUrl: "",
      vocalUrl: "",
      isReady: false,
      isPlaying: false,
      currentTime: 0,
      duration: 0,
      error: null,
      isLoading: false,
      get vocalVolume() {
        return usePerformanceControlsStore.getState().vocalVolume;
      },
      get instrumentalVolume() {
        return usePerformanceControlsStore.getState().instrumentalVolume;
      },
      setSongId: (id: string) => {
        set({
          songId: id,
          instrumentalUrl: getAudioUrl(id, "instrumental"),
          vocalUrl: getAudioUrl(id, "vocals"),
          isReady: false,
          isPlaying: false, // Always reset playing state
          currentTime: 0,
          duration: 0,
          error: null,
        });
        emitPlayerState();
      },
      setSongAndLoad: async (id: string) => {
        get().setSongId(id);
        emitPlayerState();
        // Defensive: always cleanup before loading a new song
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
          audioContext ??= new window.AudioContext();
          const [instArr, vocArr] = await Promise.all([
            fetch(instrumentalUrl, { cache: "reload" }).then((r) => {
              if (!r.ok)
                throw new Error(`fetch failed with status ${r.status}`);
              return r.arrayBuffer();
            }),
            fetch(vocalUrl, { cache: "reload" }).then((r) => {
              if (!r.ok)
                throw new Error(`fetch failed with status ${r.status}`);
              return r.arrayBuffer();
            }),
          ]);
          const [instBuf, vocBuf] = await Promise.all([
            audioContext.decodeAudioData(instArr.slice(0)),
            audioContext.decodeAudioData(vocArr.slice(0)),
          ]);
          instrumentalBuffer = instBuf;
          vocalBuffer = vocBuf;
          set({
            duration: instBuf.duration,
            isReady: true,
            error: null,
          });
          emitPlayerState();
        } catch {
          set({ error: "Failed to load or decode audio." });
        } finally {
          set({ isLoading: false });
        }
      },
      play: () => {
        if (!audioContext || !instrumentalBuffer || !vocalBuffer) return;
        clearIntervals();
        const now = audioContext.currentTime;
        setupAudioGraph(now);
        set({ isPlaying: true });
        emitPlayerState();
        startTimeInterval();
        instrumentalSource!.onended = () => {
          set({ isPlaying: false });
          emitPlayerState();
          clearIntervals();
        };
      },
      pause: () => {
        if (instrumentalSource) instrumentalSource.stop();
        if (vocalSource) vocalSource.stop();
        set({ isPlaying: false });
        emitPlayerState();
        clearIntervals();
      },
      seek: (time: number) => {
        get().pause();
        if (!audioContext || !instrumentalBuffer || !vocalBuffer) return;
        clearIntervals();
        const now = audioContext.currentTime;
        setupAudioGraph(now, time);
        set({ isPlaying: true, currentTime: time });
        emitPlayerState();
        startTimeInterval();
        startStateInterval(emitPlayerState);
        instrumentalSource!.onended = () => {
          set({ isPlaying: false });
          clearIntervals();
          emitPlayerState();
        };
      },
      cleanup: () => {
        get().pause();
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
        set({
          isReady: false,
          isLoading: false,
          error: null,
        });
      },
      getWaveformData: () => {
        if (!analyser || !waveformArray) return null;
        analyser.getByteTimeDomainData(waveformArray);
        return waveformArray;
      },
    };
  }
);
