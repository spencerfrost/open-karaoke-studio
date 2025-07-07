import React from "react";
import { Music2 } from "lucide-react";
import { Song } from "@/types/Song";
import SongResultsGrid from "./SongResultsGrid";

interface SongResultsSectionProps {
  songs: Song[];
  hasNextPage: boolean;
  isFetchingNextPage: boolean;
  fetchNextPage: () => void;
  onSongSelect: (song: Song) => void;
  onAddToQueue: (song: Song) => void;
  searchTerm: string;
}

const SongResultsSection: React.FC<SongResultsSectionProps> = ({
  songs,
  hasNextPage,
  isFetchingNextPage,
  fetchNextPage,
  onSongSelect,
  onAddToQueue,
  searchTerm,
}) => {
  // Don't show section if no search term or no songs
  if (!searchTerm.trim() || songs.length === 0) {
    return null;
  }

  return (
    <div className="mb-8">
      {/* Section Header */}
      <div className="flex items-center gap-3 mb-6">
        <Music2 size={24} className="text-orange-peel" />
        <h2 className="text-xl font-semibold text-orange-peel">Songs</h2>
        <span className="text-lemon-chiffon/60 text-sm">
          {songs.length} result{songs.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Song Grid */}
      <SongResultsGrid
        songs={songs}
        hasNextPage={hasNextPage}
        isFetchingNextPage={isFetchingNextPage}
        fetchNextPage={fetchNextPage}
        onSongSelect={onSongSelect}
        onAddToQueue={onAddToQueue}
      />
    </div>
  );
};

export default SongResultsSection;
