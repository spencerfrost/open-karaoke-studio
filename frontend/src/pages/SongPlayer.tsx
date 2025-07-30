import React, { useEffect } from "react";
import { useParams } from "react-router-dom";

import AppLayout from "@/components/layout/AppLayout";
import UnifiedLyricsDisplay from "@/components/player/UnifiedLyricsDisplay";
import WebSocketStatus from "@/components/WebsocketStatus";

import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import { useSongs } from "@/hooks/api/useSongs";

const SongPlayer: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  // Use the song query hook
  const { useSong } = useSongs();

  const {
    data: song,
    isLoading: songLoading,
    error: songError,
  } = useSong(id ?? "");

  const {
    connect,
    disconnect,
    connected,
    currentTime,
    durationMs,
    isReady,
    isPlaying,
    lyricsOffset,
    cleanup,
    seek,
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
    if (song) {
      setSongAndLoad(song.id, song.durationMs);
    }
    return () => cleanup();
  }, [song, setSongAndLoad, cleanup]);

  // Combine lyrics data if we fetched it separately
  const lyrics = song?.plainLyrics || "";
  const syncedLyrics = song?.syncedLyrics || "";

  const playerState = {
    isPlaying,
    currentTime,
    lyricsOffset,
    durationMs,
    isReady,
    connected,
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
      </div>
    </div>
  ) : null;

  if (songLoading) {
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
  if (songError || !song) {
    return (
      <>
        <div className="flex flex-col items-center justify-center h-full">
          <div className="text-lg text-destructive">
            {songError instanceof Error ? songError.message : "Song not found."}
          </div>
        </div>
        {/* Debug panel for player state */}
        {debugPanel}
      </>
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
          <UnifiedLyricsDisplay
            lyrics={syncedLyrics || lyrics || ""}
            isSynced={!!syncedLyrics}
            currentTime={currentTime * 1000}
            title={song.title}
            artist={song.artist}
            durationMs={durationMs || 0}
            onSeek={seek}
          />
        </div>
      </div>

      {/* Debug panel for player state */}
      {debugPanel}
    </AppLayout>
  );
};

export default SongPlayer;
