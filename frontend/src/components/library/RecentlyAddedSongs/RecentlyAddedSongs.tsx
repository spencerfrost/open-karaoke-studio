import React from "react";
import { RecentlyAddedSongsProps } from "./RecentlyAddedSongs.types";
import { useRecentlyAddedSongs } from "./useRecentlyAddedSongs";
import { usePagination } from "./usePagination";
import { LoadingState } from "./LoadingState";
import { EmptyState } from "./EmptyState";
import { SectionHeader } from "./SectionHeader";
import { AnimatedSongGrid } from "./AnimatedSongGrid";

const RecentlyAddedSongs: React.FC<RecentlyAddedSongsProps> = ({
  limit: songsPerPage = 6,
}) => {
  const { songs, isLoading, totalSongs } = useRecentlyAddedSongs({
    songsPerPage,
  });

  const pagination = usePagination({
    itemsPerPage: songsPerPage,
    totalItems: totalSongs,
  });

  // Early returns for loading and empty states
  if (isLoading) {
    return <LoadingState songsPerPage={songsPerPage} />;
  }

  if (!songs || songs.length === 0) {
    return <EmptyState />;
  }

  // Get current and next page songs
  const currentPageSongs = pagination.currentPageItems(songs);
  const nextPageSongs = pagination.nextPageItems(songs);

  return (
    <div className="mb-8 w-full">
      <SectionHeader
        hasNextPage={pagination.hasNextPage}
        isAnimating={pagination.state.isAnimating}
        onNext={pagination.actions.nextPage}
        songsPerPage={songsPerPage}
      />
      <AnimatedSongGrid
        currentPageSongs={currentPageSongs}
        nextPageSongs={nextPageSongs}
        isAnimating={pagination.state.isAnimating}
        displayPage={pagination.state.displayPage}
      />
    </div>
  );
};

export default RecentlyAddedSongs;