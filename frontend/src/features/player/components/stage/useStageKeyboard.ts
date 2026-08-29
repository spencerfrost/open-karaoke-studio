/**
 * useStageKeyboard - the one place stage keys are bound.
 *
 * The keyboard is already in the room, so it gets the two fixes that matter
 * mid-song: seek, and nudging the lyrics offset when they drift.
 *
 *   Space        play / pause
 *   Left/Right   seek -/+ 5s
 *   Up/Down      lyrics offset +/- 100ms
 */

import { useEffect } from "react";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";

const SEEK_STEP_SECONDS = 5;
const OFFSET_STEP_MS = 100;

export const useStageKeyboard = () => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLElement) {
        if (["INPUT", "TEXTAREA", "SELECT"].includes(e.target.tagName)) return;
        if (e.target.isContentEditable) return;
      }

      const {
        isReady,
        isPlaying,
        currentTime,
        duration,
        lyricsOffset,
        userPlay,
        userPause,
        seek,
        setLyricsOffset,
      } = useKaraokePlayerStore.getState();

      switch (e.code) {
        case "Space":
          if (!isReady) return;
          e.preventDefault(); // prevent page scroll
          if (isPlaying) userPause();
          else userPlay();
          return;
        case "ArrowLeft":
          if (!isReady) return;
          e.preventDefault();
          seek(Math.max(0, currentTime - SEEK_STEP_SECONDS));
          return;
        case "ArrowRight":
          if (!isReady) return;
          e.preventDefault();
          {
            const next = currentTime + SEEK_STEP_SECONDS;
            seek(duration > 0 ? Math.min(duration, next) : next);
          }
          return;
        case "ArrowUp":
          e.preventDefault();
          setLyricsOffset(lyricsOffset + OFFSET_STEP_MS);
          return;
        case "ArrowDown":
          e.preventDefault();
          setLyricsOffset(lyricsOffset - OFFSET_STEP_MS);
          return;
        default:
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);
};
