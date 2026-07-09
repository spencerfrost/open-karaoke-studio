import React, { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { Pause, Play, TestTube2, Waves } from "lucide-react";

import AppLayout from "@/components/layout/AppLayout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { createLogger } from "@/lib/logger";

const logger = createLogger("page:admin-three-track-compare");

type CompareEngineKey =
  | "demucs_three_track"
  | "roformer_three_track"
  | "three_track_duality_v2"
  | "three_track_mel1143";
type EngineKey = CompareEngineKey | "original";
type StemKey = "vocals" | "backing" | "instrumental";

interface ManifestEngineResult {
  engine: string;
  success: boolean;
  duration_seconds: number;
}

interface ManifestSong {
  song_id: string;
  title: string | null;
  engines: ManifestEngineResult[];
}

interface CompareManifest {
  songs: ManifestSong[];
}

interface StemBuffers {
  vocals: AudioBuffer;
  backing: AudioBuffer;
  instrumental: AudioBuffer;
}

interface EngineRuntime {
  buffers: StemBuffers | null;
  originalBuffer: AudioBuffer | null;
  gains: Partial<Record<StemKey, GainNode>>;
  sources: Partial<Record<StemKey, AudioBufferSourceNode>>;
  originalGain: GainNode | null;
  originalSource: AudioBufferSourceNode | null;
}

interface SongOption {
  id: string;
  label: string;
  duration: number;
}

const STEMS: StemKey[] = ["vocals", "backing", "instrumental"];
const COMPARE_ENGINES: CompareEngineKey[] = [
  "demucs_three_track",
  "roformer_three_track",
  "three_track_duality_v2",
  "three_track_mel1143",
];
const ALL_ENGINES: EngineKey[] = [...COMPARE_ENGINES, "original"];
const ENGINE_LABEL: Record<EngineKey, string> = {
  demucs_three_track: "Demucs 3-Track",
  roformer_three_track: "Roformer 3-Track",
  three_track_duality_v2: "Duality V2",
  three_track_mel1143: "Mel1143",
  original: "Original Mix",
};
const DEFAULT_ENGINE: EngineKey = "demucs_three_track";

const DEFAULT_VOLUMES: Record<CompareEngineKey, Record<StemKey, number>> = {
  demucs_three_track: { vocals: 1, backing: 1, instrumental: 1 },
  roformer_three_track: { vocals: 1, backing: 1, instrumental: 1 },
  three_track_duality_v2: { vocals: 1, backing: 1, instrumental: 1 },
  three_track_mel1143: { vocals: 1, backing: 1, instrumental: 1 },
};

const STEM_FETCH_TIMEOUT_MS = 15000;
const STEM_DECODE_TIMEOUT_MS = 15000;

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

function formatTime(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) {
    return "00:00";
  }
  const total = Math.floor(seconds);
  const mins = Math.floor(total / 60)
    .toString()
    .padStart(2, "0");
  const secs = (total % 60).toString().padStart(2, "0");
  return `${mins}:${secs}`;
}

async function fetchArrayBufferWithTimeout(
  url: string,
  timeoutMs: number,
): Promise<ArrayBuffer> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      cache: "reload",
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new Error(`status ${response.status}`);
    }
    return await response.arrayBuffer();
  } finally {
    window.clearTimeout(timer);
  }
}

async function decodeBufferWithTimeout(
  context: AudioContext,
  data: ArrayBuffer,
  timeoutMs: number,
): Promise<AudioBuffer> {
  const decodePromise = context.decodeAudioData(data.slice(0));

  const timeoutPromise = new Promise<never>((_, reject) => {
    const timer = window.setTimeout(() => {
      window.clearTimeout(timer);
      reject(new Error("decode timeout"));
    }, timeoutMs);

    void decodePromise.finally(() => {
      window.clearTimeout(timer);
    });
  });

  return Promise.race([decodePromise, timeoutPromise]);
}

const AdminThreeTrackComparePage: React.FC = () => {
  const createEmptyRuntime = (): EngineRuntime => ({
    buffers: null,
    originalBuffer: null,
    gains: {},
    sources: {},
    originalGain: null,
    originalSource: null,
  });

  const audioContextRef = useRef<AudioContext | null>(null);
  const runtimesRef = useRef<Record<EngineKey, EngineRuntime>>({
    demucs_three_track: createEmptyRuntime(),
    roformer_three_track: createEmptyRuntime(),
    three_track_duality_v2: createEmptyRuntime(),
    three_track_mel1143: createEmptyRuntime(),
    original: createEmptyRuntime(),
  });
  const playbackOffsetRef = useRef(0);
  const playbackStartRef = useRef<number | null>(null);
  const activeEngineRef = useRef<EngineKey | null>(DEFAULT_ENGINE);
  const isPlayingRef = useRef(false);
  const isScrubbingRef = useRef(false);
  const rafRef = useRef<number | null>(null);
  const durationRef = useRef(0);

  const [manifest, setManifest] = useState<CompareManifest | null>(null);
  const [songId, setSongId] = useState<string>("");
  const [isLoadingManifest, setIsLoadingManifest] = useState(true);
  const [isLoadingAudio, setIsLoadingAudio] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [activeEngine, setActiveEngine] = useState<EngineKey>(DEFAULT_ENGINE);
  const [isPlaying, setIsPlaying] = useState(false);
  const [seekPreviewTime, setSeekPreviewTime] = useState<number | null>(null);
  const [volumes, setVolumes] = useState<
    Record<CompareEngineKey, Record<StemKey, number>>
  >(
    DEFAULT_VOLUMES,
  );

  const sharedVolumes = volumes.demucs_three_track;

  const songOptions = useMemo<SongOption[]>(() => {
    if (!manifest) return [];
    return manifest.songs.map((song) => {
      const maxDuration = song.engines.reduce((max, engine) => {
        return Math.max(max, engine.duration_seconds || 0);
      }, 0);
      return {
        id: song.song_id,
        label: song.title?.trim() || song.song_id,
        duration: maxDuration,
      };
    });
  }, [manifest]);

  const selectedSong = useMemo(
    () => songOptions.find((song) => song.id === songId) ?? null,
    [songId, songOptions],
  );

  const ensureAudioContext = async (): Promise<AudioContext> => {
    if (!audioContextRef.current) {
      audioContextRef.current = new window.AudioContext();
    }
    if (audioContextRef.current.state === "suspended") {
      await audioContextRef.current.resume();
    }
    return audioContextRef.current;
  };

  const stopAnimationFrame = () => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
  };

  const getCurrentOffset = (): number => {
    const context = audioContextRef.current;
    if (!context || !isPlayingRef.current || playbackStartRef.current === null) {
      return playbackOffsetRef.current;
    }
    const elapsed = context.currentTime - playbackStartRef.current;
    return clamp(playbackOffsetRef.current + elapsed, 0, durationRef.current);
  };

  const stopEngineSources = (engine: EngineKey) => {
    const runtime = runtimesRef.current[engine];

    if (runtime.originalSource) {
      try {
        runtime.originalSource.onended = null;
        runtime.originalSource.stop();
      } catch {
        // No-op.
      }
      runtime.originalSource = null;
      runtime.originalGain = null;
    }

    STEMS.forEach((stem) => {
      const source = runtime.sources[stem];
      if (!source) return;
      try {
        source.onended = null;
        source.stop();
      } catch {
        // No-op.
      }
    });
    runtime.sources = {};
  };

  const stopPlayback = (keepOffset: boolean) => {
    if (keepOffset) {
      playbackOffsetRef.current = getCurrentOffset();
    }

    ALL_ENGINES.forEach((engine) => stopEngineSources(engine));
    stopAnimationFrame();

    playbackStartRef.current = null;
    isPlayingRef.current = false;
    setIsPlaying(false);
    setCurrentTime(playbackOffsetRef.current);
  };

  const startTimeLoop = () => {
    stopAnimationFrame();

    const tick = () => {
      const offset = getCurrentOffset();
      if (!isScrubbingRef.current) {
        setCurrentTime(offset);
      }

      if (offset >= durationRef.current && isPlayingRef.current) {
        playbackOffsetRef.current = durationRef.current;
        stopPlayback(false);
        return;
      }

      if (isPlayingRef.current) {
        rafRef.current = requestAnimationFrame(tick);
      }
    };

    rafRef.current = requestAnimationFrame(tick);
  };

  const startEnginePlayback = async (engine: EngineKey, fromOffset: number) => {
    const context = await ensureAudioContext();
    const runtime = runtimesRef.current[engine];

    if (engine === "original") {
      if (!runtime.originalBuffer) {
        toast.error("Original mix is not loaded yet");
        return;
      }

      stopEngineSources(engine);

      const source = context.createBufferSource();
      source.buffer = runtime.originalBuffer;

      const gain = context.createGain();
      gain.gain.value = 1;

      source.connect(gain);
      gain.connect(context.destination);

      const effectiveOffset = clamp(fromOffset, 0, durationRef.current);
      source.start(0, effectiveOffset);

      source.onended = () => {
        if (!isPlayingRef.current || activeEngineRef.current !== engine) {
          return;
        }

        playbackOffsetRef.current = durationRef.current;
        stopPlayback(false);
      };

      runtime.originalSource = source;
      runtime.originalGain = gain;

      playbackOffsetRef.current = effectiveOffset;
      playbackStartRef.current = context.currentTime;
      activeEngineRef.current = engine;
      isPlayingRef.current = true;

      setActiveEngine(engine);
      setIsPlaying(true);
      startTimeLoop();
      return;
    }

    if (!runtime.buffers) {
      toast.error(`${ENGINE_LABEL[engine]} is not loaded yet`);
      return;
    }

    stopEngineSources(engine);

    const localSources: Partial<Record<StemKey, AudioBufferSourceNode>> = {};

    STEMS.forEach((stem) => {
      const source = context.createBufferSource();
      source.buffer = runtime.buffers![stem];

      const gain = context.createGain();
      gain.gain.value = volumes[engine][stem];

      source.connect(gain);
      gain.connect(context.destination);

      runtime.gains[stem] = gain;
      localSources[stem] = source;
    });

    runtime.sources = localSources;

    const effectiveOffset = clamp(fromOffset, 0, durationRef.current);
    Object.values(localSources).forEach((source) => source?.start(0, effectiveOffset));

    const referenceStem = localSources.instrumental;
    if (referenceStem) {
      referenceStem.onended = () => {
        if (!isPlayingRef.current || activeEngineRef.current !== engine) {
          return;
        }

        playbackOffsetRef.current = durationRef.current;
        stopPlayback(false);
      };
    }

    playbackOffsetRef.current = effectiveOffset;
    playbackStartRef.current = context.currentTime;
    activeEngineRef.current = engine;
    isPlayingRef.current = true;

    setActiveEngine(engine);
    setIsPlaying(true);
    startTimeLoop();
  };

  const handlePlayEngine = async (engine: EngineKey) => {
    try {
      const switchOffset = getCurrentOffset();
      playbackOffsetRef.current = switchOffset;
      stopPlayback(false);
      await startEnginePlayback(engine, switchOffset);
    } catch (error) {
      logger.error("Failed to start engine playback", error);
      toast.error("Failed to start playback");
    }
  };

  const handlePause = () => {
    stopPlayback(true);
  };

  const handleSeek = async (nextTime: number) => {
    const clamped = clamp(nextTime, 0, durationRef.current);
    playbackOffsetRef.current = clamped;
    setCurrentTime(clamped);

    if (!isPlayingRef.current) {
      return;
    }

    const currentEngine = activeEngineRef.current ?? activeEngine;
    stopPlayback(false);
    await startEnginePlayback(currentEngine, clamped);
  };

  const handleSeekPreview = (nextTime: number) => {
    isScrubbingRef.current = true;
    setSeekPreviewTime(nextTime);
  };

  const handleSeekCommit = async (nextTime: number) => {
    const clamped = clamp(nextTime, 0, durationRef.current);
    setSeekPreviewTime(clamped);
    try {
      await handleSeek(clamped);
    } finally {
      isScrubbingRef.current = false;
      setSeekPreviewTime(null);
    }
  };

  const handleSharedVolumeChange = (stem: StemKey, value: number) => {
    setVolumes((current) => {
      const updated = COMPARE_ENGINES.reduce(
        (acc, engine) => {
          acc[engine] = {
            ...current[engine],
            [stem]: value,
          };
          return acc;
        },
        {} as Record<CompareEngineKey, Record<StemKey, number>>,
      );

      COMPARE_ENGINES.forEach((engine) => {
        const gainNode = runtimesRef.current[engine].gains[stem];
        if (gainNode) {
          gainNode.gain.value = value;
        }
      });

      return updated;
    });
  };

  const resetVolumes = (engine: EngineKey) => {
    STEMS.forEach((stem) => {
      const gainNode = runtimesRef.current[engine].gains[stem];
      if (gainNode) {
        gainNode.gain.value = 1;
      }
    });

    setVolumes((current) => ({
      ...current,
      [engine]: { vocals: 1, backing: 1, instrumental: 1 },
    }));
  };

  const resetSharedVolumes = () => {
    COMPARE_ENGINES.forEach((engine) => {
      STEMS.forEach((stem) => {
        const gainNode = runtimesRef.current[engine].gains[stem];
        if (gainNode) {
          gainNode.gain.value = 1;
        }
      });
    });

    setVolumes({ ...DEFAULT_VOLUMES });
  };

  const handleEngineToggle = async (value: string) => {
    if (value !== "original" && !COMPARE_ENGINES.includes(value as CompareEngineKey)) {
      return;
    }

    const nextEngine = value as EngineKey;
    setActiveEngine(nextEngine);
    activeEngineRef.current = nextEngine;

    if (isPlayingRef.current) {
      await handlePlayEngine(nextEngine);
    }
  };

  const decodeSong = async (selectedSongId: string) => {
    setIsLoadingAudio(true);
    stopPlayback(false);

    const decodeContext = new window.AudioContext();

    try {
      const nextRuntimes: Record<EngineKey, EngineRuntime> = {
        demucs_three_track: createEmptyRuntime(),
        roformer_three_track: createEmptyRuntime(),
        three_track_duality_v2: createEmptyRuntime(),
        three_track_mel1143: createEmptyRuntime(),
        original: createEmptyRuntime(),
      };

      for (const engine of COMPARE_ENGINES) {
        const [vocals, backing, instrumental] = await Promise.all([
          fetchArrayBufferWithTimeout(
            `/three-track-compare/${selectedSongId}/${engine}/vocals.mp3`,
            STEM_FETCH_TIMEOUT_MS,
          ).then((buffer) =>
            decodeBufferWithTimeout(decodeContext, buffer, STEM_DECODE_TIMEOUT_MS),
          ),
          fetchArrayBufferWithTimeout(
            `/three-track-compare/${selectedSongId}/${engine}/backing_vocals.mp3`,
            STEM_FETCH_TIMEOUT_MS,
          ).then((buffer) =>
            decodeBufferWithTimeout(decodeContext, buffer, STEM_DECODE_TIMEOUT_MS),
          ),
          fetchArrayBufferWithTimeout(
            `/three-track-compare/${selectedSongId}/${engine}/instrumental.mp3`,
            STEM_FETCH_TIMEOUT_MS,
          ).then((buffer) =>
            decodeBufferWithTimeout(decodeContext, buffer, STEM_DECODE_TIMEOUT_MS),
          ),
        ]);

        nextRuntimes[engine].buffers = { vocals, backing, instrumental };
      }

      const originalBuffer = await fetchArrayBufferWithTimeout(
        `/three-track-compare/${selectedSongId}/original.mp3`,
        STEM_FETCH_TIMEOUT_MS,
      ).then((buffer) =>
        decodeBufferWithTimeout(decodeContext, buffer, STEM_DECODE_TIMEOUT_MS),
      );
      nextRuntimes.original.originalBuffer = originalBuffer;

      runtimesRef.current = nextRuntimes;

      const nextDuration = Math.max(
        originalBuffer.duration,
        ...COMPARE_ENGINES.map((engine) => {
          const buffers = nextRuntimes[engine].buffers;
          if (!buffers) return 0;
          return Math.max(
            buffers.vocals.duration,
            buffers.backing.duration,
            buffers.instrumental.duration,
          );
        }),
      );

      durationRef.current = nextDuration;
      playbackOffsetRef.current = 0;
      playbackStartRef.current = null;

      setCurrentTime(0);
      setDuration(nextDuration);
      setIsPlaying(false);
      activeEngineRef.current = DEFAULT_ENGINE;
      setActiveEngine(DEFAULT_ENGINE);
    } catch (error) {
      logger.error("Failed to decode audio assets", error);
      toast.error(
        "Could not load test tracks. Ensure frontend/public/three-track-compare is available.",
      );
      runtimesRef.current = {
        demucs_three_track: createEmptyRuntime(),
        roformer_three_track: createEmptyRuntime(),
        three_track_duality_v2: createEmptyRuntime(),
        three_track_mel1143: createEmptyRuntime(),
        original: createEmptyRuntime(),
      };
      durationRef.current = 0;
      setDuration(0);
      setCurrentTime(0);
      activeEngineRef.current = DEFAULT_ENGINE;
      setActiveEngine(DEFAULT_ENGINE);
      setIsPlaying(false);
    } finally {
      void decodeContext.close();
      setIsLoadingAudio(false);
    }
  };

  useEffect(() => {
    let cancelled = false;

    const loadManifest = async () => {
      try {
        const response = await fetch("/three-track-compare/manifest.json", {
          cache: "reload",
        });
        if (!response.ok) {
          throw new Error(`manifest status=${response.status}`);
        }

        const data = (await response.json()) as CompareManifest;
        if (cancelled) return;

        setManifest(data);
        if (data.songs.length > 0) {
          setSongId(data.songs[0].song_id);
        }
      } catch (error) {
        logger.error("Failed to load compare manifest", error);
        toast.error(
          "Could not load compare manifest. Add test assets under frontend/public/three-track-compare.",
        );
      } finally {
        if (!cancelled) {
          setIsLoadingManifest(false);
        }
      }
    };

    loadManifest();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!songId) return;
    void decodeSong(songId);
    // decodeSong is intentionally treated as an imperative loader for song changes only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [songId]);

  useEffect(() => {
    return () => {
      stopPlayback(false);
      ALL_ENGINES.forEach((engine) => stopEngineSources(engine));
      if (audioContextRef.current) {
        void audioContextRef.current.close();
      }
    };
    // Teardown should run only on unmount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <AppLayout>
      <div className="max-w-6xl mx-auto pb-8 space-y-4">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold flex items-center gap-2">
                <Waves className="h-6 w-6 text-primary" />
                Three-Track Compare
              </h1>
              <Badge variant="secondary" className="gap-1">
                <TestTube2 className="h-3 w-3" />
                Temporary Tool
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              Compare all generated three-track engines with one shared timeline. Backing vocal A/B is not fully apples-to-apples.
            </p>
          </div>

          <div className="w-full sm:w-[340px]">
            <Select value={songId} onValueChange={setSongId} disabled={isLoadingManifest || songOptions.length === 0}>
              <SelectTrigger>
                <SelectValue placeholder="Select test song" />
              </SelectTrigger>
              <SelectContent>
                {songOptions.map((song) => (
                  <SelectItem key={song.id} value={song.id}>
                    {song.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Compare Controls</CardTitle>
            <CardDescription>
              Shared transport and shared stem mix for both engines.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="space-y-2">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Engine</p>
              <ToggleGroup
                type="single"
                value={activeEngine}
                onValueChange={(value) => void handleEngineToggle(value)}
                variant="outline"
                className="w-full justify-start"
              >
                <ToggleGroupItem value="demucs_three_track" className="px-4">
                  Demucs
                </ToggleGroupItem>
                <ToggleGroupItem value="roformer_three_track" className="px-4">
                  Roformer
                </ToggleGroupItem>
                <ToggleGroupItem value="three_track_duality_v2" className="px-4">
                  Duality V2
                </ToggleGroupItem>
                <ToggleGroupItem value="three_track_mel1143" className="px-4">
                  Mel1143
                </ToggleGroupItem>
                <ToggleGroupItem value="original" className="px-4">
                  Original
                </ToggleGroupItem>
              </ToggleGroup>
            </div>

            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant={isPlaying ? "secondary" : "default"}
                onClick={isPlaying ? handlePause : () => void handlePlayEngine(activeEngine)}
                disabled={isLoadingAudio}
              >
                {isPlaying ? <Pause className="h-4 w-4 mr-1" /> : <Play className="h-4 w-4 mr-1" />}
                {isPlaying ? "Pause" : `Play ${ENGINE_LABEL[activeEngine]}`}
              </Button>
              <Badge variant="outline">{formatTime(currentTime)}</Badge>
              <span className="text-xs text-muted-foreground">/</span>
              <Badge variant="outline">{formatTime(duration)}</Badge>
              {isLoadingAudio && <Badge variant="secondary">Loading tracks...</Badge>}
            </div>

            <Slider
              min={0}
              max={Math.max(duration, 0.1)}
              step={0.05}
              value={[seekPreviewTime ?? currentTime]}
              onValueChange={([value]) => handleSeekPreview(value)}
              onValueCommit={([value]) => void handleSeekCommit(value)}
              disabled={isLoadingAudio || duration <= 0}
            />

            {STEMS.map((stem) => (
              <div key={`shared-${stem}`} className="space-y-1">
                <div className="flex items-center justify-between text-sm">
                  <span className="capitalize">{stem === "backing" ? "Backing Vocals" : stem}</span>
                  <span className="text-xs text-muted-foreground">
                    {Math.round(sharedVolumes[stem] * 100)}%
                  </span>
                </div>
                <Slider
                  min={0}
                  max={1.5}
                  step={0.01}
                  value={[sharedVolumes[stem]]}
                  onValueChange={([value]) => handleSharedVolumeChange(stem, value)}
                  disabled={isLoadingAudio || activeEngine === "original"}
                />
              </div>
            ))}

            <Button
              type="button"
              variant="outline"
              className="w-full"
              onClick={resetSharedVolumes}
              disabled={activeEngine === "original"}
            >
              Reset Shared Volumes
            </Button>
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  );
};

export default AdminThreeTrackComparePage;
