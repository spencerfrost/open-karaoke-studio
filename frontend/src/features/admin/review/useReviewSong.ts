import { useSongs } from "@/hooks/api/useSongs";
import type { Song } from "@/types/Song";
import type { SongBasics } from "./SongPanel";

/** The full song once it's loaded, else what the list knows about it. */
export function useReviewSong(basics: SongBasics): Song {
  const { useSong } = useSongs();
  // Ghost records and the like may 404; the basics stand in.
  const { data } = useSong(basics.id, { retry: false });
  return data ?? (basics as Song);
}
