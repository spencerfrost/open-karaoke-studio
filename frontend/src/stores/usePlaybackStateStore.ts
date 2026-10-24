import { create } from "zustand";
import { useAudioControlsStore } from "./useAudioControlsStore";

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
  play: (volumes: {
    vocal: number;
    backing: number;
    instrumental: number;
  }) => void;
  pause: () => void;
  seek: (
    timeSeconds: number,
    volumes: { vocal: number; backing: number; instrumental: number },
  ) => void;
  /**
   * Ramp the output to silence over `ms`. Resolves true once it is silent,
   * false if play, pause, seek or a new song interrupted it (the volume is back
   * at full by then). Resolves true at once when nothing is playing.
   * The players keep running at gain 0: stopping them is the caller's call.
   */
  fadeOut: (ms: number) => Promise<boolean>;
  resetSongEnded: () => void;
  cleanup: () => void;
  getWaveformData: () => number[] | null;
  getFrequencyData: () => number[] | null;

  // Internal state updaters
  updatePlaybackState: (
    updates: Partial<
      Pick<PlaybackStateState, "isPlaying" | "currentTime" | "duration">
    >,
  ) => void;

  // Lifecycle methods
  startTimeUpdate: (
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
  // One-shot sources: a buffer source can only be started once, so every
  // play and seek makes new ones. All three start at the same audio-clock
  // instant, which keeps the stems sample-locked.
  let instrumentalSource: AudioBufferSourceNode | null = null;
  let vocalSource: AudioBufferSourceNode | null = null;
  let backingVocalSource: AudioBufferSourceNode | null = null;
  let instrumentalGain: GainNode | null = null;
  let vocalGain: GainNode | null = null;
  let backingVocalGain: GainNode | null = null;
  let analyser: AnalyserNode | null = null;
  // Safety ceiling between the fade node and the analyser; see setupLimiter.
  let limiter: DynamicsCompressorNode | null = null;
  let animationFrameId: number | null = null;
  let websocketInterval: number | null = null;

  let playbackStartTime: number | null = null; // audioContext.currentTime when playback started
  let playbackOffset: number = 0; // seconds into the track when playback started

  // Add a variable to store song duration in seconds
  let songDuration: number | undefined = undefined;
  // Per-song normalization gain in dB (stored when song is loaded, applied in audio graph)
  let normalizationGainDb: number = 0;
  let normalizationGainNode: GainNode | null = null;
  // Its own node rather than a ramp on normalizationGainNode, so the per-song
  // loudness value is never overwritten and nothing has to restore it. Before
  // the analyser, so the visualizer fades with the sound.
  let fadeGainNode: GainNode | null = null;
  let activeFade: {
    promise: Promise<boolean>;
    resolve: (completed: boolean) => void;
    timer: ReturnType<typeof setTimeout>;
  } | null = null;

  // --- Audio graph helpers ---
  /**
   * A safety ceiling just under full scale. The stored per-song gain already
   * keeps peaks below it; this catches what that can't predict, such as the
   * lead vocal turned up or songs that haven't been measured yet. Reused for
   * the life of the audio context, like the analyser.
   */
  function setupLimiter() {
    if (!limiter && audioContext) {
      limiter = audioContext.createDynamicsCompressor();
      limiter.threshold.value = -1;
      limiter.knee.value = 0;
      limiter.ratio.value = 20;
      limiter.attack.value = 0.003;
      limiter.release.value = 0.1;
    }
  }

  function setupAnalyser() {
    if (!analyser && audioContext) {
      analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      // Default (0.8) smooths so heavily that the visualizer barely moves
      // frame to frame; lower this for a snappier, more reactive look.
      analyser.smoothingTimeConstant = 0.4;
    }
  }

  /**
   * Stop any fade in progress and put the volume back to full. Everything that
   * changes what is playing calls this, so a fade never outlives the song
   * position it was started on.
   */
  function cancelFade() {
    if (activeFade) {
      clearTimeout(activeFade.timer);
      activeFade.resolve(false);
      activeFade = null;
    }
    if (fadeGainNode) {
      fadeGainNode.gain.cancelScheduledValues(0);
      fadeGainNode.gain.value = 1;
    }
  }

  function stopSources() {
    for (const source of [
      instrumentalSource,
      vocalSource,
      backingVocalSource,
    ]) {
      if (!source) continue;
      // A deliberate stop is not the song ending.
      source.onended = null;
      try {
        source.stop();
      } catch {
        // Ignore if already stopped
      }
      source.disconnect();
    }
    instrumentalSource = null;
    vocalSource = null;
    backingVocalSource = null;
  }

  function clearIntervals() {
    if (animationFrameId) cancelAnimationFrame(animationFrameId);
    if (websocketInterval) clearInterval(websocketInterval);
    animationFrameId = null;
    websocketInterval = null;
  }

  function setupAudioGraph(
    offset: number,
    volumes: { vocal: number; backing: number; instrumental: number },
  ) {
    stopSources();

    if (!audioContext || !instrumentalBuffer || !vocalBuffer) return;
    const ctx = audioContext;

    const makeSource = (buffer: AudioBuffer) => {
      const source = ctx.createBufferSource();
      source.buffer = buffer;
      return source;
    };

    instrumentalSource = makeSource(instrumentalBuffer);
    vocalSource = makeSource(vocalBuffer);
    // Three-track songs only
    backingVocalSource = backingVocalBuffer
      ? makeSource(backingVocalBuffer)
      : null;

    // Create gain nodes for volume control
    instrumentalGain = ctx.createGain();
    instrumentalGain.gain.value = volumes.instrumental;
    vocalGain = ctx.createGain();
    vocalGain.gain.value = volumes.vocal;
    backingVocalGain = ctx.createGain();
    backingVocalGain.gain.value = volumes.backing;

    // Create or reuse the limiter and analyser nodes
    setupLimiter();
    setupAnalyser();

    // Create normalization gain node (converts dB to linear amplitude)
    if (normalizationGainNode) normalizationGainNode.disconnect();
    normalizationGainNode = ctx.createGain();
    normalizationGainNode.gain.value = Math.pow(10, normalizationGainDb / 20);

    // A fresh fade node per graph, at full volume: every play and seek starts
    // unfaded.
    if (fadeGainNode) fadeGainNode.disconnect();
    fadeGainNode = ctx.createGain();
    fadeGainNode.gain.value = 1;

    // Source -> VolumeGain -> NormalizationGain -> FadeGain -> Limiter -> Analyser -> Destination
    instrumentalSource.connect(instrumentalGain);
    vocalSource.connect(vocalGain);
    instrumentalGain.connect(normalizationGainNode);
    vocalGain.connect(normalizationGainNode);
    if (backingVocalSource) {
      backingVocalSource.connect(backingVocalGain);
      backingVocalGain.connect(normalizationGainNode);
    }
    normalizationGainNode.connect(fadeGainNode);
    fadeGainNode.connect(limiter!);
    limiter!.connect(analyser!);
    analyser!.connect(ctx.destination);

    // The instrumental is the reference track for the end of the song.
    // stopSources clears this handler first, so it only fires on a real end.
    instrumentalSource.onended = () => {
      const { isPlaying, duration } = get();
      if (!isPlaying) return;
      clearIntervals();
      playbackStartTime = null;
      playbackOffset = duration;
      set({ currentTime: duration, isPlaying: false, songEnded: true });
    };

    // Start every stem at the same instant, slightly ahead so none of them
    // misses it while the others are being started.
    const startAt = ctx.currentTime + 0.05;
    instrumentalSource.start(startAt, offset);
    vocalSource.start(startAt, offset);
    backingVocalSource?.start(startAt, offset);
    playbackStartTime = startAt;
  }

  function resetAudioNodes() {
    stopSources();
    if (audioContext) audioContext.close();
    audioContext = null;
    instrumentalBuffer = null;
    vocalBuffer = null;
    backingVocalBuffer = null;
    instrumentalGain = null;
    vocalGain = null;
    backingVocalGain = null;
    if (normalizationGainNode) {
      normalizationGainNode.disconnect();
      normalizationGainNode = null;
    }
    cancelFade();
    if (fadeGainNode) {
      fadeGainNode.disconnect();
      fadeGainNode = null;
    }
    limiter = null;
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
      cancelFade();
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

        // Fetch required tracks. /api/songs/{id}/download/{track} is served
        // unauthenticated (so <audio> elements can load it directly), so these
        // carry no Authorization header.
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

    play: (volumes) => {
      if (!audioContext) {
        audioContext = new window.AudioContext();
      }
      if (!instrumentalBuffer || !vocalBuffer) return;
      clearIntervals();
      cancelFade();

      // Reset songEnded flag when starting playback
      set({ songEnded: false });

      setupAudioGraph(playbackOffset, volumes);
      set({ isPlaying: true });
    },

    pause: () => {
      stopSources();
      // After stopping, so restoring the volume can't let a moment of the
      // song through at full level.
      cancelFade();
      clearIntervals();
      if (audioContext && playbackStartTime !== null) {
        // Clamped: a pause inside the short lead-in before the start would
        // otherwise step the position backwards.
        playbackOffset += Math.max(
          0,
          audioContext.currentTime - playbackStartTime,
        );
        playbackStartTime = null;
        set({ currentTime: playbackOffset, isPlaying: false });
      } else {
        set({ isPlaying: false });
      }
    },

    seek: (timeSeconds, volumes) => {
      if (!audioContext || !instrumentalBuffer || !vocalBuffer) return;
      clearIntervals();
      cancelFade();
      playbackOffset = timeSeconds;

      // Reset songEnded flag when seeking
      set({ songEnded: false });

      if (get().isPlaying) {
        setupAudioGraph(timeSeconds, volumes);
        set({ currentTime: timeSeconds });
      } else {
        playbackStartTime = null;
        set({ currentTime: timeSeconds, isPlaying: false });
      }
    },

    fadeOut: (ms: number) => {
      if (activeFade) return activeFade.promise;
      if (!get().isPlaying || !audioContext || !fadeGainNode) {
        return Promise.resolve(true);
      }

      const gain = fadeGainNode.gain;
      const now = audioContext.currentTime;
      gain.cancelScheduledValues(now);
      // A straight line in amplitude sounds like it holds and then drops off
      // at the end, because loudness tracks amplitude roughly as a square
      // root. Squaring the line makes the fall sound even all the way down.
      // The curve starts at the current level, so it needs no anchor event
      // (one at `now` would overlap the curve and throw).
      const start = gain.value;
      const steps = 64;
      const curve = new Float32Array(steps + 1);
      for (let i = 0; i <= steps; i++) {
        const remaining = 1 - i / steps;
        curve[i] = start * remaining * remaining;
      }
      gain.setValueCurveAtTime(curve, now, ms / 1000);

      let resolve!: (completed: boolean) => void;
      const promise = new Promise<boolean>((r) => {
        resolve = r;
      });
      const timer = setTimeout(() => {
        activeFade = null;
        resolve(true);
      }, ms);
      activeFade = { promise, resolve, timer };
      return promise;
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

    getFrequencyData: () => {
      if (!analyser) return null;
      const array = new Uint8Array(analyser.frequencyBinCount);
      analyser.getByteFrequencyData(array);
      return Array.from(array);
    },

    updatePlaybackState: (
      updates: Partial<
        Pick<PlaybackStateState, "isPlaying" | "currentTime" | "duration">
      >,
    ) => {
      set(updates);
    },

    startTimeUpdate: (onUpdate) => {
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
            playbackOffset +
            Math.max(0, audioContext.currentTime - playbackStartTime);
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
