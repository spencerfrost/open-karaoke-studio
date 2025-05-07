import { getAudioUrl } from "@/services/songService";
import { usePerformanceControlsStore } from "./usePerformanceControlsStore";
import { create } from "zustand";

interface WebAudioKaraokeState {
  songId: string | null;
  instrumentalUrl: string;
  vocalUrl: string;
  isReady: boolean;
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  error: string | null;
  vocalVolume: number;
  instrumentalVolume: number;
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
      // Only update if volume actually changed
      if (state.vocalVolume !== prevState.vocalVolume && vocalGain) {
        console.log("vocalVolume changed", state.vocalVolume, vocalGain);

        vocalGain.gain.value = state.vocalVolume;
      }
      if (
        state.instrumentalVolume !== prevState.instrumentalVolume &&
        instrumentalGain
      ) {
        instrumentalGain.gain.value = state.instrumentalVolume;
      }
    });

    const emitPlayerState = () => {
      const perfStore = usePerformanceControlsStore.getState();
      const { isPlaying, currentTime, duration } = get();
      const { socket } = perfStore;
      if (socket?.connected) {
        console.log("isPlaying", isPlaying);
        console.log("currentTime", currentTime);
        console.log("duration", duration);
        socket.emit("update_player_state", {
          isPlaying,
          currentTime,
          duration,
        });
      }
    };

    return {
      songId: null,
      instrumentalUrl: "",
      vocalUrl: "",
      isReady: false,
      isPlaying: false,
      currentTime: 0,
      duration: 0,
      error: null,
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
          isPlaying: false,
          currentTime: 0,
          duration: 0,
          error: null,
        });
      },
      setSongAndLoad: async (id: string) => {
        set({
          songId: id,
          instrumentalUrl: getAudioUrl(id, "instrumental"),
          vocalUrl: getAudioUrl(id, "vocals"),
          isReady: false,
          isPlaying: false,
          currentTime: 0,
          duration: 0,
          error: null,
        });
        await get().load();
      },
      load: async () => {
        const { instrumentalUrl, vocalUrl } = get();
        try {
          audioContext ??= new window.AudioContext();
          const [instArr, vocArr] = await Promise.all([
            fetch(instrumentalUrl).then((r) => r.arrayBuffer()),
            fetch(vocalUrl).then((r) => r.arrayBuffer()),
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
        } catch (err) {
          console.error("Failed to load or decode audio:", err);
          set({ error: "Failed to load or decode audio." });
        }
      },
      play: () => {
        if (!audioContext || !instrumentalBuffer || !vocalBuffer) return;
        // Clean up any previous sources
        if (instrumentalSource) instrumentalSource.stop();
        if (vocalSource) vocalSource.stop();
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
        if (!analyser) {
          analyser = audioContext.createAnalyser();
          analyser.fftSize = 256;
          waveformArray = new Uint8Array(analyser.frequencyBinCount);
        }
        // Connect graph
        instrumentalSource.connect(instrumentalGain).connect(analyser);
        vocalSource.connect(vocalGain).connect(analyser);
        analyser.connect(audioContext.destination);
        // Start in sync
        const now = audioContext.currentTime;
        instrumentalSource.start(now);
        vocalSource.start(now);
        set({ isPlaying: true });
        emitPlayerState();
        // Track time
        if (interval) clearInterval(interval);
        interval = setInterval(() => {
          set({ currentTime: audioContext!.currentTime });
        }, 100);
        instrumentalSource.onended = () => {
          set({ isPlaying: false });
          emitPlayerState();
          if (interval) clearInterval(interval);
        };
        // Sync gain nodes in case volume changed before play
        if (vocalGain) vocalGain.gain.value = get().vocalVolume;
        if (instrumentalGain)
          instrumentalGain.gain.value = get().instrumentalVolume;
      },
      pause: () => {
        if (instrumentalSource) instrumentalSource.stop();
        if (vocalSource) vocalSource.stop();
        set({ isPlaying: false });
        emitPlayerState();
        if (interval) clearInterval(interval);
        if (stateInterval) clearInterval(stateInterval);
      },
      seek: (time: number) => {
        get().pause();
        if (!audioContext || !instrumentalBuffer || !vocalBuffer) return;
        instrumentalSource = audioContext.createBufferSource();
        instrumentalSource.buffer = instrumentalBuffer;
        vocalSource = audioContext.createBufferSource();
        vocalSource.buffer = vocalBuffer;
        instrumentalGain = audioContext.createGain();
        instrumentalGain.gain.value = get().instrumentalVolume;
        vocalGain = audioContext.createGain();
        vocalGain.gain.value = get().vocalVolume;
        if (!analyser) {
          analyser = audioContext.createAnalyser();
          analyser.fftSize = 256;
          waveformArray = new Uint8Array(analyser.frequencyBinCount);
        }
        instrumentalSource.connect(instrumentalGain).connect(analyser);
        vocalSource.connect(vocalGain).connect(analyser);
        analyser.connect(audioContext.destination);
        const now = audioContext.currentTime;
        instrumentalSource.start(now, time);
        vocalSource.start(now, time);
        set({ isPlaying: true, currentTime: time });
        emitPlayerState();
        if (interval) clearInterval(interval);
        interval = setInterval(() => {
          set({ currentTime: audioContext!.currentTime });
        }, 100);
        if (stateInterval) clearInterval(stateInterval);
        stateInterval = setInterval(() => {
          emitPlayerState();
        }, 500);
        instrumentalSource.onended = () => {
          set({ isPlaying: false });
          if (interval) clearInterval(interval);
          if (stateInterval) clearInterval(stateInterval);
          emitPlayerState();
        };
        if (vocalGain) vocalGain.gain.value = get().vocalVolume;
        if (instrumentalGain)
          instrumentalGain.gain.value = get().instrumentalVolume;
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
        if (stateInterval) clearInterval(stateInterval);
        set({ isReady: false });
      },
      getWaveformData: () => {
        if (!analyser || !waveformArray) return null;
        analyser.getByteTimeDomainData(waveformArray);
        return waveformArray;
      },
    };
  }
);
