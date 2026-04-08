import { useState } from "react";
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

export const useSongCreation = () => {
  const [isAdding, setIsAdding] = useState(false);
  const [currentSong, setCurrentSong] = useState<SongInput | null>(null);

  const { useCreateSong } = useSongs();
  const createSongMutation = useCreateSong();

  const youtubeDownloadMutation = useYoutubeDownloadMutation({
    onSuccess: () => {
      // Download started successfully
    },
    onError: (error) => {
      toast.error(`Failed to start download: ${error.message}`);
    },
  });

  const downloadFromYouTube = (songId: string, song: SongInput) => {
    youtubeDownloadMutation.mutate({
      song_id: songId,
      video_id: song.videoId,
      title: song.title,
      artist: song.artist,
      album: song.album,
      engine_type: "three_track",
    });
  };

  const createSong = (song: SongInput) => {
    setIsAdding(true);
    setCurrentSong(song);

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
      .then((createdSong) => {
        logger.debug("Song created successfully:", createdSong);

        downloadFromYouTube(createdSong.id, song);

        return createdSong;
      })
      .catch((error) => {
        logger.error("Error creating song:", error);
        throw error;
      })
      .finally(() => {
        setIsAdding(false);
      });
  };

  return {
    // State
    isAdding,
    currentSong,

    // Actions
    createSong,

    // Mutations
    createSongMutation,
  };
};
