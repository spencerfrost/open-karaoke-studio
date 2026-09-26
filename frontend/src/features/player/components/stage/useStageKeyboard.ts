/**
 * useStageKeyboard - the one place stage keys are bound.
 *
 * The keyboard is already in the room, so it gets the fixes that matter
 * mid-song: the guide vocal, and nudging the lyrics when they drift. Seeking
 * is left to the transport - it is almost never what anyone wants mid-song,
 * and on the arrow keys it was one stray press away.
 *
 *   Space/Enter  play / pause
 *   Up/Down      vocal volume +/- 10%
 *   Left/Right   lyrics offset -/+ 100ms (Left = lyrics earlier)
 *   F            toggle fullscreen
 *
 * Escape is not bound: the Fullscreen API makes the browser exit on Escape and
 * the page cannot prevent it, so a handler here would only shadow it.
 */

import { useEffect, useRef } from "react";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";

const VOCAL_STEP = 0.1;
const OFFSET_STEP_MS = 100;

interface UseStageKeyboardOptions {
  onToggleFullscreen?: () => void;
  /**
   * False while another stage screen covers the player. The guards below stop
   * typed keys reaching the shortcuts, but arrowing around a song grid is not
   * typing — and it should not be seeking the song playing underneath.
   */
  enabled?: boolean;
}

export const useStageKeyboard = ({
  onToggleFullscreen,
  enabled = true,
}: UseStageKeyboardOptions = {}) => {
  // Held in a ref so the listener below keeps its empty deps — toggleFullscreen
  // changes identity every time fullscreen does, and rebinding on that is noise.
  const onToggleFullscreenRef = useRef(onToggleFullscreen);
  onToggleFullscreenRef.current = onToggleFullscreen;

  // Same reason: flipping screens must not tear down and rebind the listener.
  const enabledRef = useRef(enabled);
  enabledRef.current = enabled;

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLElement) {
        if (["INPUT", "TEXTAREA", "SELECT"].includes(e.target.tagName)) return;
        if (e.target.isContentEditable) return;
      }

      // Radix preventDefaults its own arrow handling but never stops
      // propagation, so a focused slider thumb or an open dialog would move
      // AND run the shortcuts below. Bail out for anything that owns its keys.
      const t = e.target instanceof HTMLElement ? e.target : null;
      if (t?.closest("[role='dialog'], [role='slider']")) return;

      // Fullscreen is not a playback control - it stays live on every stage
      // screen, including while someone is browsing the library.
      if (e.code === "KeyF") {
        // No isReady gate — hiding browser chrome is useful with no song
        // loaded, and this runs off a real keypress so it carries the user
        // activation requestFullscreen() demands.
        if (e.ctrlKey || e.metaKey || e.altKey) return;
        e.preventDefault();
        onToggleFullscreenRef.current?.();
        return;
      }

      if (!enabledRef.current) return;

      const {
        isReady,
        isPlaying,
        vocalVolume,
        lyricsOffset,
        userPlay,
        userPause,
        setVocalVolume,
        setLyricsOffset,
      } = useKaraokePlayerStore.getState();

      switch (e.code) {
        case "Space":
        case "Enter":
        case "NumpadEnter":
          // A focused button owns Enter; let it click rather than toggling
          // playback as well.
          if (e.code !== "Space" && t?.closest("button, a, [role='button']")) {
            return;
          }
          if (!isReady) return;
          e.preventDefault(); // prevent page scroll
          // Enter that started the song on the confirm screen, still held,
          // must not auto-repeat into pausing it.
          if (e.repeat) return;
          if (isPlaying) userPause();
          else userPlay();
          return;
        case "ArrowUp":
          e.preventDefault();
          setVocalVolume(Math.min(1, vocalVolume + VOCAL_STEP));
          return;
        case "ArrowDown":
          e.preventDefault();
          setVocalVolume(Math.max(0, vocalVolume - VOCAL_STEP));
          return;
        case "ArrowLeft":
          e.preventDefault();
          setLyricsOffset(lyricsOffset - OFFSET_STEP_MS);
          return;
        case "ArrowRight":
          e.preventDefault();
          setLyricsOffset(lyricsOffset + OFFSET_STEP_MS);
          return;
        default:
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);
};
