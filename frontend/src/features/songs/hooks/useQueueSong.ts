import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { useAddToKaraokeQueue } from "@/hooks/api/useKaraokeQueue";
import { useSessionStore } from "@/stores/sessionStore";
import { useAccess } from "@/hooks/useAccess";
import { useStageShell } from "@/features/stage";
import { Song } from "@/types/Song";

/**
 * Queueing a library song, wherever it's asked for: a song card, or the add
 * flow's "Sing it" on a song that's already in the songbook.
 *
 * Takes the song per call rather than per hook, so a caller that only has a
 * song's id can fetch it first.
 */
export const useQueueSong = (sessionId?: string) => {
  // Null everywhere but the stage.
  const shell = useStageShell();
  const queryClient = useQueryClient();
  const { sessionId: storeSessionId } = useSessionStore();
  const access = useAccess();
  const addToKaraokeQueue = useAddToKaraokeQueue(
    sessionId ?? storeSessionId ?? undefined,
  );

  const addToQueue = (
    song: Song,
    singerName: string,
    { announce = false }: { announce?: boolean } = {},
  ) => {
    addToKaraokeQueue.mutate(
      { songId: song.id, singer: singerName },
      {
        onSuccess: () => {
          if (announce) toast.success(`Added "${song.title}" to the queue`);
          queryClient.invalidateQueries({
            queryKey: ["karaoke-queue"],
          });
        },
        onError: () => toast.error(`"${song.title}" didn't make the queue`),
      },
    );
  };

  /**
   * `pickSinger` opens the caller's QueueSingerDialog. A host's device - the
   * stage browser, or any device on the account that owns the session - is
   * shared, so it asks who is singing instead of crediting the host's name.
   *
   * False when there's no session to queue into.
   */
  const queueSong = (song: Song, pickSinger: () => void): boolean => {
    // On the stage, queueing goes through the confirm screen so the singer is a
    // person rather than whoever happens to own the session.
    if (shell) {
      shell.openConfirm(song);
      return true;
    }

    if (access.inSession && (access.isStageDevice || access.isSessionOwner)) {
      pickSinger();
      return true;
    }

    // A guest in a session queues under their own name, straight away.
    if (access.inSession && access.singerName) {
      addToQueue(song, access.singerName, { announce: true });
      return true;
    }
    // No session to queue into - the gate means this can now only happen to
    // an account holder (a guest can't reach this screen without a session).
    return false;
  };

  return { queueSong, addToQueue };
};
