import React, { useEffect } from "react";

import AppLayout from "@/components/layout/AppLayout";
import WebSocketStatus from "@/components/WebsocketStatus";
import KaraokeQueueList from "@/components/queue/KaraokeQueueList";
import UnifiedLyricsDisplay from "@/components/player/UnifiedLyricsDisplay";

import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import { useKaraokeQueueStore } from "@/stores/useKaraokeQueueStore";
import { useQueue, useRemoveFromKaraokeQueue, usePlayFromKaraokeQueue } from "@/hooks/api/useKaraokeQueue";
import { toast } from "sonner";

const Stage: React.FC = () => {
  const {
    currentTime,
    duration,
    durationMs,
    seek,
    connect,
    disconnect,
    connected,
    setSongAndLoad,
  } = useKaraokePlayerStore();

  const { currentQueueItem, setKaraokeQueue } = useKaraokeQueueStore();
  const currentSong = currentQueueItem?.song;

  // API hooks
  const queueQuery = useQueue();
  const removeFromQueueMutation = useRemoveFromKaraokeQueue();
  const playFromQueueMutation = usePlayFromKaraokeQueue();

  // Update store when API data changes
  useEffect(() => {
    if (queueQuery.data) {
      setKaraokeQueue(queueQuery.data);
    }
  }, [queueQuery.data, setKaraokeQueue]);

  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  const handleRemoveFromQueue = async (id: string) => {
    try {
      await removeFromQueueMutation.mutateAsync(id);
      queueQuery.refetch(); // Refresh queue
      toast.success("Song removed from queue");
    } catch (error) {
      console.error("Failed to remove song from queue:", error);
      toast.error("Failed to remove song from queue");
    }
  };

  const handlePlayFromQueue = async (id: string) => {
    try {
      const songData = await playFromQueueMutation.mutateAsync(id);
      queueQuery.refetch(); // Refresh queue
      
      // Load song into player
      if (songData && songData.id) {
        await setSongAndLoad(songData.id, songData.durationMs);
        toast.success(`Now playing: ${songData.title}`);
      }
    } catch (error) {
      console.error("Failed to play song from queue:", error);
      toast.error("Failed to play song from queue");
    }
  };

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
            lyrics={currentSong?.syncedLyrics || currentSong?.plainLyrics || ""}
            isSynced={!!currentSong?.syncedLyrics}
            currentTime={currentTime * 1000}
            title={currentSong?.title || ""}
            artist={currentSong?.artist || ""}
            durationMs={durationMs !== undefined ? durationMs : duration * 1000}
            onSeek={seek}
          />
        </div>
        <h2 className="text-2xl font-semibold text-center my-4 text-orange-peel">
          Up Next
        </h2>

        <div className="max-w-2xl mx-auto w-full rounded-xl overflow-hidden text-background border border-orange-peel">
          <KaraokeQueueList
            items={queueQuery.data || []}
            emptyMessage="No songs in the queue"
            onRemove={handleRemoveFromQueue}
            onPlay={handlePlayFromQueue}
          />
        </div>
      </div>
    </AppLayout>
  );
};

export default Stage;
