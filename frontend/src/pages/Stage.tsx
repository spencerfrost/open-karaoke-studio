import React, { useEffect } from "react";
import AppLayout from "@/components/layout/AppLayout";
import KaraokeQueueList from "@/components/karaoke-queue/KaraokeQueueList";
import KaraokePlayer from "@/components/karaoke-player/KaraokePlayer";

import { useSongs } from "@/hooks/api/useSongs";
import { useSessionStore } from "@/stores/sessionStore";
import {
  useQueue,
  useRemoveFromKaraokeQueue,
  usePlayFromKaraokeQueue,
} from "@/hooks/api/useKaraokeQueue";
import { sessionWebSocketService } from "@/services/sessionWebSocketService";
import { toast } from "sonner";

const Stage: React.FC = () => {
  const { displayCode, createSession } = useSessionStore();

  const { useSong } = useSongs();

  // Create session on mount if not already in one
  useEffect(() => {
    if (!displayCode) {
      createSession("stage").catch((error) => {
        console.error("Failed to create session:", error);
        toast.error("Failed to create session");
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [displayCode]);

  // API hooks
  const queueQuery = useQueue(displayCode || undefined);
  const removeFromQueueMutation = useRemoveFromKaraokeQueue(displayCode || undefined);
  const playFromQueueMutation = usePlayFromKaraokeQueue(displayCode || undefined);

  // Get the current song (position 0) from the queue
  const currentQueueItem = queueQuery.data?.find((item) => item.position === 0);
  const currentSongId = currentQueueItem?.song?.id;

  const { data: currentSong } = useSong(currentSongId ?? "");

  // WebSocket effect for queue updates using unified session WebSocket
  useEffect(() => {
    const handleQueueUpdate = () => {
      console.log("Queue updated via unified session WebSocket, refetching queue data");
      queueQuery.refetch();
    };

    const handleQueueJoined = (data: { room?: string } = {}) => {
      console.log("Joined queue room:", data?.room);
      // Request initial queue state
      sessionWebSocketService.requestQueueUpdate();
    };

    // Set up WebSocket event listeners using unified session service
    const cleanupJoined = sessionWebSocketService.on("queue_joined", handleQueueJoined);
    const cleanupUpdated = sessionWebSocketService.on("queue_updated", handleQueueUpdate);

    // Cleanup
    return () => {
      cleanupJoined();
      cleanupUpdated();
    };
  }, [queueQuery]);

  const handleRemoveFromQueue = async (id: string) => {
    try {
      await removeFromQueueMutation.mutateAsync(id);
      // Notify unified WebSocket service about queue changes
      sessionWebSocketService.notifyQueueChanged();
      toast.success("Song removed from queue");
    } catch (error) {
      console.error("Failed to remove song from queue:", error);
      toast.error("Failed to remove song from queue");
    }
  };

  const handlePlayFromQueue = async (id: string) => {
    try {
      await playFromQueueMutation.mutateAsync(id);
      // Notify unified WebSocket service about queue changes
      sessionWebSocketService.notifyQueueChanged();
      toast.success("Song is being loaded...");
    } catch (error) {
      console.error("Failed to play song from queue:", error);
      toast.error("Failed to play song from queue");
    }
  };

  return (
    <AppLayout>
      <div className="flex flex-col gap-4 min-h-full p-6 relative z-20">

        <div className="aspect-video w-full max-w-[90vw] max-h-[90vh] bg-black/80 rounded-xl overflow-hidden">
          <KaraokePlayer
            songId={currentSong?.id || ""}
            size="full"
            autoPlay={false}
            controls={true}
            showInfo={true}
            showVisualizer={true}
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
