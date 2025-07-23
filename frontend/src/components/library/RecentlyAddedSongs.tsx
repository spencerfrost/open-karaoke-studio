import React from "react";
import SongCard from "@/components/songs/SongCard";
import { useSongs as useSongsHook } from "@/hooks/api/useSongs";
import { Song } from "@/types/Song";

interface RecentlyAddedSongsProps {
  onSongSelect: (song: Song) => void;
  onAddToQueue: (song: Song) => void;
  limit?: number;
}

const RecentlyAddedSongs: React.FC<RecentlyAddedSongsProps> = ({
  onSongSelect,
  onAddToQueue,
  limit = 6,
}) => {
  const { useSongs } = useSongsHook();
  const { data: recentSongs, isLoading } = useSongs({
    limit,
    sort_by: "date_added",
    direction: "desc",
  });

  const sortedSongs = recentSongs || [];

  // TODO: Improve empty and loading states
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
            onAddToQueue={onAddToQueue}
          />
        ))}
      </div>
    </div>
  );
};

export default RecentlyAddedSongs;
