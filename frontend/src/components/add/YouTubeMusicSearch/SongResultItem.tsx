import React from "react";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";
import { SongResultItemProps } from "./YouTubeMusicSearch.types";

export const SongResultItem: React.FC<SongResultItemProps> = ({
  song,
  isAdding,
  onAddToLibrary,
}) => {
  return (
    <li className="py-3 flex items-center">
      {song.thumbnails?.[0]?.url && (
        <img
          src={song.thumbnails[0].url}
          alt={song.title}
          className="w-12 h-12 rounded mr-3 object-cover"
        />
      )}
      <div className="flex-1">
        <div className="font-medium">{song.title}</div>
        <div className="text-sm text-muted-foreground">
          {song.artist} • {song.duration}
        </div>
        {song.album && (
          <div className="text-xs text-muted-foreground">
            Album: {song.album}
          </div>
        )}
      </div>
      <Button
        onClick={() => onAddToLibrary(song)}
        disabled={isAdding}
        className="ml-4"
      >
        {isAdding ? (
          <>
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            Processing...
          </>
        ) : (
          "Add to Library"
        )}
      </Button>
    </li>
  );
};