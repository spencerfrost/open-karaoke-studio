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
      <div className="w-full max-w-3xl mx-auto">
        <h1 className="text-3xl font-bold text-center mb-2 text-orange-peel">
          {song.title}
        </h1>
        <h2 className="text-xl text-center mb-4 text-background/80">
          {song.artist}
        </h2>
        <div className="aspect-video w-full bg-black/80 rounded-xl overflow-hidden mb-4 flex items-center justify-center relative">
          <KaraokePlayer
            songId={song.id}
            size="full"
            autoPlay={false}
            controls={true}
            showInfo={false}
            showVisualizer={true}
          />
        </div>
      </div>
    </AppLayout>
  );
};

export default SongPlayer;
