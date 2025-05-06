import { useRef, useState, useCallback } from "react";

interface UseWebAudioKaraokeOptions {
  instrumentalUrl: string;
  vocalUrl: string;
}

export function useWebAudioKaraoke({
  instrumentalUrl,
  vocalUrl,
}: UseWebAudioKaraokeOptions) {
  const audioContextRef = useRef<AudioContext | null>(null);
  const instrumentalBufferRef = useRef<AudioBuffer | null>(null);
  const vocalBufferRef = useRef<AudioBuffer | null>(null);
  const instrumentalSourceRef = useRef<AudioBufferSourceNode | null>(null);
  const vocalSourceRef = useRef<AudioBufferSourceNode | null>(null);
  const instrumentalGainRef = useRef<GainNode | null>(null);
  const vocalGainRef = useRef<GainNode | null>(null);

  const [isReady, setIsReady] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [vocalVolume, setVocalVolume] = useState(1);
  const [instrumentalVolume, setInstrumentalVolume] = useState(1);
  const [error, setError] = useState<string | null>(null);

  // Load and decode both tracks
  const load = useCallback(async () => {
    try {
      setError(null);
      if (!audioContextRef.current) {
        audioContextRef.current = new window.AudioContext();
      }
      const ctx = audioContextRef.current;
      // Fetch and decode
      const [instArr, vocArr] = await Promise.all([
        fetch(instrumentalUrl).then((r) => r.arrayBuffer()),
        fetch(vocalUrl).then((r) => r.arrayBuffer()),
      ]);
      const [instBuf, vocBuf] = await Promise.all([
        ctx.decodeAudioData(instArr.slice(0)),
        ctx.decodeAudioData(vocArr.slice(0)),
      ]);
      instrumentalBufferRef.current = instBuf;
      vocalBufferRef.current = vocBuf;
      setDuration(instBuf.duration);
      setIsReady(true);
    } catch (e) {
      setError("Failed to load or decode audio.");
    }
  }, [instrumentalUrl, vocalUrl]);

  // Play both tracks in sync
  const play = useCallback(
    (offset = 0) => {
      if (
        !audioContextRef.current ||
        !instrumentalBufferRef.current ||
        !vocalBufferRef.current
      )
        return;
      const ctx = audioContextRef.current;
      // Clean up any previous sources
      instrumentalSourceRef.current?.stop();
      vocalSourceRef.current?.stop();

      // Create sources
      const instSource = ctx.createBufferSource();
      instSource.buffer = instrumentalBufferRef.current;
      const vocSource = ctx.createBufferSource();
      vocSource.buffer = vocalBufferRef.current;

      // Create gain nodes
      const instGain = ctx.createGain();
      instGain.gain.value = instrumentalVolume;
      const vocGain = ctx.createGain();
      vocGain.gain.value = vocalVolume;

      // Connect graph
      instSource.connect(instGain).connect(ctx.destination);
      vocSource.connect(vocGain).connect(ctx.destination);

      // Store refs
      instrumentalSourceRef.current = instSource;
      vocalSourceRef.current = vocSource;
      instrumentalGainRef.current = instGain;
      vocalGainRef.current = vocGain;

      // Start in sync
      const now = ctx.currentTime;
      instSource.start(now, offset);
      vocSource.start(now, offset);

      setIsPlaying(true);

      // Track time
      const interval = setInterval(() => {
        setCurrentTime(ctx.currentTime - now + offset);
      }, 100);

      instSource.onended = () => {
        setIsPlaying(false);
        clearInterval(interval);
      };
    },
    [instrumentalVolume, vocalVolume]
  );

  // Pause (stop both sources)
  const pause = useCallback(() => {
    instrumentalSourceRef.current?.stop();
    vocalSourceRef.current?.stop();
    setIsPlaying(false);
  }, []);

  // Seek (stop and re-play at new offset)
  const seek = useCallback(
    (time: number) => {
      pause();
      play(time);
      setCurrentTime(time);
    },
    [pause, play]
  );

  // Volume controls
  const setVocalVol = (vol: number) => {
    setVocalVolume(vol);
    vocalGainRef.current && (vocalGainRef.current.gain.value = vol);
  };
  const setInstrumentalVol = (vol: number) => {
    setInstrumentalVolume(vol);
    instrumentalGainRef.current &&
      (instrumentalGainRef.current.gain.value = vol);
  };

  // Cleanup
  const cleanup = useCallback(() => {
    pause();
    audioContextRef.current?.close();
    audioContextRef.current = null;
    setIsReady(false);
  }, [pause]);

  return {
    isReady,
    isPlaying,
    currentTime,
    duration,
    error,
    load,
    play,
    pause,
    seek,
    setVocalVol,
    setInstrumentalVol,
    cleanup,
    vocalVolume,
    instrumentalVolume,
  };
}
