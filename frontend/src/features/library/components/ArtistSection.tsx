import React, { useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  LayoutGrid,
  List,
  MoreHorizontal,
  Theater,
  Users,
} from "lucide-react";
import {
  useInfiniteArtistSongs,
  useInfiniteShowSongs,
} from "@/hooks/api/useArtistSongs";
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
  /** Takes the artist name so the parent can pass one stable callback for every
      row - a per-row closure would defeat the memo below. */
  onToggle: (artistName: string) => void;
  isAdmin?: boolean;
}

type ViewMode = "grid" | "table";

/**
 * Holds the two useInfiniteQuery hooks and only mounts once a row is
 * expanded, so collapsed rows carry no React Query observer at all.
 */
const ArtistSectionBody: React.FC<{ artist: Artist; viewMode: ViewMode }> = ({
  artist,
  viewMode,
}) => {
  // A show isn't a real artist row, so it has no artist image and no admin
  // edit/collab actions — but it reuses this same accordion row and the same
  // infinite-songs shape, just sourced from a different endpoint.
  const artistSongs = useInfiniteArtistSongs(artist.name, 200, {
    enabled: !artist.isShow,
  });
  const showSongs = useInfiniteShowSongs(artist.name, 200, {
    enabled: !!artist.isShow,
  });
  const { songs, hasNextPage, isFetchingNextPage, fetchNextPage } =
    artist.isShow ? showSongs : artistSongs;

  return (
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
  );
};

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

  return (
    <div
      className="border border-orange-peel rounded-lg overflow-hidden"
      id={`artist-${artist.name}`}
    >
      {/* Artist Header */}
      <div className="flex items-center bg-lemon-chiffon/10 text-lemon-chiffon">
        <button
          onClick={() => onToggle(artist.name)}
          className="flex-1 px-4 py-3 flex items-center text-left hover:bg-lemon-chiffon/5 transition-colors"
        >
          <div className="flex items-center gap-3">
            {isExpanded ? (
              <ChevronDown size={20} className="text-orange-peel" />
            ) : (
              <ChevronRight size={20} className="text-orange-peel" />
            )}
            <div className="w-14 h-14 rounded-md overflow-hidden flex-shrink-0 bg-orange-peel/20 flex items-center justify-center">
              {artist.isShow ? (
                <Theater size={18} className="text-orange-peel" />
              ) : imageError ? (
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

        {isAdmin && !artist.isShow && (
          <DropdownMenu>
            <DropdownMenuTrigger
              onClick={(e) => e.stopPropagation()}
              className="px-3 py-3 hover:bg-lemon-chiffon/5 transition-colors text-orange-peel/60 hover:text-orange-peel"
              aria-label={`Actions for ${artist.name}`}
            >
              <MoreHorizontal size={18} />
            </DropdownMenuTrigger>
            <DropdownMenuContent
              align="end"
              className="bg-overlay/95 border-orange-peel/20"
            >
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
      {isExpanded && <ArtistSectionBody artist={artist} viewMode={viewMode} />}

      {isAdmin && !artist.isShow && (
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

/**
 * Memoized because the library renders ~600 of these at once, and each one
 * holds two React Query observers plus (for admins) a Radix dropdown. Without
 * this, expanding a single row re-rendered every other row in the list, which
 * is what made the accordion feel like it was thinking about it.
 */
export default React.memo(ArtistSection);
