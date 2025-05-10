import React, { useEffect, useState } from "react";
import { Play, Pause } from "lucide-react";
import { getSongById } from "@/services/songService";
import { Song } from "@/types/Song";
import SyncedLyricsDisplay from "@/components/player/SyncedLyricsDisplay";
import LyricsDisplay from "@/components/player/LyricsDisplay";
import ProgressBar from "@/components/player/ProgressBar";
import { Button } from "@/components/ui/button";

import AppLayout from "@/components/layout/AppLayout";
import WebSocketStatus from "@/components/WebsocketStatus";
import { useParams } from "react-router-dom";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";

const SongPlayer: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [song, setSong] = useState<Song | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const {
    connect,
    disconnect,
    connected,
    currentTime,
    duration,
    isReady,
    isPlaying,
    lyricsOffset,
    cleanup,
    seek,
    play,
    pause,
    setSongAndLoad,
  } = useKaraokePlayerStore();

  useEffect(() => {
    connect();
    return () => {
      cleanup();
      disconnect();
    };
  }, [connect, disconnect, cleanup]);

  useEffect(() => {
    if (!id) return;

    setLoading(true);
    getSongById(id)
      .then((res) => {
        setSong(res.data);
      })
      .catch(() => setError("Failed to fetch song."))
      .finally(() => setLoading(false));
  }, [id, pause]);

  useEffect(() => {
    if (song) {
      setSongAndLoad(song.id);
    }
    return () => cleanup();
  }, [song, setSongAndLoad, cleanup]);

  const playerState = {
    isPlaying,
    currentTime,
    lyricsOffset,
    duration,
    isReady,
    connected,
  };

  // eslint-disable-next-line
  const debugPanel = true ? (
    <div className="fixed bottom-16 left-0 w-full text-xs p-2 z-50 border-t border-russet bg-black/80 text-background">
      <div className="flex">
        <div className="flex-1">
          <strong>Player State Debug:</strong>
          <pre className="overflow-x-auto whitespace-pre-wrap">
            {JSON.stringify(playerState, null, 2)}
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
              className="p-4 rounded-full bg-orange-peel text-russet"
              onClick={isPlaying ? pause : play}
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
