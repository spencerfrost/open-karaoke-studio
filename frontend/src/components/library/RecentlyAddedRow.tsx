import React from "react";
import SongCard from "@/components/songs/SongCard";
import { useSongs as useSongsHook } from "@/hooks/useSongs";
import { Song } from "@/types/Song";

interface RecentlyAddedRowProps {
  onSongSelect: (song: Song) => void;
  onToggleFavorite: (song: Song) => void;
  onAddToQueue: (song: Song) => void;
  limit?: number;
}

const RecentlyAddedRow: React.FC<RecentlyAddedRowProps> = ({
  onSongSelect,
  onToggleFavorite,
  onAddToQueue,
  limit = 6,
}) => {
  const { useSongs } = useSongsHook();
  const { data: recentSongs, isLoading } = useSongs({
    limit,
    sort_by: "date_added",
    direction: "desc",
  });

  // Log dateAdded values for debugging
  React.useEffect(() => {
    if (recentSongs) {
      console.log(
        "RecentlyAddedRow dateAdded values:",
        recentSongs.map((s) => s.dateAdded)
      );
    }
  }, [recentSongs]);

  const sortedSongs = recentSongs || [];

  if (isLoading || !recentSongs || recentSongs.length === 0) return null;

  return (
    <div className="mb-8 w-full">
      <div className="flex items-center gap-3 mb-4">
        <span className="text-xl font-semibold text-orange-peel">
          Recently Added
        </span>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4 overflow-hidden">
        {sortedSongs.map((song: Song) => (
          <SongCard
            key={song.id}
            song={song}
            onSelect={onSongSelect}
            onToggleFavorite={onToggleFavorite}
            onAddToQueue={onAddToQueue}
          />
        ))}
      </div>
    </div>
  );
};

export default RecentlyAddedRow;
