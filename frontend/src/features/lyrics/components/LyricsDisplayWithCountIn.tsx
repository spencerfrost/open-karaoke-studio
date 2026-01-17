/**
 * LyricsDisplayWithCountIn - Wrapper component for LyricsDisplay with count-in support
 * Parses LRC content, manages count-in triggers, and overlays CountInDisplay
 */

import React, { useMemo } from "react";
import LyricsDisplay from "./LyricsDisplay";
import CountInDisplay from "./CountInDisplay";
import { parseLrcWithCountIn } from "@/utils/lrcUtils";

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
  showCountdownNumbers?: boolean;
  showCountdownIcons?: boolean;
  showProgressBar?: boolean;
  showLeadInHighlight?: boolean;
}

const LyricsDisplayWithCountIn: React.FC<LyricsDisplayWithCountInProps> = ({
  lyrics,
  bpm,
  showCountdownNumbers = false,
  showCountdownIcons = false,
  showProgressBar = false,
  showLeadInHighlight = false,
  ...lyricsDisplayProps
}) => {
  // Parse LRC with count-in data (memoized)
  const parsedData = useMemo(() => {
    if (!lyrics || !bpm) return null;
    return parseLrcWithCountIn(lyrics, bpm);
  }, [lyrics, bpm]);

  // Find active trigger (memoized)
  const activeTrigger = useMemo(() => {
    if (!parsedData) return null;
    const currentTimeMs = lyricsDisplayProps.currentTime * 1000;
    return parsedData.countInTriggers.find(
      (trigger) => currentTimeMs >= trigger.countInStart && currentTimeMs < trigger.countInEnd
    );
  }, [parsedData, lyricsDisplayProps.currentTime]);

  // Check if any count-in style is enabled
  const hasCountInEnabled =
    showCountdownNumbers || showCountdownIcons || showProgressBar || showLeadInHighlight;

  return (
    <div className="relative w-full h-full">
      {/* Original LyricsDisplay (unchanged) */}
      <LyricsDisplay {...lyricsDisplayProps} lyrics={lyrics} />

      {/* Count-in overlay */}
      {hasCountInEnabled && activeTrigger && bpm && parsedData && (
        <CountInDisplay
          trigger={activeTrigger}
          currentTime={lyricsDisplayProps.currentTime}
          bpm={bpm}
          showCountdownNumbers={showCountdownNumbers}
          showCountdownIcons={showCountdownIcons}
          showProgressBar={showProgressBar}
          showLeadInHighlight={showLeadInHighlight}
          lyricsSize={lyricsDisplayProps.lyricsSize}
          upcomingLineContent={parsedData.lines[activeTrigger.lineIndex]?.content}
        />
      )}
    </div>
  );
};

export default LyricsDisplayWithCountIn;
