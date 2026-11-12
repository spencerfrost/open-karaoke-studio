import {
  selectCurrentSongId,
  useKaraokePlayerStore,
} from "@/stores/useKaraokePlayerStore";
import { useSongs } from "@/hooks/api/useSongs";

/**
 * Whether the current song has a separate backing-vocal stem. Only
 * three-track songs do. Asks the song, not the audio player: the phone
 * controls the stage without loading any audio.
 */
export const useBackingTrackAvailable = (): boolean => {
  const songId = useKaraokePlayerStore(selectCurrentSongId);
  const { useSong } = useSongs();
  const { data: song } = useSong(songId ?? "");
  return !!song?.backingVocalPath;
};
