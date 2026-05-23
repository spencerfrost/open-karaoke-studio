import { useRef, useState } from "react";
import { toast } from "sonner";
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
  duration?: string;
  thumbnail: string;
  startTime?: number;
  endTime?: number;
  lyrics?: string;
}

export type SongSubmissionStatus = "idle" | "pending" | "queued";

export const useSongCreation = () => {
  const [submissionStates, setSubmissionStates] = useState<
    Record<string, "pending" | "queued">
  >({});
  const inFlightVideoIdRef = useRef<string | null>(null);

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

  const createSong = (song: SongInput) => {
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

    if (inFlightVideoIdRef.current === song.videoId || existingState === "pending") {
      logger.debug("Ignoring duplicate song submission while request is in flight", {
        videoId: song.videoId,
      });
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

    // Convert duration to seconds if it's provided
    let duration: number | undefined;
    if (song.duration) {
      const durationValue =
        typeof song.duration === "string"
          ? parseFloat(song.duration)
          : song.duration;
      // Assume duration is already in seconds (no conversion needed)
      duration = durationValue;
    }

    const songData = {
      title: song.title,
      artist: song.artist,
      album: song.album || "",
      duration,
      source: song.source,
      video_id: song.videoId,
    };

    return createSongMutation
      .mutateAsync(songData)
      .then(async (createdSong) => {
        logger.debug("Song created successfully:", createdSong);

        await downloadFromYouTube(createdSong.id, song);
        setSubmissionStates((current) => ({
          ...current,
          [song.videoId]: "queued",
        }));
        logger.debug("Marked song as queued in local submission state", {
          videoId: song.videoId,
          songId: createdSong.id,
        });
        toast.success("Added to library and queued for processing");

        return createdSong;
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
