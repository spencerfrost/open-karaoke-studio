import React from "react";
import { Song } from "@/types/Song";
import SongCard from "@/components/songs/SongCard";

interface SongResultsGridProps {
  songs: Song[];
  onSongSelect: (song: Song) => void;
  onAddToQueue: (song: Song) => void;
}

const SongResultsGrid: React.FC<SongResultsGridProps> = ({
  songs,
  onSongSelect,
  onAddToQueue,
}) => {
  if (songs.length === 0) {
    return null;
  }

  return (
    <div className="space-y-4">
      {/* Song Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6 gap-4">
        {songs.filter(Boolean).map((song) => (
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

export default SongResultsGrid;
