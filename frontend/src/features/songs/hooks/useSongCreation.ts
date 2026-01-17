import { useState } from "react";
import { toast } from "sonner";
import { useSongs } from "@/hooks/api/useSongs";
import { useLyricsSearch } from "@/hooks/api/useLyrics";
import { useYoutubeDownloadMutation } from "@/hooks/api/useYoutube";
import { Song } from "@/types/Song";
import type { LyricsOption } from "@/hooks/api/useLyrics";

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
  const [createdSong, setCreatedSong] = useState<Song | null>(null);

  const { useCreateSong, useUpdateSong } = useSongs();
  const createSongMutation = useCreateSong();
  const updateSongMutation = useUpdateSong();

  const lyricsSearch = useLyricsSearch();

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
      engine_type: "hybrid",
    });
  };

  const getMetadata = (songId: string, song: SongInput) => {
    const metadataPromise = Promise.all([
      downloadFromYouTube(songId, song),
      lyricsSearch.search({ title: song.title, artist: song.artist, album: song.album })
    ]);

    metadataPromise.then(() => {
      console.log("All download and lyrics search operations started");
    });
  };

  const createSong = (song: SongInput) => {
    setIsAdding(true);
    setCurrentSong(song);

    // Convert duration to seconds if it's provided
    let duration: number | undefined;
    if (song.duration) {
      const durationValue = typeof song.duration === 'string' ? parseFloat(song.duration) : song.duration;
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
        setCreatedSong(createdSong);
        console.log("Song created successfully:", createdSong);
        
        // Start parallel processes for lyrics and download
        getMetadata(createdSong.id, song);
        
        return createdSong;
      })
      .catch((error) => {
        console.error("Error creating song:", error);
        throw error;
      })
      .finally(() => {
        setIsAdding(false);
      });
  };

  const saveLyrics = (lyrics: LyricsOption) => {
    if (!createdSong) return Promise.reject("No created song");

    return updateSongMutation.mutateAsync({
      id: createdSong.id,
      plainLyrics: lyrics.plainLyrics,
      syncedLyrics: lyrics.syncedLyrics,
    });
  };

  const searchLyrics = (
    customTitle?: string,
    customArtist?: string,
    customAlbum?: string,
  ) => {
    if (!currentSong) return Promise.reject("No current song");

    return lyricsSearch.search({
      title: customTitle || currentSong.title,
      artist: customArtist || currentSong.artist,
      album: customAlbum || currentSong.album || "",
    });
  };

  const resetState = () => {
    setCurrentSong(null);
    setCreatedSong(null);
    setIsAdding(false);
  };

  const setCurrentSongState = (song: SongInput | null) => {
    setCurrentSong(song);
  };

  const setCreatedSongState = (song: Song | null) => {
    setCreatedSong(song);
  };

  return {
    // State
    isAdding,
    currentSong,
    createdSong,
    lyricsOptions: lyricsSearch.data || [],
    isLoadingLyrics: lyricsSearch.loading,

    // Actions
    createSong,
    saveLyrics,
    searchLyrics,
    resetState,
    setCurrentSong: setCurrentSongState,
    setCreatedSong: setCreatedSongState,

    // Mutations
    createSongMutation,
    updateSongMutation,
  };
};
