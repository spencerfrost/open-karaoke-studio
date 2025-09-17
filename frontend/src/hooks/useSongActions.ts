import { useNavigate } from "react-router-dom";
import { useSongs } from "@/hooks/api/useSongs";
import { useAddToKaraokeQueue } from "@/hooks/api/useKaraokeQueue";
import { Song } from "@/types/Song";

export interface SongActionsConfig {
  onPlay?: (song: Song) => void;
  enableDelete?: boolean;
  enableDetails?: boolean;
}

export const useSongActions = (song: Song, config: SongActionsConfig = {}, sessionId?: string) => {
  const navigate = useNavigate();
  const { useDeleteSong } = useSongs();
  const addToKaraokeQueue = useAddToKaraokeQueue(sessionId);
  const deleteSongMutation = useDeleteSong();

  const handlePlay = (e?: React.MouseEvent) => {
    if (e) e.stopPropagation();

    if (config.onPlay) {
      config.onPlay(song);
    } else {
      navigate(`/player/${song.id}`);
    }
  };

  const handleAddToQueue = (singerName: string) => {
    addToKaraokeQueue.mutate({ songId: song.id, singer: singerName });
  };

  const handleDelete = () => {
    return deleteSongMutation.mutate({ id: song.id });
  };

  return {
    handlePlay,
    handleAddToQueue,
    handleDelete,
    isDeleting: deleteSongMutation.isPending,
    deleteError: deleteSongMutation.isError,
  };
};
