import React, { useEffect, useState, useRef } from "react";
import { getSongLyrics } from "../../services/songService";
import SyncedLyricsDisplay from "./SyncedLyricsDisplay";

interface LyricsDisplayProps {
  className?: string;
  songId: string;
  progress: number; // Progress in percentage (0 to 1)
  currentTime?: number; // Current time in milliseconds
}

const LyricsDisplay: React.FC<LyricsDisplayProps> = ({
  className = "",
  songId,
  progress,
  currentTime = 0,
}) => {
  const [lyrics, setLyrics] = useState<{
    plainLyrics: string;
    syncedLyrics: string;
    duration: number;
  } | null>(null);

  const [error, setError] = useState<string | null>(null);
  const lyricsRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchLyrics = async () => {
      try {
        const fetchedLyrics = await getSongLyrics(songId);
        setLyrics(fetchedLyrics.data);
      } catch {
        setError("Failed to fetch lyrics.");
      }
    };

    fetchLyrics();
  }, [songId]);

  useEffect(() => {
    // Only apply scroll effect for plain lyrics
    // Synced lyrics will be handled by the SyncedLyricsDisplay component
    if (lyrics && lyricsRef.current && containerRef.current && !lyrics.syncedLyrics) {
      const updateScrollPosition = () => {
        const lyricsElement = lyricsRef.current;
        if (!lyricsElement) return;

        // Calculate the total scrollable distance (total height minus visible height)
        const totalScrollHeight = lyricsElement.scrollHeight - lyricsElement.clientHeight;
        // Calculate scroll position based on progress percentage
        const scrollPosition = Math.max(0, Math.min(totalScrollHeight, progress * totalScrollHeight));

        lyricsElement.scrollTop = scrollPosition;
      };
      setTimeout(updateScrollPosition, 0);
    }
  }, [progress, lyrics]);

  const renderLyricsContent = () => {
    if (error) {
      return <div className="text-red-500">{error}</div>;
    }
    
    if (lyrics) {
      // If we have synced lyrics, use the SyncedLyricsDisplay component
      if (lyrics.syncedLyrics) {
        return (
          <SyncedLyricsDisplay
            syncedLyrics={lyrics.syncedLyrics}
            currentTime={currentTime}
            className="h-full"
          />
        );
      }
      
      // Fallback to plain lyrics
      return lyrics.plainLyrics ? (
        <div className="text-2xl font-semibold text-background whitespace-pre-line">
          {lyrics.plainLyrics}
        </div>
      ) : (
        <div className="text-gray-400">No lyrics available</div>
      );
    }
    return <div className="text-gray-500">Loading lyrics...</div>;
  };

  return (
    <div
      className={`flex flex-col items-center justify-center text-center p-4 ${className}`}
      ref={containerRef}
      style={{ height: "100%", width: "100%" }}
    >
      <div
        ref={lyricsRef}
        className="w-full h-full overflow-y-auto scrollbar-hide"
        style={{ maxHeight: "100%" }}
      >
        {renderLyricsContent()}
      </div>
    </div>
  );
};

export default LyricsDisplay;
