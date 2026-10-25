/**
 * PreviewPlayer - one audio preview for the whole add-song flow.
 *
 * A single <audio> lives in the provider, so starting a preview from any row
 * pauses whatever was playing, and the preview keeps going while someone moves
 * between the search, artist and album screens. The bar at the bottom shows
 * what's playing.
 *
 * The audio streams from /api/youtube/preview/:videoId, which redirects to
 * YouTube's own audio URL.
 */

import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { Loader2, Pause, Play, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { createLogger } from "@/lib/logger";
import { formatTime } from "@/utils/formatters";
import {
  PreviewApiContext,
  PreviewStateContext,
  usePreviewApi,
  usePreviewState,
  type PreviewState,
  type PreviewTrack,
} from "./previewContext";

const logger = createLogger("component:PreviewPlayer");

export const PreviewProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [state, setState] = useState<PreviewState>({
    track: null,
    status: "paused",
    currentTime: 0,
    duration: 0,
  });
  const trackRef = useRef<PreviewTrack | null>(null);

  const play = useCallback((audio: HTMLAudioElement) => {
    audio.play().catch((error: unknown) => {
      // A newer toggle interrupting this one isn't a failure.
      if (error instanceof DOMException && error.name === "AbortError") return;
      logger.error("Preview playback failed", error);
      setState((s) => ({ ...s, status: "error" }));
    });
  }, []);

  const toggle = useCallback(
    (track: PreviewTrack) => {
      const audio = audioRef.current;
      if (!audio) return;

      if (trackRef.current?.videoId === track.videoId) {
        if (audio.paused) {
          setState((s) => ({ ...s, status: "loading" }));
          play(audio);
        } else {
          audio.pause();
        }
        return;
      }

      trackRef.current = track;
      setState({ track, status: "loading", currentTime: 0, duration: 0 });
      audio.src = `/api/youtube/preview/${encodeURIComponent(track.videoId)}`;
      play(audio);
    },
    [play],
  );

  const stop = useCallback(() => {
    const audio = audioRef.current;
    trackRef.current = null;
    if (audio) {
      audio.pause();
      audio.removeAttribute("src");
      audio.load();
    }
    setState({ track: null, status: "paused", currentTime: 0, duration: 0 });
  }, []);

  // Leaving the add flow ends the preview.
  useEffect(() => {
    const audio = audioRef.current;
    return () => audio?.pause();
  }, []);

  const api = useMemo(() => ({ toggle, stop }), [toggle, stop]);

  return (
    <PreviewApiContext.Provider value={api}>
      <PreviewStateContext.Provider value={state}>
        {children}
        <audio
          ref={audioRef}
          preload="none"
          onPlaying={() => setState((s) => ({ ...s, status: "playing" }))}
          onWaiting={() => setState((s) => ({ ...s, status: "loading" }))}
          onPause={() =>
            setState((s) =>
              s.status === "error" ? s : { ...s, status: "paused" },
            )
          }
          onEnded={() =>
            setState((s) => ({ ...s, status: "paused", currentTime: 0 }))
          }
          onError={() =>
            setState((s) => (s.track ? { ...s, status: "error" } : s))
          }
          onTimeUpdate={(e) => {
            const currentTime = e.currentTarget.currentTime;
            setState((s) => ({ ...s, currentTime }));
          }}
          onLoadedMetadata={(e) => {
            const duration = e.currentTarget.duration;
            setState((s) => ({
              ...s,
              duration: Number.isFinite(duration) ? duration : 0,
            }));
          }}
        />
      </PreviewStateContext.Provider>
    </PreviewApiContext.Provider>
  );
};

/** The bar at the bottom of the flow: what's previewing, pause, progress. */
export const PreviewBar: React.FC = () => {
  const { toggle, stop } = usePreviewApi();
  const { track, status, currentTime, duration } = usePreviewState();
  if (!track) return null;

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0;
  const label = status === "playing" ? "Pause preview" : "Play preview";

  return (
    <Card
      variant="surface"
      role="region"
      aria-label="Preview"
      className="sticky bottom-2 z-30 mx-auto w-full max-w-2xl shadow-lg"
    >
      <div className="flex items-center gap-3 px-3 pt-2.5 pb-2">
        <Button
          variant="primary"
          size="icon-lg"
          className="size-11 rounded-full"
          aria-label={label}
          onClick={() => toggle(track)}
        >
          {status === "loading" ? (
            <Loader2 className="animate-spin" />
          ) : status === "playing" ? (
            <Pause />
          ) : (
            <Play className="ml-0.5" />
          )}
        </Button>
        <div className="min-w-0 flex-1">
          <div className="text-section-label text-xs font-extrabold tracking-widest uppercase">
            {status === "error" ? "Preview didn't load" : "Previewing"}
          </div>
          <div className="truncate font-semibold">
            {track.title} · {track.artist}
          </div>
        </div>
        <span className="text-foreground-dim text-sm tabular-nums">
          {formatTime(currentTime)}
        </span>
        <Button
          variant="ghost"
          size="icon"
          className="text-foreground-dim"
          aria-label="Close preview"
          onClick={stop}
        >
          <X />
        </Button>
      </div>
      <Progress value={progress} className="h-1 rounded-none" />
    </Card>
  );
};
