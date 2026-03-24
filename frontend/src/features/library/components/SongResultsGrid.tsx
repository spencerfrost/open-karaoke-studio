import React from "react";
import { useNavigate } from "react-router-dom";
import { Song } from "@/types/Song";
import {
  SongCard,
  PerformerSongCard,
} from "@/features/songs/components/song-card";
import { useSessionStore } from "@/stores/sessionStore";
import { Button } from "@/components/ui/button";
import { Loader2, Youtube } from "lucide-react";
import { BrowseArtistCard } from "./BrowseArtistCard";

interface SongResultsGridProps {
  songs: Song[];
  hasNextPage?: boolean;
  isFetchingNextPage?: boolean;
  fetchNextPage?: () => void;
  searchTerm?: string;
  artistName?: string;
  showArtist?: boolean;
}

const SongResultsGrid: React.FC<SongResultsGridProps> = ({
  songs,
  hasNextPage,
  isFetchingNextPage,
  fetchNextPage,
  searchTerm,
  artistName,
  showArtist = true,
}) => {
  const navigate = useNavigate();
  const { isHost } = useSessionStore();
  const CardComponent = isHost ? SongCard : PerformerSongCard;

  if (songs.length === 0 && searchTerm) {
    return (
      <div className="flex flex-col items-center justify-center py-12 px-4">
        <div className="text-center space-y-4 max-w-md">
          <p className="text-lemon-chiffon/60">
            No songs found in your library for "{searchTerm}"
          </p>
          <Button
            onClick={() => navigate(`/add?q=${encodeURIComponent(searchTerm)}`)}
            className="gap-2"
          >
            <Youtube className="h-4 w-4" />
            Search YouTube
          </Button>
        </div>
      </div>
    );
  }

  if (songs.length === 0) {
    return null;
  }

  return (
    <div className="space-y-4">
      {/* Song Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-4">
        {songs.filter(Boolean).map((song) => (
          <CardComponent key={song.id} song={song} showArtist={showArtist} />
        ))}
        {artistName && <BrowseArtistCard artistName={artistName} />}
      </div>

      {/* Load More Button */}
      {hasNextPage && (
        <div className="flex justify-center mt-6">
          <Button
            onClick={fetchNextPage}
            disabled={isFetchingNextPage}
            variant="outline"
            className="px-8"
          >
            {isFetchingNextPage ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Loading...
              </>
            ) : (
              "Load More Songs"
            )}
          </Button>
        </div>
      )}
    </div>
  );
};

export default SongResultsGrid;
