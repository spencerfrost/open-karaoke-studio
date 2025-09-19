import React, { useEffect } from "react";
import { useParams } from "react-router-dom";

import AppLayout from "@/components/layout/AppLayout";
import KaraokePlayer from "@/components/karaoke-player/KaraokePlayer";

import { useSongs } from "@/hooks/api/useSongs";
import { useSessionStore } from "@/stores/sessionStore";
import { toast } from "sonner";

const SongPlayer: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  // Session store
  const { 
    displayCode, 
    createSession, 
    recoverSession,  // Changed from recoverHostSession
    isRecovering,
    recoveryError,
    isConnecting,
    connectionError 
  } = useSessionStore();

  // Check if user is in a session
  const isInSession = !!displayCode;

  // Use the song query hook
  const { useSong } = useSongs();

  const {
    data: song,
    isLoading: songLoading,
    error: songError,
  } = useSong(id ?? "");

  // Recover existing host session or create new one on mount
  useEffect(() => {
    const initializeSession = async () => {
      if (!displayCode) {
        try {
          // First try to recover existing session (host or performer)
          await recoverSession();
          
          // If recovery didn't work (no stored session), create new host session
          const state = useSessionStore.getState();
          if (!state.displayCode) {
            await createSession("stage");
          }
        } catch (error) {
          console.error("Failed to initialize session:", error);
          toast.error("Failed to initialize session");
        }
      }
    };

    initializeSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (songLoading) {
    return (
      <AppLayout>
        <div className="flex flex-col items-center justify-center h-full">
          <div className="text-lg text-orange-peel animate-pulse">
            Loading song...
          </div>
        </div>
      </AppLayout>
    );
  }
  
  if (songError || !song) {
    return (
      <AppLayout>
        <div className="flex flex-col items-center justify-center h-full">
          <div className="text-lg text-destructive">
            {songError instanceof Error ? songError.message : "Song not found."}
          </div>
        </div>
      </AppLayout>
    );
  }

  // Show loading state during session recovery or creation
  if (isRecovering || (isConnecting && !isInSession)) {
    return (
      <AppLayout>
        <div className="flex flex-col items-center justify-center h-full gap-6">
          <h1 className="text-4xl font-bold text-orange-peel text-center">
            {isRecovering ? "Restoring Session" : "Creating Session"}
          </h1>
          <p className="text-xl text-center text-muted-foreground max-w-md">
            {isRecovering 
              ? "Reconnecting to your existing karaoke session..." 
              : "Setting up your karaoke session..."
            }
          </p>
          {(recoveryError || connectionError) && (
            <div className="text-center text-destructive">
              {recoveryError || connectionError}
            </div>
          )}
          <div className="flex justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-peel"></div>
          </div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="w-full h-full flex flex-col items-center justify-center p-4">
        <div className="aspect-video w-full max-w-[90vw] max-h-[90vh] bg-black/80 rounded-xl overflow-hidden flex items-center justify-center relative">
          <KaraokePlayer
            songId={song.id}
            size="full"
            autoPlay={false}
            controls={true}
            showInfo={true}
            showVisualizer={true}
          />
        </div>
      </div>
    </AppLayout>
  );
};

export default SongPlayer;
