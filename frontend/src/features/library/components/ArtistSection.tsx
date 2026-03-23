import React, { useState } from "react";
import { ChevronDown, ChevronRight, MoreHorizontal, Users } from "lucide-react";
import { useInfiniteArtistSongs } from "@/hooks/api/useArtistSongs";
import SongResultsGrid from "@/features/library/components/SongResultsGrid";
import EditArtistDialog from "./EditArtistDialog";
import { Artist } from "@/hooks/api/useArtists";

interface ArtistSectionProps {
  artist: Artist;
  isExpanded: boolean;
  onToggle: () => void;
  isAdmin?: boolean;
}

const ArtistSection: React.FC<ArtistSectionProps> = ({
  artist,
  isExpanded,
  onToggle,
  isAdmin = false,
}) => {
  const [imageError, setImageError] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const imageUrl = `/api/artists/image?name=${encodeURIComponent(artist.name)}`;

  const { songs, hasNextPage, isFetchingNextPage, fetchNextPage } =
    useInfiniteArtistSongs(artist.name, 200, {
      enabled: isExpanded,
    });

  return (
    <div
      className="border border-orange-peel rounded-lg overflow-hidden"
      id={`artist-${artist.name}`}
    >
      {/* Artist Header */}
      <div className="flex items-center bg-lemon-chiffon/10 text-lemon-chiffon">
        <button
          onClick={onToggle}
          className="flex-1 px-4 py-3 flex items-center text-left hover:bg-lemon-chiffon/5 transition-colors"
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
                  alt={artist.name}
                  className="w-full h-full object-cover"
                  loading="lazy"
                  onError={() => setImageError(true)}
                />
              )}
            </div>
            <div>
              <h3 className="font-semibold text-lg">{artist.name}</h3>
              <p className="text-sm opacity-75">
                {artist.songCount} {artist.songCount === 1 ? "song" : "songs"}
              </p>
            </div>
          </div>
        </button>

        {isAdmin && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              setEditOpen(true);
            }}
            className="px-3 py-3 hover:bg-lemon-chiffon/5 transition-colors text-orange-peel/60 hover:text-orange-peel"
            aria-label={`Edit ${artist.name}`}
          >
            <MoreHorizontal size={18} />
          </button>
        )}
      </div>

      {/* Expanded Songs List */}
      {isExpanded && (
        <div className="mb-8 px-4 mt-4">
          <SongResultsGrid
            songs={songs}
            hasNextPage={hasNextPage}
            isFetchingNextPage={isFetchingNextPage}
            fetchNextPage={fetchNextPage}
            artistName={artist.name}
          />
        </div>
      )}

      {isAdmin && (
        <EditArtistDialog
          artist={artist}
          open={editOpen}
          onOpenChange={setEditOpen}
        />
      )}
    </div>
  );
};

export default ArtistSection;
