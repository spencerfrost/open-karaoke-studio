import React, { useEffect } from "react";

import AppLayout from "@/components/layout/AppLayout";
import WebSocketStatus from "@/components/WebsocketStatus";
import KaraokeQueueList from "@/components/queue/KaraokeQueueList";
import UnifiedLyricsDisplay from "@/components/player/UnifiedLyricsDisplay";

import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import { useKaraokeQueueStore } from "@/stores/useKaraokeQueueStore";

const Stage: React.FC = () => {
  const { currentTime, duration, seek, connect, disconnect, connected } =
    useKaraokePlayerStore();

  const { currentQueueItem, items } = useKaraokeQueueStore();
  const currentSong = currentQueueItem?.song;

  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return (
    <AppLayout>
      <div className="flex flex-col gap-4 h-full p-6 relative z-20">
        <WebSocketStatus
          connected={connected}
          className="absolute top-4 right-8 z-10"
        />
        <h1 className="text-3xl font-bold text-center mb-2 text-orange-peel">
          {currentSong?.title}
        </h1>
        <h2 className="text-xl text-center mb-4 text-background/80">
          {currentSong?.artist}
        </h2>
        <div className="aspect-video w-full bg-black/80 rounded-xl overflow-hidden flex items-center justify-center relative">
          <UnifiedLyricsDisplay
            lyrics={currentSong?.syncedLyrics || currentSong?.lyrics || ""}
            isSynced={!!currentSong?.syncedLyrics}
            currentTime={currentTime * 1000}
            title={currentSong?.title || ""}
            artist={currentSong?.artist || ""}
            duration={duration}
            onSeek={seek}
          />
        </div>
        <h2 className="text-2xl font-semibold text-center my-4 text-orange-peel">
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
