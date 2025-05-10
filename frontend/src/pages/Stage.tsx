import React, { useEffect } from "react";
import { Play, Pause, Volume2, VolumeX } from "lucide-react";
import AppLayout from "../components/layout/AppLayout";
import LyricsDisplay from "../components/player/LyricsDisplay";
import ProgressBar from "../components/player/ProgressBar";
import SyncedLyricsDisplay from "@/components/player/SyncedLyricsDisplay";
import { Button } from "@/components/ui/button";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import KaraokeQueueList from "../components/queue/KaraokeQueueList";
import { useKaraokeQueueStore } from "@/stores/useKaraokeQueueStore";
import WebSocketStatus from "@/components/WebsocketStatus";

const Stage: React.FC = () => {
  const {
    currentTime,
    duration,
    seek,
    isReady,
    isPlaying,
    play,
    pause,
    vocalVolume,
    setVocalVolume,
    connect,
    disconnect,
    connected,
  } = useKaraokePlayerStore();

  const { currentSong, items } = useKaraokeQueueStore();

  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

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

  let lyricsContent;
  if (currentSong?.song.syncedLyrics) {
    lyricsContent = (
      <SyncedLyricsDisplay
        syncedLyrics={currentSong?.song.syncedLyrics}
        currentTime={currentTime * 1000}
        className="h-full"
      />
    );
  } else {
    lyricsContent = (
      <LyricsDisplay
        lyrics={currentSong?.song.lyrics ?? ""}
        progress={duration ? currentTime / duration : 0}
        currentTime={currentTime * 1000}
      />
    );
  }

  return (
    <AppLayout>
      <div className="flex flex-col gap-4 h-full p-6 relative z-20">
        <WebSocketStatus
          connected={connected}
          className="absolute top-4 right-8 z-10"
        />
        <h1 className="text-3xl font-bold text-center mb-2 text-orange-peel">
          {currentSong?.song.title}
        </h1>
        <h2 className="text-xl text-center mb-4 text-background/80">
          {currentSong?.song.artist}
        </h2>
        <div className="aspect-video w-full bg-black/80 rounded-xl overflow-hidden flex items-center justify-center relative">
          {lyricsContent}
        </div>
        {/* Bottom controls */}
        <div className="p-4 pt-0 " style={{ zIndex: 30 }}>
          <ProgressBar
            currentTime={currentTime}
            duration={duration}
            onSeek={(val) => seek(val)}
            className="mb-4"
          />

          <div className="flex justify-center items-center gap-4">
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

        <h2 className="text-2xl font-semibold text-center mb-4 text-orange-peel">
          Up Next
        </h2>

        <div className="max-w-2xl mx-auto w-full rounded-xl overflow-hidden text-background border border-orange-peel">
          <KaraokeQueueList
            items={items}
            emptyMessage="No songs in the queue"
          />
        </div>
      </div>
    </AppLayout>
  );
};

export default Stage;
