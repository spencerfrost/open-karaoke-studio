/**
 * SongConfirmScreen - "ready?" — the moment the cabinet asks who is singing.
 *
 * This is the step that fixes a real bug rather than just adding a screen: on
 * the stage, `useSongActions` silently files every walk-up under the host's own
 * display name, so the queue ends up as a wall of one person. Asking once, here,
 * costs a tap and makes the queue mean something.
 *
 * The name grid itself lives in RosterPicker, because unit 4's handoff screen
 * asks the same question when someone taps "That's not me" - the second caller
 * this screen was built expecting.
 */

import React, { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { ChevronLeft, ListPlus, Mic } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { useSongs } from "@/hooks/api/useSongs";
import { useSongActions } from "@/features/songs/hooks/useSongActions";
import { cn } from "@/lib/utils";
import type { Song } from "@/types/Song";
import type { SessionPerformer } from "@/types/SessionPerformer";
import RosterPicker from "../components/RosterPicker";
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

  // The same four keys as the wheel, so a singer who arrived here on the
  // arrow keys can finish without the mouse:
  //   ▲▼ who's singing   ◀▶ which button   Enter do it   Back cancel
  // A song that cannot play yet starts on "Add to queue".
  const [choice, setChoice] = useState<"sing" | "queue">(
    isReady ? "sing" : "queue",
  );
  const keys = useRef({ handleSingNow, handleQueue, roster, singer, isReady });
  keys.current = { handleSingNow, handleQueue, roster, singer, isReady };
  const choiceRef = useRef(choice);
  choiceRef.current = choice;
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      const t = e.target instanceof HTMLElement ? e.target : null;
      // The "Someone else" field is typing, not navigating.
      if (t && ["INPUT", "TEXTAREA"].includes(t.tagName)) {
        if (e.key === "Escape") shell?.back();
        return;
      }
      if (t?.closest("[role='dialog']")) return;
      const k = keys.current;
      switch (e.key) {
        case "ArrowLeft":
        case "ArrowRight":
          e.preventDefault();
          if (e.key === "ArrowLeft" && k.isReady) setChoice("sing");
          if (e.key === "ArrowRight") setChoice("queue");
          return;
        case "ArrowUp":
        case "ArrowDown": {
          e.preventDefault();
          if (k.roster.length === 0) return;
          const i = k.roster.findIndex((p) => p.name === k.singer);
          const dir = e.key === "ArrowUp" ? -1 : 1;
          const next = (i + dir + k.roster.length) % k.roster.length;
          setSinger(k.roster[i === -1 ? 0 : next].name);
          setShowOther(false);
          return;
        }
        case "Enter":
          // A button the mouse just clicked keeps Enter for itself.
          if (t?.closest("button")) return;
          e.preventDefault();
          if (e.repeat) return;
          if (choiceRef.current === "sing") k.handleSingNow();
          else k.handleQueue();
          return;
        case "Backspace":
        case "Escape":
          e.preventDefault();
          shell?.back();
          return;
        default:
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [shell]);
  const chosenRing = "ring-4 ring-primary ring-offset-2 ring-offset-background";

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

          <RosterPicker
            roster={roster}
            value={singer}
            onChange={setSinger}
            showOther={showOther}
            onShowOtherChange={setShowOther}
          />
        </div>

        <div className="flex w-full max-w-xl gap-4">
          <Button
            variant="primary"
            size="lg"
            onClick={handleSingNow}
            disabled={!canSubmit || !isReady}
            className={cn(
              "h-16 flex-1 text-xl",
              choice === "sing" && chosenRing,
            )}
          >
            <Mic className="mr-2 size-6" />
            Sing it now
          </Button>
          <Button
            variant="accent"
            size="lg"
            onClick={handleQueue}
            disabled={!canSubmit}
            className={cn(
              "h-16 flex-1 text-xl",
              choice === "queue" && chosenRing,
            )}
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
