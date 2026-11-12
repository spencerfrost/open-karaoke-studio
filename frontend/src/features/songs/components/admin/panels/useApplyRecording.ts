import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiSend, useApiMutation } from "@/hooks/api/useApi";

/** A MusicBrainz recording picked for the song, from AcoustID or a search. */
export interface PickedRecording {
  recordingId: string;
  title: string;
  artist: string;
  score: number;
}

/** Set the song's title, artist and MusicBrainz recording from a match. */
export function useApplyRecording(songId: string, onDone: () => void) {
  const queryClient = useQueryClient();
  return useApiMutation<unknown, PickedRecording>(
    `songs/${songId}/fingerprint/apply`,
    "post",
    {
      mutationFn: (recording) =>
        apiSend(`songs/${songId}/fingerprint/apply`, "post", {
          recording_id: recording.recordingId,
          title: recording.title,
          artist: recording.artist,
          score: recording.score,
        }),
      onSuccess: (_data, recording) => {
        toast.success(`Applied: "${recording.title}" by ${recording.artist}`);
        // Prefix match: the library lists and this song's own record.
        queryClient.invalidateQueries({ queryKey: ["songs"] });
        onDone();
      },
      onError: (error) => toast.error(error.message),
    },
  );
}
