/**
 * LyricsDisplayWithCountIn - Wrapper component for LyricsDisplay with count-in support
 * Now simplified - count-in is integrated into the KaraokeLyricsRenderer
 */

import React from "react";
import LyricsDisplay from "./LyricsDisplay";

interface LyricsDisplayProps {
  lyrics: string;
  isSync: boolean;
  currentTime: number; // in seconds
  lyricsSize: "small" | "medium" | "large";
  lyricsOffset: number; // in milliseconds
  className?: string;
  "aria-label"?: string;
  // Optional song data for lyrics search
  songId?: string;
  songTitle?: string;
  songArtist?: string;
  songAlbum?: string;
  songDuration?: number; // in seconds
  // Optional seek callback for clicking on lyrics
  onSeek?: (timeSeconds: number) => void;
}

interface LyricsDisplayWithCountInProps extends LyricsDisplayProps {
  bpm?: number;
  showProgressBar?: boolean;
  showLeadInHighlight?: boolean;
}

const LyricsDisplayWithCountInComponent: React.FC<
  LyricsDisplayWithCountInProps
> = ({
  bpm,
  showProgressBar = false,
  showLeadInHighlight = false,
  ...lyricsDisplayProps
}) => {
  return (
    <LyricsDisplay
      {...lyricsDisplayProps}
      bpm={bpm}
      countInStyle={{
        showProgressBar,
        showLeadInHighlight,
      }}
    />
  );
};

// Memoize component with custom comparison to prevent unnecessary re-renders
// Only re-render when currentTime crosses a 100ms boundary (10Hz)
// This balances smooth animations with reduced React overhead
const LyricsDisplayWithCountIn = React.memo(
  LyricsDisplayWithCountInComponent,
  (prevProps, nextProps) => {
    // Always re-render if non-time props changed
    // NOTE: onSeek is intentionally excluded - function reference changes don't affect rendering
    if (
      prevProps.lyrics !== nextProps.lyrics ||
      prevProps.isSync !== nextProps.isSync ||
      prevProps.lyricsSize !== nextProps.lyricsSize ||
      prevProps.lyricsOffset !== nextProps.lyricsOffset ||
      prevProps.bpm !== nextProps.bpm ||
      prevProps.showProgressBar !== nextProps.showProgressBar ||
      prevProps.showLeadInHighlight !== nextProps.showLeadInHighlight ||
      prevProps.songId !== nextProps.songId
    ) {
      return false; // Props changed, re-render
    }

    // For currentTime, only re-render if it crosses a 100ms boundary
    // This reduces updates from 60Hz to 10Hz while keeping animations acceptably smooth
    const prevTimeBucket = Math.floor((prevProps.currentTime * 1000) / 100);
    const nextTimeBucket = Math.floor((nextProps.currentTime * 1000) / 100);

    return prevTimeBucket === nextTimeBucket; // Same bucket = skip render
  },
);

LyricsDisplayWithCountIn.displayName = "LyricsDisplayWithCountIn";

export default LyricsDisplayWithCountIn;
