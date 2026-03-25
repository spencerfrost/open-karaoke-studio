import React, { useState, useCallback } from "react";
import { ListPlus, Check, Music } from "lucide-react";
import {
  Drawer,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
  DrawerDescription,
  DrawerFooter,
} from "@/components/ui/drawer";
import { Button } from "@/components/ui/button";
import { useSessionStore } from "@/stores/sessionStore";
import { useSongActions } from "../../hooks/useSongActions";
import { useSongs } from "@/hooks/api/useSongs";
import { formatTime } from "@/utils/formatters";
import { getSongDuration } from "@/utils/songUtils";
import { Song } from "@/types/Song";
import { SongAudioPreview } from "./SongAudioPreview";
import { LyricsPreview } from "./LyricsPreview";
import { InlineJoinForm } from "./InlineJoinForm";

interface PerformerSongDrawerProps {
  song: Song;
  isOpen: boolean;
  onClose: () => void;
}

export const PerformerSongDrawer: React.FC<PerformerSongDrawerProps> = ({
  song,
  isOpen,
  onClose,
}) => {
  const { displayCode, displayName } = useSessionStore();
  const songActions = useSongActions(song);
  const { getArtworkUrl } = useSongs();
  const artworkUrl = getArtworkUrl(song, "large");

  const isInSession = !!(displayCode && displayName);
  const isProcessed = song.status === "processed";

  const [addedToQueue, setAddedToQueue] = useState(false);

  const handleAddToQueue = useCallback(
    (singerName?: string) => {
      const name = singerName || displayName;
      if (!name) return;

      songActions.handleAddToQueue(name);
      setAddedToQueue(true);

      // Auto-close after showing success
      setTimeout(() => {
        setAddedToQueue(false);
        onClose();
      }, 1200);
    },
    [displayName, songActions, onClose],
  );

  const handleJoinSuccess = useCallback(
    (singerName: string) => {
      handleAddToQueue(singerName);
    },
    [handleAddToQueue],
  );

  const handleOpenChange = (open: boolean) => {
    if (!open) {
      setAddedToQueue(false);
      onClose();
    }
  };

  return (
    <Drawer open={isOpen} onOpenChange={handleOpenChange}>
      <DrawerContent className="max-h-[85vh]">
        <div className="overflow-y-auto">
          <DrawerHeader className="pb-2">
            {/* Artwork + Song Info */}
            <div className="flex gap-4 items-start text-left">
              <div className="size-20 shrink-0 rounded-lg overflow-hidden bg-muted">
                {artworkUrl ? (
                  <img
                    src={artworkUrl}
                    alt={song.title}
                    className="size-full object-cover"
                  />
                ) : (
                  <div className="size-full flex items-center justify-center">
                    <Music size={32} className="text-muted-foreground" />
                  </div>
                )}
              </div>
              <div className="flex-1 min-w-0">
                <DrawerTitle className="text-lg leading-tight truncate">
                  {song.title}
                </DrawerTitle>
                <DrawerDescription className="mt-0.5 truncate">
                  {song.artist}
                </DrawerDescription>
                {song.album && (
                  <p className="text-xs text-muted-foreground mt-0.5 truncate">
                    {song.album}
                  </p>
                )}
                <p className="text-xs text-muted-foreground mt-1">
                  {formatTime(getSongDuration(song))}
                </p>
              </div>
            </div>
          </DrawerHeader>

          <div className="px-4 space-y-4 pb-2">
            {/* Audio Preview */}
            {isProcessed && (
              <div>
                <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
                  Preview
                </h4>
                <SongAudioPreview songId={song.id} />
              </div>
            )}

            {/* Lyrics Preview */}
            <div>
              <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
                Lyrics
              </h4>
              <LyricsPreview
                plainLyrics={song.plainLyrics}
                syncedLyrics={song.syncedLyrics}
              />
            </div>
          </div>
        </div>

        {/* Action Area */}
        <DrawerFooter>
          {!isProcessed ? (
            <p className="text-sm text-muted-foreground text-center">
              This song is still processing and can&apos;t be queued yet.
            </p>
          ) : addedToQueue ? (
            <Button disabled className="w-full" variant="outline">
              <Check size={18} className="mr-2" />
              Added to Queue!
            </Button>
          ) : isInSession ? (
            <Button onClick={() => handleAddToQueue()} className="w-full">
              <ListPlus size={18} className="mr-2" />
              Add to Queue
            </Button>
          ) : (
            <InlineJoinForm
              onJoinSuccess={handleJoinSuccess}
              songTitle={song.title}
            />
          )}
        </DrawerFooter>
      </DrawerContent>
    </Drawer>
  );
};
