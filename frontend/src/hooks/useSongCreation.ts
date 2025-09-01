import { useState } from "react";
import { toast } from "sonner";
import { useSongs } from "@/hooks/api/useSongs";
import { useLyricsSearch } from "@/hooks/api/useLyrics";
import { useYoutubeDownloadMutation } from "@/hooks/api/useYoutube";
import { YouTubeMusicSong } from "@/types/YouTubeMusic";
import { Song } from "@/types/Song";
import type { LyricsOption } from "@/hooks/api/useLyrics";

export const useSongCreation = () => {
  const [isAdding, setIsAdding] = useState(false);
  const [currentSong, setCurrentSong] = useState<YouTubeMusicSong | null>(null);
  const [createdSong, setCreatedSong] = useState<Song | null>(null);

  const { useCreateSong, useUpdateSong } = useSongs();
  const createSongMutation = useCreateSong();
  const updateSongMutation = useUpdateSong();
  
  const {
    data: lyricsOptions,
    loading: isLoadingLyrics,
    search: fetchLyrics,
  } = useLyricsSearch();

  const youtubeDownloadMutation = useYoutubeDownloadMutation({
    onSuccess: () => {
      toast.success("YouTube download started in background");
    },
    onError: (error) => {
      toast.error(`Failed to start download: ${error.message}`);
    },
  });

  const downloadFromYouTube = (songId: string, song: YouTubeMusicSong) => {
    youtubeDownloadMutation.mutate({
      video_id: song.videoId,
      title: song.title,
      artist: song.artist,
      album: song.album,
      song_id: songId,
    });
  };

  const getMetadata = (songId: string, song: YouTubeMusicSong) => {
    // TODO: Extract this to a proper service/hook
    fetch("/api/songs/metadata/auto", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        artist: song.artist,
        title: song.title,
        album: song.album,
        song_id: songId,
      }),
    }).catch(() => {});
  };

  const createSong = (song: YouTubeMusicSong) => {
    setIsAdding(true);
    setCurrentSong(song);

    return createSongMutation.mutateAsync({
      title: song.title,
      artist: song.artist,
      album: song.album || "",
      source: "youtube_music",
      videoId: song.videoId,
    })
    .then((createdSong) => {
      setCreatedSong(createdSong);
      setIsAdding(false);
      
      // Start parallel processes
      fetchLyrics({
        artist: song.artist,
        title: song.title,
        album: song.album,
      });
      downloadFromYouTube(createdSong.id, song);
      getMetadata(createdSong.id, song);
      
      return createdSong;
    })
    .catch((error) => {
      setIsAdding(false);
      toast.error("Failed to create song: " + (error?.message || error));
      throw error;
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

  const resetState = () => {
    setCurrentSong(null);
    setCreatedSong(null);
    setIsAdding(false);
  };

  return {
    // State
    isAdding,
    currentSong,
    createdSong,
    lyricsOptions,
    isLoadingLyrics,
    
    // Actions
    createSong,
    saveLyrics,
    resetState,
    
    // Mutations
    createSongMutation,
    updateSongMutation,
  };
};