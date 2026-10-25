import { useCallback, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiSend } from "@/hooks/api/useApi";
import { createLogger } from "@/lib/logger";

const logger = createLogger("hook:song-creation");

/** A YouTube or YouTube Music song to add, as POST /songs/from-youtube takes it. */
export interface SongInput {
  videoId: string;
  title: string;
  /** Every credited artist, primary first. */
  artists: string[];
  album?: string | null;
  durationSeconds?: number | null;
  source: "youtube" | "youtube_music";
}

interface AddSongResponse {
  songId: string;
  jobId: string;
  /** True when this restarted the song's failed copy instead of adding one. */
  restarted: boolean;
}

/** What this page has done with a song: its request is in flight, or it's added. */
export type SongSubmission =
  | { status: "adding" }
  | { status: "added"; songId: string };

// Surface the backend's message (e.g. demo download limits, "already in the
// songbook") when it's a real user-facing string; fall back for opaque errors.
const addSongErrorMessage = (error: unknown): string => {
  if (
    error instanceof Error &&
    error.message &&
    !error.message.startsWith("HTTP error!")
  ) {
    return error.message;
  }
  return "Couldn't add that song. Try again.";
};

/**
 * Adds songs from YouTube in one request each, and remembers what this page
 * submitted so a row's button reflects it right away.
 *
 * The server restarts a song's failed copy instead of adding a duplicate, so
 * there's nothing to decide here; a second tap while the first is in flight
 * is ignored.
 */
export const useSongCreation = () => {
  const [submissions, setSubmissions] = useState<
    Record<string, SongSubmission>
  >({});
  // Read synchronously, so a double tap can't slip past a pending state update.
  const inFlightRef = useRef(new Set<string>());
  const queryClient = useQueryClient();

  const addSong = useCallback(
    async (song: SongInput): Promise<string | null> => {
      if (inFlightRef.current.has(song.videoId)) return null;
      inFlightRef.current.add(song.videoId);
      setSubmissions((current) => ({
        ...current,
        [song.videoId]: { status: "adding" },
      }));

      try {
        const result = await apiSend<
          AddSongResponse,
          {
            video_id: string;
            title: string;
            artists: string[];
            album: string | null;
            duration: number | null;
            source: SongInput["source"];
          }
        >("songs/from-youtube", "post", {
          video_id: song.videoId,
          title: song.title,
          artists: song.artists,
          album: song.album ?? null,
          duration: song.durationSeconds ?? null,
          source: song.source,
        });
        logger.debug("Song added", { videoId: song.videoId, ...result });

        setSubmissions((current) => ({
          ...current,
          [song.videoId]: { status: "added", songId: result.songId },
        }));
        toast.success(
          result.restarted
            ? "Trying that song again"
            : "Added to the songbook. Getting it ready…",
        );
        queryClient.invalidateQueries({ queryKey: ["songs"] });
        return result.songId;
      } catch (error) {
        logger.error("Error adding song:", error);
        setSubmissions((current) => {
          const next = { ...current };
          delete next[song.videoId];
          return next;
        });
        toast.error(addSongErrorMessage(error));
        return null;
      } finally {
        inFlightRef.current.delete(song.videoId);
      }
    },
    [queryClient],
  );

  const getSubmission = useCallback(
    (videoId: string | null | undefined): SongSubmission | undefined =>
      videoId ? submissions[videoId] : undefined,
    [submissions],
  );

  return { addSong, getSubmission };
};
