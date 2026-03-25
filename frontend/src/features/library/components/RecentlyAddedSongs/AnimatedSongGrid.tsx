import React from "react";
import {
  SongCard,
  PerformerSongCard,
} from "@/features/songs/components/song-card";
import { useSessionStore } from "@/stores/sessionStore";
import { Song } from "@/types/Song";

interface AnimatedSongGridProps {
  currentPageSongs: Song[];
  nextPageSongs: Song[];
  isAnimating: boolean;
  displayPage: number;
  sessionId?: string;
}

const GRID_CLASSES =
  "grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4 transition-all duration-300 ease-in-out";

export const AnimatedSongGrid: React.FC<AnimatedSongGridProps> = ({
  currentPageSongs,
  nextPageSongs,
  isAnimating,
  displayPage,
  sessionId,
}) => {
  const { isHost } = useSessionStore();
  const CardComponent = isHost ? SongCard : PerformerSongCard;

  return (
    <div className="relative overflow-hidden">
      {/* Current page content - slides out to the left */}
      <div
        className={`${GRID_CLASSES} ${
          isAnimating
            ? "-translate-x-full opacity-0"
            : "translate-x-0 opacity-100"
        }`}
      >
        {currentPageSongs.map((song: Song) => (
          <CardComponent
            key={`${song.id}-${displayPage}`}
            song={song}
            sessionId={sessionId}
          />
        ))}
      </div>

      {/* Next page content - slides in from the right during animation */}
      {isAnimating && nextPageSongs.length > 0 && (
        <div
          className={`absolute top-0 left-0 w-full ${GRID_CLASSES} ${
            isAnimating
              ? "translate-x-0 opacity-100"
              : "translate-x-full opacity-0"
          }`}
        >
          {nextPageSongs.map((song: Song) => (
            <CardComponent
              key={`${song.id}-${displayPage + 1}`}
              song={song}
              sessionId={sessionId}
            />
          ))}
        </div>
      )}
    </div>
  );
};
