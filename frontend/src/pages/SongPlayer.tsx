import React, { useEffect, useState } from "react";
import { Play, Pause, Volume2, VolumeX } from "lucide-react";
import {
  getSongById,
  updateSongMetadata,
  getAudioUrl,
} from "@/services/songService";
import { fetchLyrics } from "@/services/youtubeService";
import { Song } from "@/types/Song";
import SyncedLyricsDisplay from "@/components/player/SyncedLyricsDisplay";
import LyricsDisplay from "@/components/player/LyricsDisplay";
import ProgressBar from "@/components/player/ProgressBar";
import { Button } from "@/components/ui/button";
import { MetadataDialog } from "@/components/upload/MetadataDialog";
import { parseYouTubeTitle } from "@/utils/formatters";
import { useParams } from "react-router-dom";
import { useWebAudioKaraoke } from "@/hooks/useWebAudioKaraoke";
import PlayerLayout from "@/components/layout/PlayerLayout";

const SongPlayer: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  // Zustand store state/actions
  const [song, setSong] = useState<Song | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lyricsLoading, setLyricsLoading] = useState(false);
  const [isSearchingLyrics, setIsSearchingLyrics] = useState(false);
  const [showMetadataDialog, setShowMetadataDialog] = useState(false);

  // Fetch song on mount
  useEffect(() => {
    if (!id) {
      setError("No song ID provided.");
      setLoading(false);
      return;
    }
    setLoading(true);
    getSongById(id)
      .then((res) => {
        if (res.data) {
          setSong(res.data);
        } else {
          setError("Song not found.");
        }
      })
      .catch(() => setError("Failed to fetch song."))
      .finally(() => setLoading(false));
  }, [id]);

  // Fetch lyrics if missing
  useEffect(() => {
    if (!song || song.lyrics || song.syncedLyrics) return;
    setLyricsLoading(true);
    fetchLyrics(song.title, song.artist, song.album, song.id)
      .then(async (res) => {
        if (res.data && (res.data.lyrics || res.data.syncedLyrics)) {
          const updated = {
            ...song,
            lyrics: res.data.lyrics ?? "",
            syncedLyrics: res.data.syncedLyrics ?? "",
          };
          setSong(updated);
          // Persist lyrics to backend
          await updateSongMetadata(song.id, {
            lyrics: res.data.lyrics ?? "",
            syncedLyrics: res.data.syncedLyrics ?? "",
          });
        }
      })
      .catch(() => {
        /* ignore lyrics fetch errors */
      })
      .finally(() => setLyricsLoading(false));
  }, [song]);

  // Show metadata dialog if lyrics are missing
  useEffect(() => {
    if (
      song &&
      !song.lyrics &&
      !song.syncedLyrics &&
      !loading &&
      !lyricsLoading
    ) {
      setShowMetadataDialog(true);
    }
  }, [song, loading, lyricsLoading]);

  // Handler for metadata dialog submit
  const handleMetadataSubmit = async (metadata: {
    artist: string;
    title: string;
    album?: string;
  }) => {
    if (!song) return;
    setIsSearchingLyrics(true);
    try {
      const res = await fetchLyrics(
        metadata.title,
        metadata.artist,
        metadata.album,
        song.id
      );
      if (res.data && (res.data.lyrics || res.data.syncedLyrics)) {
        const updated = {
          ...song,
          lyrics: res.data.lyrics ?? "",
          syncedLyrics: res.data.syncedLyrics ?? "",
        };
        setSong(updated);
        await updateSongMetadata(song.id, {
          lyrics: res.data.lyrics ?? "",
          syncedLyrics: res.data.syncedLyrics ?? "",
        });
        setShowMetadataDialog(false);
      }
    } catch {
      // Optionally handle error
    } finally {
      setIsSearchingLyrics(false);
    }
  };

  // Button handlers
  const handlePlayPause = () => {
    if (isPlaying) {
      pause();
    } else {
      play();
    }
  };
  const handleMute = () => {
    setVocalVol(vocalVolume === 0 ? 1 : 0);
  };

  // Prepare URLs for the hook, even if song is not loaded yet
  const instrumentalUrl = song ? getAudioUrl(song.id, "instrumental") : "";
  const vocalUrl = song ? getAudioUrl(song.id, "vocals") : "";
  const {
    currentTime,
    duration,
    load,
    cleanup,
    seek,
    isReady,
    isPlaying,
    play,
    pause,
    vocalVolume,
    setVocalVol,
  } = useWebAudioKaraoke({
    instrumentalUrl,
    vocalUrl,
  });

  useEffect(() => {
    if (song) load();
    return () => cleanup();
  }, [song, load, cleanup]);

  // Only render player if song is loaded
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full">
        <div className="text-lg text-orange-peel animate-pulse">
          Loading song...
        </div>
      </div>
    );
  }
  if (error || !song) {
    return (
      <div className="flex flex-col items-center justify-center h-full">
        <div className="text-lg text-destructive">
          {error ?? "Song not found."}
        </div>
      </div>
    );
  }

  let lyricsContent;
  if (lyricsLoading) {
    lyricsContent = (
      <div className="text-orange-peel animate-pulse text-xl">
        Fetching lyrics...
      </div>
    );
  } else if (song.syncedLyrics) {
    lyricsContent = (
      <SyncedLyricsDisplay
        syncedLyrics={song.syncedLyrics}
        currentTime={currentTime * 1000}
        className="h-full"
      />
    );
  } else {
    lyricsContent = (
      <LyricsDisplay
        lyrics={song.lyrics ?? ""}
        progress={duration ? currentTime / duration : 0}
        currentTime={currentTime * 1000}
      />
    );
  }

  return (
    <PlayerLayout>
      <MetadataDialog
        isOpen={showMetadataDialog}
        onClose={() => setShowMetadataDialog(false)}
        onSubmit={handleMetadataSubmit}
        initialMetadata={
          song ? parseYouTubeTitle(song.title) : { title: "", artist: "" }
        }
        videoTitle={song?.title ?? ""}
        isSubmitting={isSearchingLyrics}
      />
      <div className="w-full max-w-3xl mx-auto">
        <h1 className="text-3xl font-bold text-center mb-2 text-orange-peel">
          {song.title}
        </h1>
        <h2 className="text-xl text-center mb-4 text-background/80">
          {song.artist}
        </h2>
        <div className="aspect-video w-full bg-black/80 rounded-xl overflow-hidden mb-4 flex items-center justify-center relative">
          {lyricsContent}
        </div>
        <div className="flex flex-col gap-2 mt-2">
          <ProgressBar
            currentTime={currentTime}
            duration={duration}
            onSeek={(val) => seek(val)}
            className="mb-2"
          />
          <div className="flex justify-center items-center gap-6">
            <Button
              className="p-3 rounded-full bg-accent text-background"
              onClick={handleMute}
              aria-label={vocalVolume === 0 ? "Unmute vocals" : "Mute vocals"}
            >
              {vocalVolume === 0 ? (
                <VolumeX size={24} />
              ) : (
                <Volume2 size={24} />
              )}
            </Button>
            <Button
              className="p-4 rounded-full bg-orange-peel text-russet"
              onClick={handlePlayPause}
              aria-label={isPlaying ? "Pause" : "Play"}
              disabled={!isReady}
            >
              {isPlaying ? (
                <Pause size={32} />
              ) : (
                <Play size={32} style={{ marginLeft: "3px" }} />
              )}
            </Button>
          </div>
        </div>
      </div>
    </PlayerLayout>
  );
};

export default SongPlayer;
