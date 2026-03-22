import React from "react";
import { Song } from "@/types/Song";
import {
  SongCard,
  PerformerSongCard,
} from "@/features/songs/components/song-card";
import { useSessionStore } from "@/stores/sessionStore";
import { useSongs as useSongsHook } from "@/hooks/api/useSongs";
import LoadingSpinner from "@/components/ui/LoadingSpinner";

interface RecentlyAddedSongsProps {
  maxSongs?: number;
}

const RecentlyAddedSongs: React.FC<RecentlyAddedSongsProps> = ({
  maxSongs = 48,
}) => {
  const { isHost } = useSessionStore();
  const CardComponent = isHost ? SongCard : PerformerSongCard;
  const { useSongs } = useSongsHook();
  const { data: allSongs, isLoading } = useSongs({
    limit: maxSongs,
    sort_by: "date_added",
    direction: "desc",
  });

  const songs = allSongs || [];

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <LoadingSpinner size={24} />
      </div>
    );
  }

  if (songs.length === 0) {
    return null;
  }

  return (
    <div className="mb-8 w-full">
      {/* Section Header */}
      <div className="flex items-center gap-3 mb-4">
        <span className="text-xl font-semibold text-orange-peel">
          Recently Added
        </span>
        <span className="text-sm text-lemon-chiffon/60">{songs.length} songs</span>
      </div>

      {/* Horizontally scrollable row — scrollbar hidden on mobile, visible on md+ */}
      <div
        className={[
          "flex gap-3 overflow-x-auto",
          // Hide scrollbar on mobile
          "[&::-webkit-scrollbar]:hidden md:[&::-webkit-scrollbar]:block",
          // Scrollbar height and track
          "md:[&::-webkit-scrollbar]:h-1.5",
          "md:[&::-webkit-scrollbar-track]:rounded-full md:[&::-webkit-scrollbar-track]:bg-white/10",
          // Scrollbar thumb
          "md:[&::-webkit-scrollbar-thumb]:rounded-full md:[&::-webkit-scrollbar-thumb]:bg-orange-peel/40",
          "md:hover:[&::-webkit-scrollbar-thumb]:bg-orange-peel/70",
          // Padding below for scrollbar space on desktop
          "pb-1 md:pb-3",
        ].join(" ")}
      >
        {songs.map((song: Song) => (
          <div
            key={song.id}
            className="flex-none w-[calc(50%-6px)] sm:w-[calc(33.333%-8px)] lg:w-[calc(16.667%-10px)]"
          >
            <CardComponent song={song} />
          </div>
        ))}
      </div>
    </div>
  );
};

export default RecentlyAddedSongs;
