import React, { useEffect, useState } from "react";
import { Play, Pause, Volume2, VolumeX } from "lucide-react";
import { getSongById } from "@/services/songService";
import { Song } from "@/types/Song";
import SyncedLyricsDisplay from "@/components/player/SyncedLyricsDisplay";
import LyricsDisplay from "@/components/player/LyricsDisplay";
import ProgressBar from "@/components/player/ProgressBar";
import { Button } from "@/components/ui/button";
import { useParams } from "react-router-dom";
import { useWebAudioKaraokeStore } from "@/stores/useWebAudioKaraokeStore";
import { usePerformanceControlsStore } from "@/stores/usePerformanceControlsStore";
import WebSocketStatus from "@/components/WebsocketStatus";
import AppLayout from "@/components/layout/AppLayout";

const SongPlayer: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [song, setSong] = useState<Song | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const {
    currentTime,
    duration,
    isReady,
    cleanup,
    seek,
    play,
    pause,
    setSongAndLoad,
  } = useWebAudioKaraokeStore();

  const {
    connect,
    disconnect,
    connected,
    vocalVolume,
    instrumentalVolume,
    lyricsSize,
    isPlaying,
    setVocalVolume,
  } = usePerformanceControlsStore();

  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  useEffect(() => {
    if (!id) {
      setError("No song ID provided.");
      setLoading(false);
      return;
    }
    setLoading(true);
    getSongById(id)
      .then((res) => {
        setSong(res.data);
      })
      .catch(() => setError("Failed to fetch song."))
      .finally(() => setLoading(false));
  }, [id, pause]);

  // Button handlers
  const handlePlayPause = () => {
    if (isPlaying) {
      pause();
    } else {
      play();
    }
  };
  const handleMute = () => {
    setVocalVolume(vocalVolume === 0 ? 1 : 0);
  };

  useEffect(() => {
    if (song) {
      setSongAndLoad(song.id);
    }
    return () => cleanup();
  }, [song, setSongAndLoad, cleanup]);

  useEffect(() => {
    return () => {
      useWebAudioKaraokeStore.getState().cleanup();
    };
  }, []);

  useEffect(() => {
    const controlsStore = usePerformanceControlsStore.getState();

    const handleRemotePlay = () => play();
    const handleRemotePause = () => pause();

    controlsStore.onPlay(handleRemotePlay);
    controlsStore.onPause(handleRemotePause);
  }, [play, pause]);

  // Only render player if song is loaded
  const playerState = useWebAudioKaraokeStore();
  const performanceControlsState = {
    vocalVolume,
    instrumentalVolume,
    lyricsSize,
    isPlaying: isPlaying,
    currentTime,
    duration,
  };

  // eslint-disable-next-line
  const debugPanel = false ? (
    <div className="fixed bottom-16 left-0 w-full text-xs p-2 z-50 border-t border-russet bg-black/80 text-background">
      <div className="flex">
        <div className="flex-1">
          <strong>Player State Debug:</strong>
          <pre className="overflow-x-auto whitespace-pre-wrap">
            {JSON.stringify(playerState, null, 2)}
          </pre>
        </div>
        <div className="flex-1">
          <strong>Performance Controls State Debug:</strong>
          <pre className="overflow-x-auto whitespace-pre-wrap">
            {JSON.stringify(performanceControlsState, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  ) : null;

  if (loading) {
    return (
      <>
        <div className="flex flex-col items-center justify-center h-full">
          <div className="text-lg text-orange-peel animate-pulse">
            Loading song...
          </div>
        </div>
        {/* Debug panel for player state */}
        {debugPanel}
      </>
    );
  }
  if (error || !song) {
    return (
      <>
        <div className="flex flex-col items-center justify-center h-full">
          <div className="text-lg text-destructive">
            {error ?? "Song not found."}
          </div>
        </div>
        {/* Debug panel for player state */}
        {debugPanel}
      </>
    );
  }

  let lyricsContent;
  if (song.syncedLyrics) {
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
    <AppLayout>
      <WebSocketStatus
        connected={connected}
        className="absolute top-4 right-8 z-10"
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
              {isPlaying ? <Pause size={32} /> : <Play size={32} />}
            </Button>
          </div>
        </div>
      </div>

      {/* Debug panel for player state */}
      {debugPanel}
    </AppLayout>
  );
};

export default SongPlayer;
