import React, { useState } from "react";
import { useParams } from "react-router-dom";

import AppLayout from "@/components/layout/AppLayout";
import KaraokePlayer from "@/components/karaoke-player/KaraokePlayer";

import { useSongs } from "@/hooks/api/useSongs";
import { useSessionStore } from "@/stores/sessionStore";
import { toast } from "sonner";

const SongPlayer: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  // Session state
  const [sessionCode, setSessionCode] = useState("");

  // Session store
  const { displayCode, joinSession } = useSessionStore();

  // Check if user is in a session
  const isInSession = !!displayCode;

  // Use the song query hook
  const { useSong } = useSongs();

  const {
    data: song,
    isLoading: songLoading,
    error: songError,
  } = useSong(id ?? "");

  const handleJoinSession = async () => {
    if (sessionCode.length === 4) {
      try {
        await joinSession(sessionCode, "controller");
        toast.success("Joined session successfully!");
      } catch (error) {
        console.error("Failed to join session:", error);
        toast.error("Failed to join session. Please check the code and try again.");
      }
    } else {
      toast.error("Please enter a 4-character session code.");
    }
  };

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

  return (
    <AppLayout>
      {!isInSession ? (
        <div className="flex flex-col items-center justify-center min-h-[60vh] gap-6">
          <h1 className="text-4xl font-bold text-orange-peel text-center">
            Join a Session
          </h1>
          <p className="text-xl text-center text-muted-foreground max-w-md">
            Enter the 4-character session code to play this song!
          </p>
          <div className="flex flex-col items-center gap-4 w-full max-w-sm">
            <input
              type="text"
              placeholder="ABCD"
              value={sessionCode}
              onChange={(e) => setSessionCode(e.target.value.toUpperCase())}
              className="w-full px-4 py-3 text-center text-2xl font-mono font-bold uppercase bg-background border-2 border-orange-peel rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-peel"
              maxLength={4}
            />
            <button
              onClick={handleJoinSession}
              className="w-full px-6 py-3 bg-orange-peel text-background font-semibold rounded-lg hover:bg-orange-peel/90 transition-colors disabled:opacity-50"
              disabled={sessionCode.length !== 4}
            >
              Join Session
            </button>
          </div>
        </div>
      ) : (
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
      )}
    </AppLayout>
  );
};

export default SongPlayer;
