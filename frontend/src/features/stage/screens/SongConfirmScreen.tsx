/**
 * SongConfirmScreen - "ready?" — the moment the cabinet asks who is singing.
 *
 * This is the step that fixes a real bug rather than just adding a screen: on
 * the stage, `useSongActions` silently files every walk-up under the host's own
 * display name, so the queue ends up as a wall of one person. Asking once, here,
 * costs a tap and makes the queue mean something.
 *
 * The name grid comes from the session roster (unit 3a) rather than
 * deduplicated queue strings, so it includes everyone who has joined, been
 * picked, or been added by name - not just people who have already queued a
 * song. "Someone else…" is also this screen's second caller: unit 4's "That's
 * not me" reuses it verbatim.
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
import type { SessionPerformer } from "@/types/SessionPerformer";
import { useStageShell } from "../StageShellContext";

interface SongConfirmScreenProps {
  song: Song;
  /** The session's roster, seat order. */
  roster: SessionPerformer[];
}

const SongConfirmScreen: React.FC<SongConfirmScreenProps> = ({
  song,
  roster,
}) => {
  const shell = useStageShell();

  const { getArtworkUrl } = useSongs();
  const { handlePlayAs, handleAddToQueue } = useSongActions(song);

  const [singer, setSinger] = useState(roster[0]?.name ?? "");
  // The free-text field only shows once someone taps "Someone else…" - the
  // common case is picking a name that's already on the roster.
  const [showOther, setShowOther] = useState(roster.length === 0);

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
          <Label className="text-lg">Who's singing?</Label>

          {!showOther && roster.length > 0 && (
            <div className="flex flex-wrap justify-center gap-3">
              {roster.map((performer) => (
                <Button
                  key={performer.id}
                  variant={singer === performer.name ? "primary" : "outline"}
                  size="lg"
                  onClick={() => setSinger(performer.name)}
                  className="rounded-full text-lg"
                >
                  {performer.name}
                </Button>
              ))}
              <Button
                variant="ghost"
                size="lg"
                onClick={() => {
                  setSinger("");
                  setShowOther(true);
                }}
                className="rounded-full text-lg"
              >
                Someone else…
              </Button>
            </div>
          )}

          {showOther && (
            <div className="space-y-2">
              <Input
                id="stage-singer"
                value={singer}
                onChange={(e) => setSinger(e.target.value)}
                placeholder="Enter a name"
                maxLength={50}
                autoFocus
                className="h-14 text-center text-2xl"
              />
              {roster.length > 0 && (
                <Button
                  variant="ghost"
                  onClick={() => {
                    setSinger(roster[0]?.name ?? "");
                    setShowOther(false);
                  }}
                >
                  Pick from the roster instead
                </Button>
              )}
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
