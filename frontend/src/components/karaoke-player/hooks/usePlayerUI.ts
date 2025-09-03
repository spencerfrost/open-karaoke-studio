/**
 * Custom hook for karaoke player UI state management
 * Handles fullscreen, volume slider visibility, keyboard shortcuts, etc.
 */

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import type { PlayerUIHook } from '../KaraokePlayer.types';

export const usePlayerUI = (): PlayerUIHook => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showVolumeSlider, setShowVolumeSlider] = useState(false);
  const [isControlsVisible, setIsControlsVisible] = useState(true);
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

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange);

    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
      document.removeEventListener('webkitfullscreenchange', handleFullscreenChange);
    };
  }, []);

  // Fullscreen functions
  const enterFullscreen = useCallback(async () => {
    setFsError(null);
    try {
      if (containerRef.current) {
        if (containerRef.current.requestFullscreen) {
          await containerRef.current.requestFullscreen();
        } else if ('webkitRequestFullscreen' in containerRef.current!) {
          (
            containerRef.current! as HTMLElement & {
              webkitRequestFullscreen?: () => void;
            }
          ).webkitRequestFullscreen?.();
        } else {
          setFsError('Fullscreen not supported in this browser.');
        }
      }
    } catch {
      setFsError('Failed to enter fullscreen.');
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
      setFsError('Failed to exit fullscreen.');
    }
  }, []);

  const toggleFullscreen = useCallback(() => {
    if (isFullscreen) {
      exitFullscreen();
    } else {
      enterFullscreen();
    }
  }, [isFullscreen, enterFullscreen, exitFullscreen]);

  // Keyboard shortcuts
  const keyboardShortcuts = useMemo(() => ({
    'Escape': () => {
      if (isFullscreen) {
        exitFullscreen();
      }
    },
    ' ': () => {
      // Space bar for play/pause - will be handled by parent component
      // This is just the mapping, actual implementation in parent
    },
    'f': () => {
      toggleFullscreen();
    },
    'F': () => {
      toggleFullscreen();
    },
  }), [isFullscreen, exitFullscreen, toggleFullscreen]);

  // Keyboard event handler
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const handler = keyboardShortcuts[e.key as keyof typeof keyboardShortcuts];
      if (handler) {
        e.preventDefault();
        handler();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [keyboardShortcuts]);

  // Auto-hide controls in fullscreen (optional enhancement)
  useEffect(() => {
    if (!isFullscreen) {
      setIsControlsVisible(true);
      return;
    }

    let hideTimer: NodeJS.Timeout;
    
    const showControls = () => {
      setIsControlsVisible(true);
      clearTimeout(hideTimer);
      hideTimer = setTimeout(() => {
        setIsControlsVisible(false);
      }, 3000); // Hide after 3 seconds of inactivity
    };

    const handleMouseMove = () => showControls();
    const handleKeyDown = () => showControls();

    // Show controls initially
    showControls();

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      clearTimeout(hideTimer);
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isFullscreen]);

  // Focus management
  const focusPlayer = useCallback(() => {
    if (containerRef.current) {
      containerRef.current.focus();
    }
  }, []);

  // Volume slider management
  const handleSetShowVolumeSlider = useCallback((show: boolean) => {
    setShowVolumeSlider(show);
  }, []);

  return {
    // UI state
    isFullscreen,
    showVolumeSlider,
    isControlsVisible,
    
    // UI actions
    toggleFullscreen,
    setShowVolumeSlider: handleSetShowVolumeSlider,
    
    // Keyboard shortcuts
    keyboardShortcuts,
    
    // Focus management
    focusPlayer,
    
    // Internal refs and error state
    containerRef,
    fsError,
  };
};