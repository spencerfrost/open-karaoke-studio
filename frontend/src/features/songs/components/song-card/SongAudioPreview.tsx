import React, {
  useState,
  useRef,
  useEffect,
  useCallback,
  useImperativeHandle,
} from "react";
import { Play, Pause } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { formatTime } from "@/utils/formatters";

export type PreviewTrack =
  | "original"
  | "vocals"
  | "instrumental"
  | "backing-vocals";

/** Lets something shown alongside the player move it, e.g. a clicked lyric. */
export interface SongAudioPreviewHandle {
  /** Jump to a spot (seconds) and play from there. Called just after the
   * track changes, it plays the new track from that spot. */
  playFrom: (seconds: number) => void;
  /** Stop where it is, e.g. at the end of a clip. */
  pause: () => void;
}

interface SongAudioPreviewProps {
  songId: string;
  /** Which file to play. Switching it mid-song carries on from the same spot. */
  track?: PreviewTrack;
  /**
   * The playing position (seconds): every frame while playing, and after any
   * seek. For something that has to keep in step with the audio.
   */
  onTimeChange?: (seconds: number) => void;
  ref?: React.Ref<SongAudioPreviewHandle>;
  className?: string;
}

export const SongAudioPreview: React.FC<SongAudioPreviewProps> = ({
  songId,
  track = "original",
  onTimeChange,
  ref,
  className,
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const audioRef = useRef<HTMLAudioElement>(null);
  const progressRef = useRef<HTMLDivElement>(null);

  const audioUrl = `/api/songs/${songId}/download/${track}`;

  // A different track: remember the spot to pick up from once it loads, and
  // clear the old file's error.
  const [loadedUrl, setLoadedUrl] = useState(audioUrl);
  const [resume, setResume] = useState<{
    time: number;
    playing: boolean;
  } | null>(null);
  if (loadedUrl !== audioUrl) {
    setLoadedUrl(audioUrl);
    setResume({ time: currentTime, playing: isPlaying });
    setError(null);
    setIsPlaying(false);
  }

  // Stop audio on unmount (e.g. drawer close)
  useEffect(() => {
    const audio = audioRef.current;
    return () => {
      if (audio) {
        audio.pause();
        audio.currentTime = 0;
      }
    };
  }, []);

  const handleLoadedMetadata = useCallback(() => {
    setIsLoading(false);
    setError(null);
    const audio = audioRef.current;
    if (!audio) return;
    setDuration(audio.duration);

    if (!resume) return;
    setResume(null);
    audio.currentTime = resume.time;
    if (resume.playing) {
      audio
        .play()
        .then(() => setIsPlaying(true))
        .catch(() => setError("Failed to play audio"));
    }
  }, [resume]);

  const handleError = useCallback(() => {
    setIsLoading(false);
    setError("Failed to load audio");
    setIsPlaying(false);
  }, []);

  const handleTimeUpdate = useCallback(() => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
      onTimeChange?.(audioRef.current.currentTime);
    }
  }, [onTimeChange]);

  const handleEnded = useCallback(() => {
    setIsPlaying(false);
    setCurrentTime(0);
    onTimeChange?.(0);
  }, [onTimeChange]);

  // timeupdate fires only a few times a second: too coarse for a word sweep.
  useEffect(() => {
    if (!isPlaying || !onTimeChange) return;
    let frame = 0;
    const tick = () => {
      if (audioRef.current) onTimeChange(audioRef.current.currentTime);
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [isPlaying, onTimeChange]);

  const startPlaying = () => {
    if (!audioRef.current) return;
    setIsLoading(true);
    setError(null);
    audioRef.current
      .play()
      .then(() => {
        setIsPlaying(true);
        setIsLoading(false);
      })
      .catch(() => {
        setError("Failed to play audio");
        setIsLoading(false);
        setIsPlaying(false);
      });
  };

  const handlePlayPause = () => {
    if (!audioRef.current) return;

    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
      return;
    }

    startPlaying();
  };

  useImperativeHandle(ref, () => ({
    playFrom: (seconds: number) => {
      if (!audioRef.current) return;
      if (resume) {
        // The track is switching: start the new one here, not where the old
        // one was.
        setResume({ time: seconds, playing: true });
        setCurrentTime(seconds);
        return;
      }
      audioRef.current.currentTime = seconds;
      setCurrentTime(seconds);
      if (!isPlaying) startPlaying();
    },
    pause: () => {
      if (!audioRef.current || !isPlaying) return;
      audioRef.current.pause();
      setIsPlaying(false);
    },
  }));

  const handleProgressClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!audioRef.current || !progressRef.current || duration === 0) return;

    const rect = progressRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickRatio = clickX / rect.width;
    const newTime = clickRatio * duration;

    audioRef.current.currentTime = newTime;
    setCurrentTime(newTime);
  };

  const progressPercentage = duration > 0 ? (currentTime / duration) * 100 : 0;

  return (
    <div className={cn("space-y-2", className)}>
      <audio
        ref={audioRef}
        src={audioUrl}
        onLoadedMetadata={handleLoadedMetadata}
        onError={handleError}
        onTimeUpdate={handleTimeUpdate}
        onEnded={handleEnded}
        preload="metadata"
      />

      <div className="flex items-center gap-3">
        <Button
          variant="outline"
          size="icon"
          onClick={handlePlayPause}
          disabled={!!error}
          className="size-9 shrink-0 rounded-full"
        >
          {isLoading ? (
            <div className="animate-spin rounded-full size-4 border-2 border-current border-t-transparent" />
          ) : isPlaying ? (
            <Pause size={16} />
          ) : (
            <Play size={16} className="ml-0.5" />
          )}
        </Button>

        <div className="flex-1 space-y-1">
          <div
            ref={progressRef}
            className="w-full h-1.5 bg-muted rounded-full cursor-pointer"
            onClick={handleProgressClick}
          >
            <div
              className="h-full bg-primary rounded-full transition-all duration-100"
              style={{ width: `${Math.min(progressPercentage, 100)}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>{formatTime(currentTime)}</span>
            <span>{duration > 0 ? formatTime(duration) : "--:--"}</span>
          </div>
        </div>
      </div>

      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
};
