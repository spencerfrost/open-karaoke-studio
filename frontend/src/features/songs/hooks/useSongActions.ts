import { useNavigate } from "react-router-dom";
import { useSongs } from "@/hooks/api/useSongs";
import { useAddToKaraokeQueue } from "@/hooks/api/useKaraokeQueue";
import { useSessionStore } from "@/stores/sessionStore";
import { Song } from "@/types/Song";

export interface SongActionsConfig {
  onPlay?: (song: Song) => void;
  enableDelete?: boolean;
  enableDetails?: boolean;
}

export const useSongActions = (song: Song, config: SongActionsConfig = {}, sessionId?: string) => {
  const navigate = useNavigate();
  const { useDeleteSong } = useSongs();
  const { displayCode, displayName } = useSessionStore();
  
  // Use the provided sessionId or fall back to the current session from store
  const currentSessionId = sessionId || (displayCode ? displayCode : undefined);
  
  const addToKaraokeQueue = useAddToKaraokeQueue(currentSessionId);
  const deleteSongMutation = useDeleteSong();

  const handlePlay = (e?: React.MouseEvent) => {
    if (e) e.stopPropagation();

    if (config.onPlay) {
      config.onPlay(song);
    } else {
      navigate(`/player/${song.id}`);
    }
  };

  const handleAddToQueue = (singerName: string, sessionCode?: string) => {
    addToKaraokeQueue.mutate({ songId: song.id, singer: singerName }, {
      onSuccess: () => {
        // If we joined a session, we might want to refresh session info
        if (sessionCode) {
          // Could add session refresh logic here if needed
        }
      }
    });
  };

  const handleDelete = () => {
    return deleteSongMutation.mutate({ id: song.id });
  };

  const handleQueueClick = () => {
    // Check if user is in an active session
    if (displayCode && displayName) {
      // User is in session and has a display name, add directly to queue
      handleAddToQueue(displayName);
      return true;
    }
    // User not in session or no display name, need to show join dialog
    return false;
  };

  return {
    handlePlay,
    handleQueueClick,
    handleAddToQueue,
    handleDelete,
    isDeleting: deleteSongMutation.isPending,
    deleteError: deleteSongMutation.isError,
  };
};
