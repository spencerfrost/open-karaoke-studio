import React from "react";
import { CardContent } from "@/components/ui/card";
import { formatTimeMs } from "@/utils/formatters";
import { SongInfoProps } from "./SongCard.types";

export const SongInfo: React.FC<SongInfoProps> = ({ song }) => {
  return (
    <CardContent className="p-3 flex-1">
      <div className="flex justify-between items-start">
      <h3
        className="font-medium truncate whitespace-nowrap"
        title={song.title}
      >
        {song.title?.length > 50 ? song.title.slice(0, 47) + "..." : song.title}
      </h3>
      <span className="text-xs opacity-60 whitespace-nowrap">
        {formatTimeMs(song.durationMs || 0)}
      </span>
      </div>
      <p
      className="text-sm opacity-75 truncate whitespace-nowrap"
      title={song.artist}
      >
      {song.artist?.length > 50 ? song.artist.slice(0, 47) + "..." : song.artist}
      </p>
      <div className="flex gap-2 justify-between items-center mt-1">
      <p
        className="text-xs text-secondary truncate whitespace-nowrap"
        title={song.album}
      >
        {song.album && song.album.length > 50 ? song.album.slice(0, 25) + "..." : song.album}
      </p>
      </div>
    </CardContent>
  );
};