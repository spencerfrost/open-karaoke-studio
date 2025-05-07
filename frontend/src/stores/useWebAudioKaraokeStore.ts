import { create } from "zustand";
import { getAudioUrl } from "@/services/songService";

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
  // Actions
  setSongId: (id: string) => void;
  setSongAndLoad: (id: string) => Promise<void>;
  load: () => Promise<void>;
  play: () => void;
  pause: () => void;
  seek: (time: number) => void;
  setVocalVol: (vol: number) => void;
  setInstrumentalVol: (vol: number) => void;
  cleanup: () => void;
  getWaveformData: () => Uint8Array | null;
}

export const useWebAudioKaraokeStore = create<WebAudioKaraokeState>(
  (set, get) => {
    // Internal refs for audio context, buffers, etc.
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

    return {
      songId: null,
      instrumentalUrl: "",
      vocalUrl: "",
      isReady: false,
      isPlaying: false,
      currentTime: 0,
      duration: 0,
      error: null,
      vocalVolume: 1,
      instrumentalVolume: 1,
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
          if (!audioContext) {
            audioContext = new window.AudioContext();
          }
          // Fetch and decode
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
          // Log error for debugging, as required by SonarLint

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
        // Track time
        if (interval) clearInterval(interval);
        interval = setInterval(() => {
          set({ currentTime: audioContext!.currentTime });
        }, 100);
        instrumentalSource.onended = () => {
          set({ isPlaying: false });
          if (interval) clearInterval(interval);
        };
      },
      pause: () => {
        if (instrumentalSource) instrumentalSource.stop();
        if (vocalSource) vocalSource.stop();
        set({ isPlaying: false });
        if (interval) clearInterval(interval);
      },
      seek: (time: number) => {
        get().pause();
        if (!audioContext || !instrumentalBuffer || !vocalBuffer) return;
        // Create new sources at offset
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
        if (interval) clearInterval(interval);
        interval = setInterval(() => {
          set({ currentTime: audioContext!.currentTime });
        }, 100);
        instrumentalSource.onended = () => {
          set({ isPlaying: false });
          if (interval) clearInterval(interval);
        };
      },
      setVocalVol: (vol: number) => {
        set({ vocalVolume: vol });
        if (vocalGain) vocalGain.gain.value = vol;
      },
      setInstrumentalVol: (vol: number) => {
        set({ instrumentalVolume: vol });
        if (instrumentalGain) instrumentalGain.gain.value = vol;
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
