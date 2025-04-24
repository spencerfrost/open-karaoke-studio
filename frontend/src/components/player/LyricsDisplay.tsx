import React, { useEffect, useState, useRef } from "react";
import { getSongLyrics } from "../../services/songService";

interface LyricsDisplayProps {
  className?: string;
  songId: string;
}

const LyricsDisplay: React.FC<LyricsDisplayProps> = ({
  className = "",
  songId,
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
      } catch (err) {
        setError("Failed to fetch lyrics.");
      }
    };

    fetchLyrics();
  }, [songId]);

  useEffect(() => {
    if (lyrics && lyricsRef.current) {
      const totalHeight = lyricsRef.current.scrollHeight;
      const containerHeight = lyricsRef.current.clientHeight;
      lyricsRef.current.style.transition = `transform ${lyrics.duration}s linear`;
      lyricsRef.current.style.transform = `translateY(-${totalHeight-containerHeight}px)`;
    }
  }, [lyrics]);

  return (
    <div
      className={`flex flex-col items-center justify-center text-center p-4 overflow-hidden ${className}`}
      ref={containerRef}
    >
      {error ? (
        <div className="text-red-500">{error}</div>
      ) : lyrics ? (
        <div
          ref={lyricsRef}
          className="text-2xl font-semibold mb-4 text-background whitespace-pre-line"
        >
          {lyrics.plainLyrics || "No lyrics available"}
        </div>
      ) : (
        <div className="text-gray-500">Loading lyrics...</div>
      )}
    </div>
  );
};

export default LyricsDisplay;
