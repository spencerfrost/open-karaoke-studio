import React, { useEffect } from "react";

import AppLayout from "@/components/layout/AppLayout";
import KaraokeQueueList from "@/components/queue/KaraokeQueueList";
import UnifiedLyricsDisplay from "@/components/player/UnifiedLyricsDisplay";
import WebSocketStatus from "@/components/WebsocketStatus";

import { useSongs } from "@/hooks/api/useSongs";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import {
  useQueue,
  useRemoveFromKaraokeQueue,
  usePlayFromKaraokeQueue,
} from "@/hooks/api/useKaraokeQueue";
import { Song } from "@/types/Song";
import { toast } from "sonner";

const Stage: React.FC = () => {
  const {
    currentTime,
    seek,
    connect,
    disconnect,
    connected,
    cleanup,
    setSongAndLoad,
    socket,
  } = useKaraokePlayerStore();

  const { useSong } = useSongs();

  // API hooks
  const queueQuery = useQueue();
  const removeFromQueueMutation = useRemoveFromKaraokeQueue();
  const playFromQueueMutation = usePlayFromKaraokeQueue();

  // Get the current song (position 0) from the queue
  const currentQueueItem = queueQuery.data?.find((item) => item.position === 0);
  const currentSongId = currentQueueItem?.song?.id;

  const { data: currentSong } = useSong(currentSongId ?? "");

  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  useEffect(() => {
    if (currentSong) {
      setSongAndLoad(currentSong.id, currentSong.durationMs);
    }
    return () => cleanup();
  }, [currentSong, setSongAndLoad, cleanup]);

  // WebSocket effect for queue updates
  useEffect(() => {
    if (!socket || !connected) return;

    // Join the karaoke queue room
    socket.emit("join_queue_room", {});

    const handleQueueUpdate = () => {
      console.log("Queue updated via WebSocket, refetching queue data");
      queueQuery.refetch();
    };

    const handlePlaySong = (data: { song: Song; singer: string }) => {
      console.log(
        `Song played via WebSocket: ${data.song.title} by ${data.song.artist}`
      );

      // Refetch queue data since positions have changed
      queueQuery.refetch();

      // Automatically load the song into the player
      setSongAndLoad(data.song.id, data.song.durationMs).catch((error) => {
        console.error("Failed to load song from WebSocket:", error);
        toast.error("Failed to load song");
      });
    };

    // Set up WebSocket event listeners
    socket.on("queue_updated", handleQueueUpdate);
    socket.on("play_song", handlePlaySong);

    // Cleanup
    return () => {
      socket.off("queue_updated", handleQueueUpdate);
      socket.off("play_song", handlePlaySong);
      socket.emit("leave_queue_room", {});
    };
  }, [socket, connected, queueQuery, setSongAndLoad]);

  const handleRemoveFromQueue = async (id: string) => {
    try {
      await removeFromQueueMutation.mutateAsync(id);
      // Queue will be updated automatically via WebSocket
      toast.success("Song removed from queue");
    } catch (error) {
      console.error("Failed to remove song from queue:", error);
      toast.error("Failed to remove song from queue");
    }
  };

  const handlePlayFromQueue = async (id: string) => {
    try {
      await playFromQueueMutation.mutateAsync(id);
      // Queue and song loading will be handled automatically via WebSocket
      toast.success("Song is being loaded...");
    } catch (error) {
      console.error("Failed to play song from queue:", error);
      toast.error("Failed to play song from queue");
    }
  };

  return (
    <AppLayout>
      <div className="flex flex-col gap-4 min-h-full p-6 relative z-20">
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
            durationMs={currentSong?.durationMs || 0}
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
