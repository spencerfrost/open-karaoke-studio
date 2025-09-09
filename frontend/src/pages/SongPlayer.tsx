import React from "react";
import { useParams } from "react-router-dom";

import AppLayout from "@/components/layout/AppLayout";
import KaraokePlayer from "@/components/karaoke-player/KaraokePlayer";

import { useSongs } from "@/hooks/api/useSongs";

const SongPlayer: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  // Use the song query hook
  const { useSong } = useSongs();

  const {
    data: song,
    isLoading: songLoading,
    error: songError,
  } = useSong(id ?? "");

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
