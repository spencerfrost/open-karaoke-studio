import React, { useEffect } from "react";

import AppLayout from "@/components/layout/AppLayout";
import KaraokeQueueList from "@/components/karaoke-queue/KaraokeQueueList";
import KaraokePlayer from "@/components/karaoke-player/KaraokePlayer";
import WebSocketStatus from "@/components/WebsocketStatus";

import { useSongs } from "@/hooks/api/useSongs";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import {
  useQueue,
  useRemoveFromKaraokeQueue,
  usePlayFromKaraokeQueue,
} from "@/hooks/api/useKaraokeQueue";
import { queueWebSocketService } from "@/services/queueWebSocketService";
import { toast } from "sonner";

const Stage: React.FC = () => {
  const {
    connect,
    disconnect,
    connected,
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

  // WebSocket effect for queue updates using FastAPI queue WebSocket
  useEffect(() => {
    const handleQueueUpdate = () => {
      console.log("Queue updated via FastAPI WebSocket, refetching queue data");
      queueQuery.refetch();
    };

    const handleQueueJoined = (data: { room: string }) => {
      console.log("Joined queue room:", data.room);
      // Request initial queue state
      queueWebSocketService.requestQueueUpdate();
    };

    // Set up WebSocket event listeners using FastAPI queue service
    const cleanupJoined = queueWebSocketService.on("queue_joined", handleQueueJoined);
    const cleanupUpdated = queueWebSocketService.on("queue_updated", handleQueueUpdate);

    // Cleanup
    return () => {
      cleanupJoined();
      cleanupUpdated();
    };
  }, [queueQuery]);

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
        <div className="aspect-video w-full max-w-[90vw] max-h-[90vh] bg-black/80 rounded-xl overflow-hidden">
          {currentSong && (
            <KaraokePlayer
              songId={currentSong.id}
              size="full"
              autoPlay={false}
              controls={true}
              showInfo={true}
              showVisualizer={true}
            />
          )}
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
