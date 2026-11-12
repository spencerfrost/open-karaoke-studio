import React from "react";
import { Music2 } from "lucide-react";
import { Song } from "@/types/Song";
import SongResultsGrid from "./SongResultsGrid";

interface SongResultsSectionProps {
  songs: Song[];
  hasNextPage: boolean;
  isFetchingNextPage: boolean;
  fetchNextPage: () => void;
  searchTerm: string;
}

const SongResultsSection: React.FC<SongResultsSectionProps> = ({
  songs,
  hasNextPage,
  isFetchingNextPage,
  fetchNextPage,
  searchTerm,
}) => {
  return (
    <div className="mb-8">
      {/* Section Header */}
      <div className="flex items-center gap-3 mb-6">
        <Music2 size={24} className="text-primary" />
        <h2 className="text-xl font-semibold text-primary">Songs</h2>
        <span className="text-foreground-dim text-sm">
          {songs.length} result{songs.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Song Grid */}
      <SongResultsGrid
        songs={songs}
        hasNextPage={hasNextPage}
        isFetchingNextPage={isFetchingNextPage}
        fetchNextPage={fetchNextPage}
        searchTerm={searchTerm}
      />
    </div>
  );
};

export default SongResultsSection;
