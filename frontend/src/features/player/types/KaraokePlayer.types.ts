/**
 * TypeScript interfaces for the unified KaraokePlayer component
 */

import { ReactNode } from "react";
import type { Song } from "@/types/Song";
import type { KaraokeQueueItemWithSong } from "@/types/KaraokeQueue";

// Sidebar display modes
export type SidebarMode = "floating" | "push";

// Player control types
export type PlayerControl = "play" | "volume" | "fullscreen";

// Main component props interface
export interface KaraokePlayerProps {
  // Song to play
  songId: string;

  // Queue data (optional) - used to show queue status when song ends
  queueItems?: KaraokeQueueItemWithSong[];

  // Player configuration
  autoPlay?: boolean;

  // UI options
  controls?: boolean;
  showInfo?: boolean;
  showVisualizer?: boolean;

  // Sidebar options
  sidebarMode?: SidebarMode; // 'floating' = overlay, 'push' = takes space
  showSidebarTrigger?: boolean; // Show the settings button

  // Event callbacks
  onPlay?: () => void;
  onPause?: () => void;
  onEnd?: () => void;
  onTimeUpdate?: (currentTime: number, duration: number) => void; // Both in seconds
  onError?: (error: Error) => void;

  // Styling
  className?: string;
  style?: React.CSSProperties;
  children?: ReactNode;
}

// Player options for useKaraokePlayer hook
export interface PlayerOptions {
  autoPlay?: boolean;
  preload?: boolean;
}

// Error type for player errors
export interface PlayerError {
  code: string;
  message: string;
  details?: unknown;
}

// Return interface for useKaraokePlayer hook
export interface KaraokePlayerHook {
  // State
  song: Song | null;
  isLoading: boolean;
  isReady: boolean;
  isPlaying: boolean;
  songEnded: boolean; // True when song finished naturally (not paused)
  currentTime: number; // In seconds (changed from milliseconds)
  duration: number; // In seconds (changed from milliseconds)
  error: PlayerError | null;
  connectionStatus: "connected" | "disconnected" | "connecting";

  // Playback controls
  play: () => void;
  pause: () => void;
  togglePlay: () => void;
  seek: (timeSeconds: number) => void; // Now accepts seconds instead of milliseconds
  replay: () => void; // Restart playback from the beginning

  // Audio controls
  setVocalVolume: (volume: number) => void;
  setInstrumentalVolume: (volume: number) => void;
  vocalVolume: number;
  instrumentalVolume: number;

  // Lyrics and display
  lyrics: string;
  isLyricsSync: boolean;
  lyricsSize: "small" | "medium" | "large";
  lyricsOffset: number;
  setLyricsSize: (size: "small" | "medium" | "large") => void;
  setLyricsOffset: (offset: number) => void;

  // Visualizer
  waveformData: Uint8Array | null;

  // Advanced
  reload: () => Promise<void>;
  preload: (songId: string) => Promise<void>;
}

// Return interface for usePlayerUI hook
export interface PlayerUIHook {
  // UI state
  isFullscreen: boolean;
  showVolumeSlider: boolean;
  isControlsVisible: boolean;

  // UI actions
  toggleFullscreen: () => void;
  setShowVolumeSlider: (show: boolean) => void;

  // Keyboard shortcuts
  keyboardShortcuts: {
    [key: string]: () => void;
  };

  // Focus management
  focusPlayer: () => void;

  // Internal refs and error state (for component usage)
  containerRef: React.RefObject<HTMLDivElement | null>;
  fsError: string | null;
}
