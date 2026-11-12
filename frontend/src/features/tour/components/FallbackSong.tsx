/**
 * FallbackSong - a song already in the library, offered when the visitor's
 * own can't be had (quota, busy, failed). Started with the same "Sing this"
 * path as the processing list, so the tour carries on from the countdown.
 */

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemTitle,
} from "@/components/ui/item";
import { useSingThis } from "@/features/stage/hooks/useSingThis";
import type { Song } from "@/types/Song";

const FallbackSong: React.FC<{ song: Song }> = ({ song }) => {
  const start = useSingThis(song);
  const [starting, setStarting] = useState(false);

  const handleClick = async () => {
    setStarting(true);
    try {
      await start();
    } finally {
      setStarting(false);
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <Item size="sm" variant="muted" className="gap-3 px-3 py-2">
        <ItemContent className="min-w-0 gap-0.5">
          <ItemTitle className="w-full min-w-0">
            <span className="truncate">{song.title}</span>
          </ItemTitle>
          <ItemDescription className="truncate">{song.artist}</ItemDescription>
        </ItemContent>
        <ItemActions>
          <Button
            variant="primary"
            size="sm"
            disabled={starting}
            onClick={handleClick}
          >
            Sing this
          </Button>
        </ItemActions>
      </Item>
      <p className="text-sm text-muted-foreground">
        Or pick anything on the wheel.
      </p>
    </div>
  );
};

export default FallbackSong;
