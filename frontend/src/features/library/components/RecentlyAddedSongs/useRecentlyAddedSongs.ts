import { useSongs as useSongsHook } from "@/hooks/api/useSongs";

interface UseRecentlyAddedSongsOptions {
  songsPerPage: number;
}

export const useRecentlyAddedSongs = ({
  songsPerPage,
}: UseRecentlyAddedSongsOptions) => {
  // Fetch a larger number of songs to support pagination
  const totalSongsToFetch = Math.max(24, songsPerPage * 4);

  const { useSongs } = useSongsHook();
  const {
    data: allSongs,
    isLoading,
    error,
  } = useSongs({
    limit: totalSongsToFetch,
    sort_by: "date_added",
    direction: "desc",
  });

  const songs = allSongs || [];

  return {
    songs,
    isLoading,
    error,
    totalSongs: songs.length,
  };
};
