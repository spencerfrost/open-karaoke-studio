/**
 * SongConfirmScreen - "ready?" — the moment the cabinet asks who is singing.
 *
 * This is the step that fixes a real bug rather than just adding a screen: on
 * the stage, `useSongActions` silently files every walk-up under the host's own
 * display name, so the queue ends up as a wall of one person. Asking once, here,
 * costs a tap and makes the queue mean something.
 *
 * The chip row is deliberately a stand-in. Unit 3's roster replaces these
 * deduplicated queue strings with real performer entries.
 */

import React, { useState } from "react";
import { toast } from "sonner";
import { ChevronLeft, ListPlus, Mic } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useSongs } from "@/hooks/api/useSongs";
import { useSongActions } from "@/features/songs/hooks/useSongActions";
import type { Song } from "@/types/Song";
import { useStageShell } from "../StageShellContext";

interface SongConfirmScreenProps {
  song: Song;
  /** Names already used in this session's queue, most recent first. */
  recentSingers: string[];
}

const SongConfirmScreen: React.FC<SongConfirmScreenProps> = ({
  song,
  recentSingers,
}) => {
  const shell = useStageShell();

  const { getArtworkUrl } = useSongs();
  const { handlePlayAs, handleAddToQueue } = useSongActions(song);

  // Seeded with the most recent singer: at a small party the same person often
  // queues twice in a row, and it makes the field a confirmation, not a chore.
  const [singer, setSinger] = useState(recentSingers[0] ?? "");

  const trimmed = singer.trim();
  const canSubmit = trimmed.length > 0;
  const isReady = song.status === "processed";

  const handleSingNow = () => {
    if (!canSubmit) return;
    handlePlayAs(trimmed);
  };

  const handleQueue = () => {
    if (!canSubmit) return;
    handleAddToQueue(trimmed);
    toast.success(`Added "${song.title}" for ${trimmed}`);
    shell?.openSelect();
  };

  return (
    <div className="flex h-full w-full flex-col overflow-auto">
      <div className="shrink-0 px-6 pt-4">
        <Button
          variant="ghost"
          onClick={() => shell?.back()}
          className="text-foreground/60 hover:text-foreground"
        >
          <ChevronLeft className="mr-1 size-5" />
          Back
        </Button>
      </div>

      <div className="flex min-h-0 flex-1 flex-col items-center justify-center gap-8 p-6">
        <div className="flex items-center gap-6">
          <img
            src={getArtworkUrl(song, "medium") ?? undefined}
            alt=""
            className="size-40 rounded-lg object-cover shadow-xl"
          />
          <div className="max-w-xl">
            <h1 className="font-display text-4xl leading-tight text-foreground">
              {song.title}
            </h1>
            <h2 className="pt-2 text-2xl text-foreground/55">{song.artist}</h2>
          </div>
        </div>

        <div className="w-full max-w-xl space-y-4">
          <div className="space-y-2">
            <Label htmlFor="stage-singer" className="text-lg">
              Who's singing?
            </Label>
            <Input
              id="stage-singer"
              value={singer}
              onChange={(e) => setSinger(e.target.value)}
              placeholder="Enter a name"
              maxLength={50}
              autoFocus
              className="h-14 text-center text-2xl"
            />
          </div>

          {recentSingers.length > 0 && (
            <div className="flex flex-wrap justify-center gap-2">
              {recentSingers.map((name) => (
                <Button
                  key={name}
                  variant="outline"
                  size="sm"
                  onClick={() => setSinger(name)}
                  className="rounded-full"
                >
                  {name}
                </Button>
              ))}
            </div>
          )}
        </div>

        <div className="flex w-full max-w-xl gap-4">
          <Button
            variant="primary"
            size="lg"
            onClick={handleSingNow}
            disabled={!canSubmit || !isReady}
            className="h-16 flex-1 text-xl"
          >
            <Mic className="mr-2 size-6" />
            Sing it now
          </Button>
          <Button
            variant="accent"
            size="lg"
            onClick={handleQueue}
            disabled={!canSubmit}
            className="h-16 flex-1 text-xl"
          >
            <ListPlus className="mr-2 size-6" />
            Add to queue
          </Button>
        </div>

        {!isReady && (
          <p className="text-sm text-muted-foreground">
            Still processing — you can queue it, but it can't play yet.
          </p>
        )}
      </div>
    </div>
  );
};

export default SongConfirmScreen;
