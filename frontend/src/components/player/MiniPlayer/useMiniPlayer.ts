/**
 * useMiniPlayer - Logic hook for mini-player behavior
 */

import { useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import { useIsPlayerPage } from "@/hooks/useIsPlayerPage";

export function useMiniPlayer() {
  const navigate = useNavigate();
  const isPlayerPage = useIsPlayerPage();

  const {
    songId,
    songTitle,
    songArtist,
    isPlaying,
    isReady,
    songEnded,
    currentTime,
    duration,
    miniPlayerEnabled,
    miniPlayerPosition,
    miniPlayerDismissed,
    userPlay,
    userPause,
    setMiniPlayerPosition,
    dismissMiniPlayer,
  } = useKaraokePlayerStore();

  // Determine if mini-player should be visible
  // Only show when song is actively playing, not when ended
  const shouldShow = Boolean(
    songId && // Has a song loaded
      isReady && // Song is ready to play
      isPlaying && // Song is currently playing
      !songEnded && // Song hasn't finished
      miniPlayerEnabled && // User has mini-player enabled
      !miniPlayerDismissed && // User hasn't dismissed it for this song
      !isPlayerPage, // Not on a player-related page
  );

  // Toggle play/pause
  const handlePlayPause = useCallback(() => {
    if (isPlaying) {
      userPause();
    } else {
      userPlay();
    }
  }, [isPlaying, userPlay, userPause]);

  // Expand to full player (navigate to stage)
  const handleExpand = useCallback(() => {
    navigate(`/stage`);
  }, [navigate]);

  // Close/dismiss mini-player
  const handleClose = useCallback(() => {
    dismissMiniPlayer();
  }, [dismissMiniPlayer]);

  // Update position (for draggable feature)
  const handleDrag = useCallback(
    (x: number, y: number) => {
      setMiniPlayerPosition({ x, y });
    },
    [setMiniPlayerPosition],
  );

  return {
    // State
    shouldShow,
    songId,
    songTitle,
    songArtist,
    isPlaying,
    currentTime,
    duration,
    position: miniPlayerPosition,

    // Actions
    handlePlayPause,
    handleExpand,
    handleClose,
    handleDrag,
  };
}

export default useMiniPlayer;
