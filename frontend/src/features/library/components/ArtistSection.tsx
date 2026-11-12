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
  const artistSongs = useInfiniteArtistSongs(
    artist.isShow ? null : artist.id,
    200,
  );
  const showSongs = useInfiniteShowSongs(artist.name, 200, {
    enabled: !!artist.isShow,
  });
  const { songs, hasNextPage, isFetchingNextPage, fetchNextPage } =
    artist.isShow ? showSongs : artistSongs;

  // The API sends their own songs first, so each group keeps its order.
  const ownSongs = songs.filter((song) => song.role !== "featured");
  const appearsOn = songs.filter((song) => song.role === "featured");
  // "Load more" sits under whichever group the next page continues.
  const more = { hasNextPage, isFetchingNextPage, fetchNextPage };
  const ownMore = appearsOn.length === 0 ? more : {};

  return (
    <div className="mb-8 px-4 mt-4 space-y-6">
      {viewMode === "grid" ? (
        <ArtistSongGrid
          songs={ownSongs}
          {...ownMore}
          artistName={artist.name}
          youtubeMusicArtistId={artist.youtubeMusicArtistId}
          showArtist={false}
        />
      ) : (
        ownSongs.length > 0 && <ArtistSongTable songs={ownSongs} {...ownMore} />
      )}

      {appearsOn.length > 0 && (
        <section className="space-y-3">
          <h4 className="text-sm font-semibold uppercase tracking-wide text-foreground-dim">
            Appears on
          </h4>
          {viewMode === "grid" ? (
            <ArtistSongGrid songs={appearsOn} {...more} showArtist />
          ) : (
            <ArtistSongTable songs={appearsOn} {...more} />
          )}
        </section>
      )}
    </div>
  );
};

/** "12 songs · appears on 3", or "Appears on 2 songs" for a guest. */
function describeCounts(artist: Artist): string {
  const songs = (n: number) => `${n} ${n === 1 ? "song" : "songs"}`;
  if (artist.ownCount === 0) return `Appears on ${songs(artist.featuredCount)}`;
  if (artist.featuredCount === 0) return songs(artist.ownCount);
  return `${songs(artist.ownCount)} · appears on ${artist.featuredCount}`;
}

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
  const imageUrl = `/api/artists/${artist.id}/image`;

  return (
    <div
      className="border border-border rounded-lg overflow-hidden"
      id={`artist-${artist.name}`}
    >
      {/* Artist Header */}
      <div className="flex items-center bg-surface-raised text-foreground">
        <button
          onClick={() => onToggle(artist.name)}
          className="flex-1 px-4 py-3 flex items-center text-left hover:bg-surface-hover transition-colors"
        >
          <div className="flex items-center gap-3">
            {isExpanded ? (
              <ChevronDown size={20} className="text-primary" />
            ) : (
              <ChevronRight size={20} className="text-primary" />
            )}
            <div className="w-14 h-14 rounded-md overflow-hidden flex-shrink-0 bg-primary/20 flex items-center justify-center">
              {artist.isShow ? (
                <Theater size={18} className="text-primary" />
              ) : imageError ? (
                <Users size={18} className="text-primary" />
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
              <p className="text-sm opacity-75">{describeCounts(artist)}</p>
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
              className={`p-1.5 rounded transition-colors ${viewMode === "grid" ? "text-primary" : "text-foreground-faint hover:text-foreground-dim"}`}
              aria-label="Grid view"
            >
              <LayoutGrid size={16} />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setViewMode("table");
              }}
              className={`p-1.5 rounded transition-colors ${viewMode === "table" ? "text-primary" : "text-foreground-faint hover:text-foreground-dim"}`}
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
              className="px-3 py-3 hover:bg-surface-hover transition-colors text-primary/60 hover:text-primary"
              aria-label={`Actions for ${artist.name}`}
            >
              <MoreHorizontal size={18} />
            </DropdownMenuTrigger>
            <DropdownMenuContent
              align="end"
              className="bg-overlay/95 border-primary/20"
            >
              <DropdownMenuItem
                onClick={() => setEditOpen(true)}
                className="text-foreground hover:bg-glass/10 cursor-pointer"
              >
                Edit Artist
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => setCollabsOpen(true)}
                className="text-foreground hover:bg-glass/10 cursor-pointer"
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
