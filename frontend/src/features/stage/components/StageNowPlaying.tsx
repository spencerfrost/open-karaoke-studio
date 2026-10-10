/**
 * StageNowPlaying - the footer that says what's playing while someone browses
 * for what's next. The same idea as a media player's now-playing bar.
 *
 * It is also the way back to the song: clicking anywhere but play/pause goes
 * wherever Back would. Part of the screen's layout, not floating over it, so
 * there is nothing to close or drag.
 *
 * Time left rather than time elapsed: during a long outro the room's question
 * is "how long is this going to go on?"
 *
 * Several hundred wheel rows sit on the same screen, so this is careful about
 * what re-renders: it reads narrow store slices, and only the progress parts
 * subscribe to `currentTime`, which ticks every frame.
 */

import React from "react";
import { ChevronRight, Mic, Pause, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import ProgressBar from "@/features/player/components/subcomponents/ProgressBar";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import { usePlaybackStateStore } from "@/stores/usePlaybackStateStore";
import { cn } from "@/lib/utils";
import { formatTime } from "@/utils/formatters";
import { useStageQueue, useStageShell } from "../StageShellContext";
import { findTurnItem } from "../turnItem";

/** The only parts that re-render as the song plays. */
const NowPlayingProgress: React.FC = () => {
  const currentTime = usePlaybackStateStore((state) => state.currentTime);
  const duration = usePlaybackStateStore((state) => state.duration);

  return (
    <>
      {/* Display only: a stray click from the mic stand must not seek. */}
      <ProgressBar
        currentTime={currentTime}
        duration={duration}
        className="min-w-24 flex-1"
      />
      <span className="w-28 shrink-0 text-right font-accent text-xl tabular-nums text-foreground/70">
        {formatTime(Math.max(0, duration - currentTime))} left
      </span>
    </>
  );
};

// `relative`: song select paints its blurred backdrop as an absolute layer,
// and only positioned elements after it are drawn on top. Left static, the
// footer sat under it, dimmed and unclickable.
const footerClass =
  "relative flex h-14 shrink-0 items-center gap-4 border-t border-foreground/10 px-6";

const StageNowPlaying: React.FC = () => {
  const shell = useStageShell();
  const queue = useStageQueue();
  const songId = usePlaybackStateStore((state) => state.songId);
  const isReady = usePlaybackStateStore((state) => state.isReady);
  const isPlaying = usePlaybackStateStore((state) => state.isPlaying);
  const songEnded = usePlaybackStateStore((state) => state.songEnded);
  const userPlay = useKaraokePlayerStore((state) => state.userPlay);
  const userPause = useKaraokePlayerStore((state) => state.userPause);

  const current = queue?.current;
  if (!current || !songId) return null;

  if (songEnded) {
    const turn = queue.turn;
    const next = findTurnItem(turn, queue.upcoming);
    const message = next ? (
      <>
        Song's over:{" "}
        <strong className="text-foreground">{turn.performerName}</strong>'s up
        with <em className="text-foreground">{next.song.title}</em>
      </>
    ) : turn.performerName ? (
      <>
        Song's over: pick a song for{" "}
        <strong className="text-foreground">{turn.performerName}</strong>
      </>
    ) : (
      "Song's over: pick the next song"
    );

    // Nothing queued for them: the library is already the right place, so
    // there is nowhere for a click to go.
    if (!next) {
      return (
        <footer className={footerClass}>
          <span className="truncate text-xl text-foreground/70">{message}</span>
        </footer>
      );
    }
    return (
      <footer className={footerClass}>
        <button
          type="button"
          onClick={() => shell?.openHandoff()}
          className="group flex h-full min-w-0 flex-1 items-center gap-3 text-left"
        >
          <span className="truncate text-xl text-foreground/70">{message}</span>
          <ChevronRight className="size-6 shrink-0 text-foreground/40 transition-colors group-hover:text-foreground" />
        </button>
      </footer>
    );
  }

  return (
    <footer className={footerClass}>
      <Button
        variant="ghost"
        size="icon"
        disabled={!isReady}
        onClick={isPlaying ? userPause : userPlay}
        aria-label={isPlaying ? "Pause" : "Play"}
        className="size-9 shrink-0 text-foreground/80 hover:text-foreground"
      >
        {isPlaying ? (
          <Pause className="size-6" fill="currentColor" />
        ) : (
          <Play className="size-6" fill="currentColor" />
        )}
      </Button>

      <button
        type="button"
        onClick={() => shell?.openPerformance()}
        aria-label="Back to the song"
        className="group flex h-full min-w-0 flex-1 items-center gap-6 text-left"
      >
        {/* One line. The song truncates before the singer does: the name is
            short and is who the room is looking for. */}
        <span className="flex min-w-0 max-w-[50%] shrink items-center gap-4 text-xl">
          <span className="min-w-0 truncate">
            <span className="text-foreground">{current.song.title}</span>
            <span className="text-foreground/50">
              {" · "}
              {current.song.artist}
            </span>
          </span>
          <span className="flex shrink-0 items-center gap-1.5 text-foreground/60">
            <Mic className="size-4" />
            {current.singer}
          </span>
        </span>
        <NowPlayingProgress />
        <ChevronRight
          className={cn(
            "size-6 shrink-0 text-foreground/40 transition-colors",
            "group-hover:text-foreground",
          )}
        />
      </button>
    </footer>
  );
};

export default StageNowPlaying;
