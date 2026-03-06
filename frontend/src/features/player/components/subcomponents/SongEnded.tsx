/**
 * SongEnded - Content displayed when a song finishes playing and queue has more songs
 *
 * Shows the next song with a prominent play button, countdown timer for auto-advance,
 * and the completed song info. Replaces the lyrics display when the song ends.
 */

import React, { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Music, Library, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useSongs } from "@/hooks/api/useSongs";
import type { Song } from "@/types/Song";
import type { KaraokeQueueItemWithSong } from "@/types/KaraokeQueue";

const COUNTDOWN_SECONDS = 30;

interface SongEndedProps {
  /** The song that just finished */
  currentSong: Song;
  /** The next song in the queue */
  nextQueueItem?: KaraokeQueueItemWithSong;
  /** Callback to play the next song */
  onPlayNext?: () => void;
  /** Optional class name */
  className?: string;
}

export const SongEnded: React.FC<SongEndedProps> = ({
  currentSong,
  nextQueueItem,
  onPlayNext,
  className = "",
}) => {
  const navigate = useNavigate();
  const { getArtworkUrl } = useSongs();
  const [countdown, setCountdown] = useState(COUNTDOWN_SECONDS);
  const hasTriggeredRef = useRef(false);

  const nextSong = nextQueueItem?.song;
  const nextArtworkUrl = nextSong ? getArtworkUrl(nextSong, "large") : null;

  const handlePlayNext = useCallback(() => {
    if (onPlayNext && !hasTriggeredRef.current) {
      hasTriggeredRef.current = true;
      onPlayNext();
    }
  }, [onPlayNext]);

  // Countdown timer for auto-advance
  useEffect(() => {
    if (!onPlayNext || !nextSong) return;
    hasTriggeredRef.current = false;

    const interval = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          handlePlayNext();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [onPlayNext, nextSong, handlePlayNext]);

  // SVG circular progress for countdown
  const radius = 58;
  const circumference = 2 * Math.PI * radius;
  const progress = countdown / COUNTDOWN_SECONDS;
  const strokeDashoffset = circumference * (1 - progress);

  return (
    <div
      className={`flex items-center justify-center w-full h-full ${className}`}
    >
      <div className="flex flex-col items-center gap-6 p-6 max-w-lg w-full">
        {/* Header */}
        <div className="text-center">
          <h2 className="text-2xl font-bold text-white/80">Song Complete!</h2>
        </div>

        {/* Next song section */}
        {nextSong && (
          <div className="flex flex-col items-center gap-4">
            <p className="text-sm text-white/50 uppercase tracking-wider">
              Up next
            </p>

            {/* Thumbnail with play overlay */}
            <button
              onClick={handlePlayNext}
              className="relative group cursor-pointer w-48 h-48 rounded-xl overflow-hidden bg-black/60 flex items-center justify-center shadow-2xl"
              aria-label={`Play ${nextSong.title}`}
            >
              {nextArtworkUrl ? (
                <img
                  src={nextArtworkUrl}
                  alt={nextSong.title}
                  className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                />
              ) : (
                <Music size={64} className="text-white/20" />
              )}

              {/* Play button overlay with countdown ring */}
              <div className="absolute inset-0 flex items-center justify-center bg-black/40 group-hover:bg-black/50 transition-colors">
                <div className="relative flex items-center justify-center">
                  {/* Countdown ring */}
                  {onPlayNext && (
                    <svg
                      className="absolute w-32 h-32 -rotate-90"
                      viewBox="0 0 128 128"
                    >
                      <circle
                        cx="64"
                        cy="64"
                        r={radius}
                        fill="none"
                        stroke="rgba(255,255,255,0.15)"
                        strokeWidth="4"
                      />
                      <circle
                        cx="64"
                        cy="64"
                        r={radius}
                        fill="none"
                        stroke="rgb(249, 115, 22)"
                        strokeWidth="4"
                        strokeDasharray={circumference}
                        strokeDashoffset={strokeDashoffset}
                        strokeLinecap="round"
                        className="transition-all duration-1000 ease-linear"
                      />
                    </svg>
                  )}
                  <Play
                    size={48}
                    className="text-white drop-shadow-lg group-hover:scale-110 transition-transform"
                    fill="currentColor"
                    strokeWidth={0}
                  />
                </div>
              </div>
            </button>

            {/* Song info */}
            <div className="text-center">
              <h3 className="text-xl font-semibold text-white truncate max-w-xs">
                {nextSong.title}
              </h3>
              <p className="text-white/60 text-sm truncate max-w-xs">
                {nextSong.artist}
              </p>
              {nextQueueItem?.singer && (
                <p className="text-orange-400 text-sm mt-1">
                  {nextQueueItem.singer}
                </p>
              )}
            </div>

            {/* Countdown text */}
            {onPlayNext && countdown > 0 && (
              <p className="text-white/40 text-sm">
                Playing in {countdown}s...
              </p>
            )}
          </div>
        )}

        {/* Previous song (minimal) */}
        <div className="text-center text-white/30 text-xs mt-2">
          Just played: {currentSong.title} — {currentSong.artist}
        </div>

        {/* Browse Library Button */}
        <Button
          variant="outline"
          size="sm"
          onClick={() => navigate("/library")}
          className="bg-black/50 hover:bg-black/70 border-white/20 hover:border-white/40 text-white/70 gap-2"
        >
          <Library className="w-4 h-4" />
          Browse Library
        </Button>
      </div>
    </div>
  );
};

export default SongEnded;
