/**
 * usePlayerUI - fullscreen for the stage, and nothing else.
 *
 * Now that the page IS the player, fullscreen's only job is hiding browser
 * chrome. Keys are bound in useStageKeyboard (the one place with a guard for
 * inputs and dialogs), so this hook deliberately registers no listeners of its
 * own beyond tracking the browser's own fullscreen state.
 */

import { useState, useEffect, useCallback, useRef } from "react";
import type { PlayerUIHook } from "../types/KaraokePlayer.types";

export const usePlayerUI = (): PlayerUIHook => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [fsError, setFsError] = useState<string | null>(null);

  // Fullscreen event listeners
  useEffect(() => {
    const handleFullscreenChange = () => {
      const fsElement =
        document.fullscreenElement ||
        (document as Document & { webkitFullscreenElement?: Element })
          .webkitFullscreenElement;
      setIsFullscreen(!!fsElement && fsElement === containerRef.current);
    };

    document.addEventListener("fullscreenchange", handleFullscreenChange);
    document.addEventListener("webkitfullscreenchange", handleFullscreenChange);

    return () => {
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
      document.removeEventListener(
        "webkitfullscreenchange",
        handleFullscreenChange,
      );
    };
  }, []);

  // Fullscreen functions
  const enterFullscreen = useCallback(async () => {
    setFsError(null);
    try {
      if (containerRef.current) {
        if (containerRef.current.requestFullscreen) {
          await containerRef.current.requestFullscreen();
        } else if ("webkitRequestFullscreen" in containerRef.current!) {
          (
            containerRef.current! as HTMLElement & {
              webkitRequestFullscreen?: () => void;
            }
          ).webkitRequestFullscreen?.();
        } else {
          setFsError("Fullscreen not supported in this browser.");
        }
      }
    } catch {
      setFsError("Failed to enter fullscreen.");
    }
  }, []);

  const exitFullscreen = useCallback(async () => {
    setFsError(null);
    try {
      if (document.exitFullscreen) {
        await document.exitFullscreen();
      } else if (
        (document as Document & { webkitExitFullscreen?: () => void })
          .webkitExitFullscreen
      ) {
        (
          document as Document & { webkitExitFullscreen?: () => void }
        ).webkitExitFullscreen?.();
      }
    } catch {
      setFsError("Failed to exit fullscreen.");
    }
  }, []);

  const toggleFullscreen = useCallback(() => {
    if (isFullscreen) {
      exitFullscreen();
    } else {
      enterFullscreen();
    }
  }, [isFullscreen, enterFullscreen, exitFullscreen]);

  return {
    isFullscreen,
    toggleFullscreen,
    containerRef,
    fsError,
  };
};
