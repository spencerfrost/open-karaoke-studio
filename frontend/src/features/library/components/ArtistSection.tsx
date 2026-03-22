import React, { useState } from "react";
import { ChevronDown, ChevronRight, Users } from "lucide-react";
import { useInfiniteArtistSongs } from "@/hooks/api/useInfiniteLibraryBrowsing";
import SongResultsGrid from "@/features/library/components/SongResultsGrid";

interface ArtistSectionProps {
  artistName: string;
  songCount: number;
  isExpanded: boolean;
  onToggle: () => void;
}

const ArtistSection: React.FC<ArtistSectionProps> = ({
  artistName,
  songCount,
  isExpanded,
  onToggle,
}) => {
  const [imageError, setImageError] = useState(false);
  const imageUrl = `/api/artists/image?name=${encodeURIComponent(artistName)}`;

  const { songs, hasNextPage, isFetchingNextPage, fetchNextPage } =
    useInfiniteArtistSongs(artistName, 200, {
      enabled: isExpanded,
    });

  return (
    <div
      className="border border-orange-peel rounded-lg overflow-hidden"
      id={`artist-${artistName}`}
    >
      {/* Artist Header */}
      <button
        onClick={onToggle}
        className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-lemon-chiffon/5 transition-colors bg-lemon-chiffon/10 text-lemon-chiffon"
      >
        <div className="flex items-center gap-3">
          {isExpanded ? (
            <ChevronDown size={20} className="text-orange-peel" />
          ) : (
            <ChevronRight size={20} className="text-orange-peel" />
          )}
          <div className="w-14 h-14 rounded-md overflow-hidden flex-shrink-0 bg-orange-peel/20 flex items-center justify-center">
            {imageError ? (
              <Users size={18} className="text-orange-peel" />
            ) : (
              <img
                src={imageUrl}
                alt={artistName}
                className="w-full h-full object-cover"
                loading="lazy"
                onError={() => setImageError(true)}
              />
            )}
          </div>
          <div>
            <h3 className="font-semibold text-lg">{artistName}</h3>
            <p className="text-sm opacity-75">
              {songCount} {songCount === 1 ? "song" : "songs"}
            </p>
          </div>
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
            artistName={artistName}
          />
        </div>
      )}
    </div>
  );
};

export default ArtistSection;
