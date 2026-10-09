import { useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiSend } from "@/hooks/api/useApi";
import { useSongs } from "@/hooks/api/useSongs";
import { useYoutubeDownloadMutation } from "@/hooks/api/useYoutube";
import { createLogger } from "@/lib/logger";

const logger = createLogger("hook:song-creation");

// Generic song input interface for both YouTube sources
export interface SongInput {
  title: string;
  artist: string;
  album?: string;
  videoId: string;
  source: "youtube" | "youtube_music";
  url: string;
  duration?: number; // seconds
  thumbnail: string;
  startTime?: number;
  endTime?: number;
  lyrics?: string;
  // A failed library copy of this song: adding restarts it instead of
  // creating a duplicate beside it.
  failedSongId?: string | null;
}

export type SongSubmissionStatus = "idle" | "pending" | "queued";

export const useSongCreation = () => {
  const [submissionStates, setSubmissionStates] = useState<
    Record<string, "pending" | "queued">
  >({});
  const inFlightVideoIdRef = useRef<string | null>(null);
  const queryClient = useQueryClient();

  const { useCreateSong } = useSongs();
  const createSongMutation = useCreateSong();

  const youtubeDownloadMutation = useYoutubeDownloadMutation({
    onError: (error) => {
      logger.error("Error queueing song download:", error);
    },
  });

  const downloadFromYouTube = (songId: string, song: SongInput) => {
    logger.debug("Queueing backend processing request", {
      songId,
      videoId: song.videoId,
      title: song.title,
      source: song.source,
    });

    return youtubeDownloadMutation.mutateAsync({
      song_id: songId,
      video_id: song.videoId,
      title: song.title,
      artist: song.artist,
      album: song.album,
      engine_type: "three_track",
    });
  };

  const retryFailedSong = async (songId: string) => {
    logger.debug("Restarting failed song instead of adding a duplicate", {
      songId,
    });
    await apiSend<{ jobId: string }, null>(`songs/${songId}/retry`, "post");
    // It's back in the songbook (as processing) now that it's no longer failed.
    queryClient.invalidateQueries({ queryKey: ["songs"] });
    return songId;
  };

  const addNewSong = async (song: SongInput) => {
    const songData = {
      title: song.title,
      artist: song.artist,
      album: song.album || "",
      duration: song.duration,
      source: song.source,
      video_id: song.videoId,
    };
    const createdSong = await createSongMutation.mutateAsync(songData);
    logger.debug("Song created successfully:", createdSong);
    await downloadFromYouTube(createdSong.id, song);
    return createdSong.id;
  };

  const createSong = (song: SongInput): Promise<string | null> => {
    const existingState = submissionStates[song.videoId];
    logger.debug("createSong invoked", {
      videoId: song.videoId,
      title: song.title,
      source: song.source,
      existingState,
      inFlightVideoId: inFlightVideoIdRef.current,
    });

    if (existingState === "queued") {
      logger.debug("Ignoring duplicate song submission after song was queued", {
        videoId: song.videoId,
      });
      return Promise.resolve(null);
    }

    if (
      inFlightVideoIdRef.current === song.videoId ||
      existingState === "pending"
    ) {
      logger.debug(
        "Ignoring duplicate song submission while request is in flight",
        {
          videoId: song.videoId,
        },
      );
      return Promise.resolve(null);
    }

    inFlightVideoIdRef.current = song.videoId;
    setSubmissionStates((current) => ({
      ...current,
      [song.videoId]: "pending",
    }));
    logger.debug("Marked song as pending in local submission state", {
      videoId: song.videoId,
    });

    const request = song.failedSongId
      ? retryFailedSong(song.failedSongId)
      : addNewSong(song);

    return request
      .then((songId) => {
        setSubmissionStates((current) => ({
          ...current,
          [song.videoId]: "queued",
        }));
        logger.debug("Marked song as queued in local submission state", {
          videoId: song.videoId,
          songId,
        });
        toast.success("Added to the songbook and queued for processing");

        return songId;
      })
      .catch((error) => {
        logger.error("Error creating song:", error);
        setSubmissionStates((current) => {
          const nextState = { ...current };
          delete nextState[song.videoId];
          return nextState;
        });
        logger.debug("Cleared local submission state after failure", {
          videoId: song.videoId,
        });
        throw error;
      })
      .finally(() => {
        inFlightVideoIdRef.current = null;
        logger.debug("Reset transient add-song state", {
          videoId: song.videoId,
        });
      });
  };

  const getSubmissionStatus = (videoId: string): SongSubmissionStatus => {
    const state = submissionStates[videoId];
    if (state === "pending" || state === "queued") {
      return state;
    }
    return "idle";
  };

  return {
    // State
    submissionStates,
    getSubmissionStatus,

    // Actions
    createSong,

    // Mutations
    createSongMutation,
  };
};
