import { useQuery } from "@tanstack/react-query";

export interface Artist {
  id: number;
  name: string;
  /**
   * What the name files under: leading article dropped, accents folded,
   * lowercased. Computed server-side so every A–Z list agrees.
   */
  sortName: string;
  songCount: number;
  /** "A"–"Z", or "#" for anything else. */
  firstLetter: string;
  /** True for a musical/soundtrack show folded into the artist browse list, not a real artist row. */
  isShow?: boolean;
}

interface Show {
  name: string;
  sortName: string;
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
      sortName: show.sortName,
      songCount: show.songCount,
      firstLetter: show.firstLetter,
      isShow: true,
    }));

    return [...artists, ...showsAsArtists].sort((a, b) =>
      a.sortName.localeCompare(b.sortName, undefined, { numeric: true }),
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
