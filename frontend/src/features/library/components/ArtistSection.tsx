import React, { useState } from "react";
import { ChevronDown, ChevronRight, LayoutGrid, List, MoreHorizontal, Users } from "lucide-react";
import { useInfiniteArtistSongs } from "@/hooks/api/useArtistSongs";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import ArtistSongGrid from "./ArtistSongGrid";
import ArtistSongTable from "./ArtistSongTable";
import EditArtistDialog from "./EditArtistDialog";
import ManageCollabsDialog from "./ManageCollabsDialog";
import { Artist } from "@/hooks/api/useArtists";

interface ArtistSectionProps {
  artist: Artist;
  isExpanded: boolean;
  onToggle: () => void;
  isAdmin?: boolean;
}

type ViewMode = "grid" | "table";

const ArtistSection: React.FC<ArtistSectionProps> = ({
  artist,
  isExpanded,
  onToggle,
  isAdmin = false,
}) => {
  const [imageError, setImageError] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [collabsOpen, setCollabsOpen] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
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

        {isExpanded && (
          <div className="flex items-center px-2">
            <button
              onClick={(e) => {
                e.stopPropagation();
                setViewMode("grid");
              }}
              className={`p-1.5 rounded transition-colors ${viewMode === "grid" ? "text-orange-peel" : "text-lemon-chiffon/30 hover:text-lemon-chiffon/60"}`}
              aria-label="Grid view"
            >
              <LayoutGrid size={16} />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setViewMode("table");
              }}
              className={`p-1.5 rounded transition-colors ${viewMode === "table" ? "text-orange-peel" : "text-lemon-chiffon/30 hover:text-lemon-chiffon/60"}`}
              aria-label="List view"
            >
              <List size={16} />
            </button>
          </div>
        )}

        {isAdmin && (
          <DropdownMenu>
            <DropdownMenuTrigger
              onClick={(e) => e.stopPropagation()}
              className="px-3 py-3 hover:bg-lemon-chiffon/5 transition-colors text-orange-peel/60 hover:text-orange-peel"
              aria-label={`Actions for ${artist.name}`}
            >
              <MoreHorizontal size={18} />
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="bg-zinc-900 border-orange-peel/20">
              <DropdownMenuItem
                onClick={() => setEditOpen(true)}
                className="text-lemon-chiffon hover:bg-lemon-chiffon/10 cursor-pointer"
              >
                Edit Artist
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => setCollabsOpen(true)}
                className="text-lemon-chiffon hover:bg-lemon-chiffon/10 cursor-pointer"
              >
                Manage Collabs
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>

      {/* Expanded Songs */}
      {isExpanded && (
        <div className="mb-8 px-4 mt-4">
          {viewMode === "grid" ? (
            <ArtistSongGrid
              songs={songs}
              hasNextPage={hasNextPage}
              isFetchingNextPage={isFetchingNextPage}
              fetchNextPage={fetchNextPage}
              artistName={artist.name}
              showArtist={false}
            />
          ) : (
            <ArtistSongTable
              songs={songs}
              hasNextPage={hasNextPage}
              isFetchingNextPage={isFetchingNextPage}
              fetchNextPage={fetchNextPage}
            />
          )}
        </div>
      )}

      {isAdmin && (
        <>
          <EditArtistDialog
            artist={artist}
            open={editOpen}
            onOpenChange={setEditOpen}
          />
          <ManageCollabsDialog
            artist={artist}
            open={collabsOpen}
            onOpenChange={setCollabsOpen}
          />
        </>
      )}
    </div>
  );
};

export default ArtistSection;
