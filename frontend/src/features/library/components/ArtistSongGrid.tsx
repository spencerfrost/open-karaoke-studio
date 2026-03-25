import React from "react";
import { Song } from "@/types/Song";
import SongResultsGrid from "./SongResultsGrid";

interface ArtistSongGridProps {
  songs: Song[];
  hasNextPage?: boolean;
  isFetchingNextPage?: boolean;
  fetchNextPage?: () => void;
  artistName?: string;
  showArtist?: boolean;
}

const ArtistSongGrid: React.FC<ArtistSongGridProps> = React.memo((props) => {
  return <SongResultsGrid {...props} />;
});

ArtistSongGrid.displayName = "ArtistSongGrid";

export default ArtistSongGrid;
