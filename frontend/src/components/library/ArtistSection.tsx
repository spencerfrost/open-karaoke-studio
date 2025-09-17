import React from "react";
import { ChevronDown, ChevronRight, Users } from "lucide-react";
import { Song } from "@/types/Song";
import { useInfiniteArtistSongs } from "@/hooks/api/useInfiniteLibraryBrowsing";
import SongResultsGrid from "@/components/library/SongResultsGrid";

interface ArtistSectionProps {
  artistName: string;
  songCount: number;
  isExpanded: boolean;
  onToggle: () => void;
  onSongSelect: (song: Song) => void;
  sessionId?: string;
}

const ArtistSection: React.FC<ArtistSectionProps> = ({
  artistName,
  songCount,
  isExpanded,
  onToggle,
  onSongSelect,
  sessionId,
}) => {
  const { songs, hasNextPage, isFetchingNextPage, fetchNextPage } =
    useInfiniteArtistSongs(artistName, 200, {
      enabled: isExpanded,
    });

  return (
    <div className="border border-orange-peel rounded-lg overflow-hidden">
      {/* Artist Header */}
      <button
        onClick={onToggle}
        className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-opacity-50 transition-colors bg-lemon-chiffon/10 text-lemon-chiffon"
      >
        <div className="flex items-center gap-3">
          {isExpanded ? (
            <ChevronDown size={20} className="text-orange-peel" />
          ) : (
            <ChevronRight size={20} className="text-orange-peel" />
          )}
          <Users size={18} className="text-orange-peel" />
          <div>
            <h3 className="font-semibold text-lg">{artistName}</h3>
            <p className="text-sm opacity-75">
              {songCount} {songCount === 1 ? "song" : "songs"}
            </p>
          </div>
        </div>
        <div className="px-3 py-1 rounded-full text-sm font-medium bg-orange-peel text-dark-cyan">
          {songCount}
        </div>
      </button>

      {/* Expanded Songs List */}
      {isExpanded && (
        <div className="mb-8 px-4 mt-4">
          <SongResultsGrid
            songs={songs}
            hasNextPage={hasNextPage}
            isFetchingNextPage={isFetchingNextPage}
            fetchNextPage={fetchNextPage}
            onSongSelect={onSongSelect}
            sessionId={sessionId}
          />
        </div>
      )}
    </div>
  );
};

export default ArtistSection;
