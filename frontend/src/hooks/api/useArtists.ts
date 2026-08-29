import { useQuery } from "@tanstack/react-query";

export interface Artist {
  id: number;
  name: string;
  songCount: number;
  firstLetter: string;
  /** True for a musical/soundtrack show folded into the artist browse list, not a real artist row. */
  isShow?: boolean;
}

interface Show {
  name: string;
  songCount: number;
  firstLetter: string;
}

interface UseArtistsParams {
  search?: string;
}

interface UseArtistsResult {
  artists: Artist[];
  isLoading: boolean;
  error: unknown;
}

export function useArtists({
  search = "",
}: UseArtistsParams = {}): UseArtistsResult {
  const queryKey = ["artists", { search }];
  const queryFn = async () => {
    const params = new URLSearchParams();
    if (search.trim()) params.set("search", search);

    const [artistsRes, showsRes] = await Promise.all([
      fetch(`/api/songs/artists?${params.toString()}`),
      fetch(`/api/songs/shows?${params.toString()}`),
    ]);
    if (!artistsRes.ok) throw new Error("Failed to fetch artists");
    if (!showsRes.ok) throw new Error("Failed to fetch shows");

    const artistsData = await artistsRes.json();
    const showsData = await showsRes.json();

    const artists: Artist[] = Array.isArray(artistsData.artists)
      ? artistsData.artists
      : [];
    const shows: Show[] = Array.isArray(showsData.shows) ? showsData.shows : [];

    // Shows aren't real artist rows, so they get a synthetic id — negative,
    // never collides with a real (positive, serial) artist id.
    const showsAsArtists: Artist[] = shows.map((show, i) => ({
      id: -(i + 1),
      name: show.name,
      songCount: show.songCount,
      firstLetter: show.firstLetter,
      isShow: true,
    }));

    return [...artists, ...showsAsArtists].sort((a, b) =>
      a.name.localeCompare(b.name),
    );
  };

  const { data, isLoading, error } = useQuery({
    queryKey,
    queryFn,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  return {
    artists: data ?? [],
    isLoading,
    error,
  };
}
