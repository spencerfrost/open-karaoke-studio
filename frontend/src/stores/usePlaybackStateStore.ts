import { create } from "zustand";
import * as Tone from "tone";
import { createLogger } from "@/lib/logger";
import { useAudioControlsStore } from "./useAudioControlsStore";
import { getGrainParams } from "./shared/audioHelpers";

const logger = createLogger("store:playbackState");

export interface PlaybackStateState {
  // Audio/track info
  songId: string | null;
  instrumentalUrl: string;
  vocalUrl: string;
  backingVocalUrl: string;
  isReady: boolean;
  isLoading: boolean;
  duration: number; // seconds (float) - canonical unit
  error: string | null;

  // Playback state
  isPlaying: boolean;
  currentTime: number;
  songEnded: boolean; // True when song has finished playing (not just paused)

  // Actions
  setSongId: (id: string, duration?: number, gainDb?: number) => void;
  load: () => Promise<void>;
  play: (
    playbackSpeed: number,
    volumes: { vocal: number; backing: number; instrumental: number },
  ) => void;
  pause: (playbackSpeed: number) => void;
  seek: (
    timeSeconds: number,
    playbackSpeed: number,
    volumes: { vocal: number; backing: number; instrumental: number },
  ) => void;
  resetSongEnded: () => void;
  cleanup: () => void;
  getWaveformData: () => number[] | null;

  // Internal state updaters
  updatePlaybackState: (
    updates: Partial<
      Pick<PlaybackStateState, "isPlaying" | "currentTime" | "duration">
    >,
  ) => void;

  // Lifecycle methods
  startTimeUpdate: (
    playbackSpeed: number,
    onUpdate: (state: {
      isPlaying: boolean;
      currentTime: number;
      duration: number;
    }) => void,
  ) => void;
  stopTimeUpdate: () => void;
}

export const usePlaybackStateStore = create<PlaybackStateState>((set, get) => {
  // --- Web Audio API internals (not exposed to UI) ---
  let audioContext: AudioContext | null = null;
  let instrumentalBuffer: AudioBuffer | null = null;
  let vocalBuffer: AudioBuffer | null = null;
  let backingVocalBuffer: AudioBuffer | null = null;
  // Tone.js GrainPlayers for pitch-preserving speed control
  let instrumentalPlayer: Tone.GrainPlayer | null = null;
  let vocalPlayer: Tone.GrainPlayer | null = null;
  let backingVocalPlayer: Tone.GrainPlayer | null = null;
  let instrumentalGain: GainNode | null = null;
  let vocalGain: GainNode | null = null;
  let backingVocalGain: GainNode | null = null;
  let analyser: AnalyserNode | null = null;
  let animationFrameId: number | null = null;
  let websocketInterval: number | null = null;

  let playbackStartTime: number | null = null; // audioContext.currentTime when playback started
  let playbackOffset: number = 0; // seconds into the track when playback started

  // Add a variable to store song duration in seconds
  let songDuration: number | undefined = undefined;
  // Per-song normalization gain in dB (stored when song is loaded, applied in audio graph)
  let normalizationGainDb: number = 0;
  let normalizationGainNode: GainNode | null = null;

  // --- Audio graph helpers ---
  function setupAnalyser() {
    if (!analyser && audioContext) {
      analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
    }
  }

  function clearIntervals() {
    if (animationFrameId) cancelAnimationFrame(animationFrameId);
    if (websocketInterval) clearInterval(websocketInterval);
    animationFrameId = null;
    websocketInterval = null;
  }

  function setupAudioGraph(
    _startTime: number,
    offset: number | undefined,
    playbackSpeed: number,
    volumes: { vocal: number; backing: number; instrumental: number },
  ) {
    // Clean up any previous GrainPlayers
    if (instrumentalPlayer) {
      try {
        instrumentalPlayer.stop();
      } catch {
        // Ignore if already stopped
      }
      instrumentalPlayer.dispose();
    }
    if (vocalPlayer) {
      try {
        vocalPlayer.stop();
      } catch {
        // Ignore if already stopped
      }
      vocalPlayer.dispose();
    }
    if (backingVocalPlayer) {
      try {
        backingVocalPlayer.stop();
      } catch {
        // Ignore if already stopped
      }
      backingVocalPlayer.dispose();
    }

    if (!audioContext || !instrumentalBuffer || !vocalBuffer) return;

    // Set Tone.js to use our AudioContext
    Tone.setContext(audioContext);

    // Calculate grain parameters based on current playback speed
    const { grainSize, overlap } = getGrainParams(playbackSpeed);

    // Create GrainPlayers for pitch-preserving speed control
    instrumentalPlayer = new Tone.GrainPlayer({
      url: instrumentalBuffer,
      loop: false,
      grainSize,
      overlap,
      playbackRate: playbackSpeed,
    });

    vocalPlayer = new Tone.GrainPlayer({
      url: vocalBuffer,
      loop: false,
      grainSize,
      overlap,
      playbackRate: playbackSpeed,
    });

    // Create backing vocal player if buffer available (three-track songs)
    if (backingVocalBuffer) {
      backingVocalPlayer = new Tone.GrainPlayer({
        url: backingVocalBuffer,
        loop: false,
        grainSize,
        overlap,
        playbackRate: playbackSpeed,
      });
    } else {
      backingVocalPlayer = null;
    }

    // Create gain nodes for volume control
    instrumentalGain = audioContext.createGain();
    instrumentalGain.gain.value = volumes.instrumental;
    vocalGain = audioContext.createGain();
    vocalGain.gain.value = volumes.vocal;
    backingVocalGain = audioContext.createGain();
    backingVocalGain.gain.value = volumes.backing;

    // Create or reuse the analyser node
    setupAnalyser();

    // Create normalization gain node (converts dB to linear amplitude)
    normalizationGainNode = audioContext.createGain();
    normalizationGainNode.gain.value = Math.pow(10, normalizationGainDb / 20);

    // Connect the graph: GrainPlayer -> VolumeGain -> NormalizationGain -> Analyser -> Destination
    instrumentalPlayer.connect(instrumentalGain);
    vocalPlayer.connect(vocalGain);
    instrumentalGain.connect(normalizationGainNode);
    vocalGain.connect(normalizationGainNode);
    if (backingVocalPlayer) {
      backingVocalPlayer.connect(backingVocalGain);
      backingVocalGain.connect(normalizationGainNode);
    }
    normalizationGainNode.connect(analyser!);
    analyser!.connect(audioContext.destination);

    // Handle playback end - use instrumental track as the reference
    // GrainPlayer uses onstop callback
    instrumentalPlayer.onstop = () => {
      // Check if we're still playing (wasn't manually stopped)
      const { isPlaying, duration } = get();
      if (isPlaying && playbackStartTime !== null && audioContext) {
        // Account for playback speed in time calculation
        const currentTime =
          playbackOffset +
          (audioContext.currentTime - playbackStartTime) * playbackSpeed;
        // Only auto-stop if we're near or past the end of the song
        if (currentTime >= duration - 0.5) {
          clearIntervals();
          playbackStartTime = null;
          playbackOffset = duration; // Set to exact duration
          set({ currentTime: duration, isPlaying: false, songEnded: true });
        }
      }
    };

    // Start the GrainPlayers in sync
    const playOffset = typeof offset === "number" ? offset : 0;
    instrumentalPlayer.start(Tone.now(), playOffset);
    vocalPlayer.start(Tone.now(), playOffset);
    if (backingVocalPlayer) {
      backingVocalPlayer.start(Tone.now(), playOffset);
    }
  }

  function resetAudioNodes() {
    if (instrumentalPlayer) {
      try {
        instrumentalPlayer.stop();
      } catch {
        // Ignore if already stopped
      }
      instrumentalPlayer.dispose();
    }
    if (vocalPlayer) {
      try {
        vocalPlayer.stop();
      } catch {
        // Ignore if already stopped
      }
      vocalPlayer.dispose();
    }
    if (backingVocalPlayer) {
      try {
        backingVocalPlayer.stop();
      } catch {
        // Ignore if already stopped
      }
      backingVocalPlayer.dispose();
    }
    if (audioContext) audioContext.close();
    audioContext = null;
    instrumentalBuffer = null;
    vocalBuffer = null;
    backingVocalBuffer = null;
    instrumentalPlayer = null;
    vocalPlayer = null;
    backingVocalPlayer = null;
    instrumentalGain = null;
    vocalGain = null;
    backingVocalGain = null;
    if (normalizationGainNode) {
      normalizationGainNode.disconnect();
      normalizationGainNode = null;
    }
    analyser = null;
    clearIntervals();
    playbackStartTime = null;
    playbackOffset = 0;
  }

  useAudioControlsStore.subscribe((state) => {
    const { applyVolumeToGainNode } = useAudioControlsStore.getState();
    applyVolumeToGainNode(vocalGain, state.vocalVolume);
    applyVolumeToGainNode(backingVocalGain, state.backingVocalVolume);
    applyVolumeToGainNode(instrumentalGain, state.instrumentalVolume);
  });

  return {
    songId: null,
    instrumentalUrl: "",
    vocalUrl: "",
    backingVocalUrl: "",
    isReady: false,
    isLoading: false,
    duration: 0,
    error: null,
    isPlaying: false,
    currentTime: 0,
    songEnded: false,

    setSongId: (id: string, duration?: number, gainDb?: number) => {
      // Accept duration and normalization gain from the backend if available
      songDuration = duration;
      normalizationGainDb = gainDb ?? 0;
      // Reset playback state when changing songs
      playbackOffset = 0;
      playbackStartTime = null;
      set({
        songId: id,
        instrumentalUrl: `/api/songs/${id}/download/instrumental`,
        vocalUrl: `/api/songs/${id}/download/vocals`,
        backingVocalUrl: `/api/songs/${id}/download/backing-vocals`,
        isReady: false,
        error: null,
        duration: duration || 0,
        currentTime: 0,
        isPlaying: false,
      });
    },

    load: async () => {
      set({ isLoading: true });
      try {
        const { instrumentalUrl, vocalUrl, backingVocalUrl } = get();
        if (!instrumentalUrl || !vocalUrl) {
          set({
            error: "Missing instrumental or vocal URL.",
            isLoading: false,
          });
          return;
        }
        const tempContext = new window.AudioContext();

        // Fetch required tracks
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

        // Optionally fetch backing vocals (may 404 for legacy 2-track songs)
        let backingVocalArr: ArrayBuffer | null = null;
        if (backingVocalUrl) {
          try {
            const resp = await fetch(backingVocalUrl, { cache: "reload" });
            if (resp.ok) {
              backingVocalArr = await resp.arrayBuffer();
            }
          } catch {
            // Backing vocals not available — continue with 2-track mode
          }
        }

        // Decode audio buffers
        const decodePromises: Promise<AudioBuffer>[] = [
          tempContext.decodeAudioData(instArr.slice(0)),
          tempContext.decodeAudioData(vocArr.slice(0)),
        ];
        if (backingVocalArr) {
          decodePromises.push(
            tempContext.decodeAudioData(backingVocalArr.slice(0)),
          );
        }
        const decoded = await Promise.all(decodePromises);
        instrumentalBuffer = decoded[0];
        vocalBuffer = decoded[1];
        backingVocalBuffer = decoded[2] ?? null;

        // Prefer songDuration from backend, otherwise use decoded buffer duration
        const durationSeconds =
          songDuration !== undefined
            ? songDuration
            : instrumentalBuffer.duration;
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

    play: (
      playbackSpeed: number,
      volumes: { vocal: number; backing: number; instrumental: number },
    ) => {
      if (!audioContext) {
        audioContext = new window.AudioContext();
      }
      if (!instrumentalBuffer || !vocalBuffer) return;
      clearIntervals();

      // Reset songEnded flag when starting playback
      set({ songEnded: false });

      setupAudioGraph(
        audioContext.currentTime,
        playbackOffset,
        playbackSpeed,
        volumes,
      );
      playbackStartTime = audioContext.currentTime;
      set({ isPlaying: true });
    },

    pause: (playbackSpeed: number) => {
      if (instrumentalPlayer) {
        try {
          instrumentalPlayer.stop();
        } catch {
          // Ignore if already stopped
        }
      }
      if (vocalPlayer) {
        try {
          vocalPlayer.stop();
        } catch {
          // Ignore if already stopped
        }
      }
      if (backingVocalPlayer) {
        try {
          backingVocalPlayer.stop();
        } catch {
          // Ignore if already stopped
        }
      }
      clearIntervals();
      if (audioContext && playbackStartTime !== null) {
        // Calculate how much time has elapsed since playback started, accounting for speed
        const elapsedRealTime = audioContext.currentTime - playbackStartTime;
        const elapsedSongTime = elapsedRealTime * playbackSpeed;
        playbackOffset = playbackOffset + elapsedSongTime;
        playbackStartTime = null;
        set({ currentTime: playbackOffset, isPlaying: false });
      } else {
        set({ isPlaying: false });
      }
    },

    seek: (
      timeSeconds: number,
      playbackSpeed: number,
      volumes: { vocal: number; backing: number; instrumental: number },
    ) => {
      if (!audioContext || !instrumentalBuffer || !vocalBuffer) return;
      clearIntervals();
      playbackOffset = timeSeconds;

      // Reset songEnded flag when seeking
      set({ songEnded: false });

      if (get().isPlaying) {
        // Stop current players before recreating
        if (instrumentalPlayer) {
          try {
            instrumentalPlayer.stop();
          } catch {
            // Ignore if already stopped
          }
        }
        if (vocalPlayer) {
          try {
            vocalPlayer.stop();
          } catch {
            // Ignore if already stopped
          }
        }
        if (backingVocalPlayer) {
          try {
            backingVocalPlayer.stop();
          } catch {
            // Ignore if already stopped
          }
        }
        setupAudioGraph(
          audioContext.currentTime,
          timeSeconds,
          playbackSpeed,
          volumes,
        );
        playbackStartTime = audioContext.currentTime;
        set({ currentTime: timeSeconds });
      } else {
        playbackStartTime = null;
        set({ currentTime: timeSeconds, isPlaying: false });
      }
    },

    resetSongEnded: () => {
      set({ songEnded: false });
    },

    cleanup: () => {
      resetAudioNodes();
    },

    getWaveformData: () => {
      if (!analyser) return null;
      const array = new Uint8Array(analyser.frequencyBinCount);
      analyser.getByteTimeDomainData(array);
      return Array.from(array);
    },

    updatePlaybackState: (
      updates: Partial<
        Pick<PlaybackStateState, "isPlaying" | "currentTime" | "duration">
      >,
    ) => {
      set(updates);
    },

    startTimeUpdate: (
      playbackSpeed: number,
      onUpdate: (state: {
        isPlaying: boolean;
        currentTime: number;
        duration: number;
      }) => void,
    ) => {
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
          // Account for playback speed in time calculation
          const elapsedRealTime = audioContext.currentTime - playbackStartTime;
          const elapsedSongTime = elapsedRealTime * playbackSpeed;
          currentTime = playbackOffset + elapsedSongTime;
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
          onUpdate({ isPlaying: true, currentTime, duration });
        }
      }, 300);
    },

    stopTimeUpdate: () => {
      clearIntervals();
    },
  };
});
