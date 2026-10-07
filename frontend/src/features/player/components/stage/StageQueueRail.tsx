/**
 * StageQueueRail - the right rail: who is singing and who is next. The join
 * code under it is StageJoinCode, which stays up while the rail collapses.
 * Full replacement for the old KaraokeQueueList/Item pair.
 */

import React from "react";
import { Library, Mic, Play, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useOpenSongSelect } from "@/hooks/useOpenSongSelect";
import { cn } from "@/lib/utils";
import type { KaraokeQueueItemWithSong } from "@/types/KaraokeQueue";

const cardClass =
  "flex flex-col gap-2.5 rounded-md border border-glass-border/10 bg-glass/5 p-3.5";
const railLabelClass =
  "text-[0.9375rem] font-semibold uppercase tracking-[0.08em] text-foreground/70";

interface StageQueueRailProps {
  current?: KaraokeQueueItemWithSong | null;
  upcoming: KaraokeQueueItemWithSong[];
  onPlay?: (id: string) => void;
  onRemove?: (id: string) => void;
}

const StageQueueRail: React.FC<StageQueueRailProps> = ({
  current,
  upcoming,
  onPlay,
  onRemove,
}) => {
  const openSongSelect = useOpenSongSelect();

  return (
    // h-full so the rail is bounded by the stage row rather than by its own
    // content — that is what lets "Up Next" scroll instead of growing and
    // shoving the join code below it off the bottom of the screen.
    <div className="flex h-full min-h-0 flex-col gap-4">
      <div className={cn(cardClass, "shrink-0")}>
        <span className={railLabelClass}>Singing Now</span>
        <div className="flex items-center gap-3">
          <Mic className="size-6 shrink-0 text-primary" />
          <span className="min-w-0 truncate font-display text-2xl font-bold text-foreground">
            {current?.singer ?? "—"}
          </span>
        </div>
        {current && (
          <span className="truncate text-base text-foreground/50">
            {current.song.title} · {current.song.artist}
          </span>
        )}
      </div>

      <div className={cn(cardClass, "min-h-0 flex-1 gap-4")}>
        <div className="flex shrink-0 items-center justify-between">
          <span className={railLabelClass}>Up Next</span>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => openSongSelect()}
            aria-label="Open the songbook"
            className="text-foreground/40 hover:text-foreground"
          >
            <Library className="size-4.5" />
          </Button>
        </div>

        {upcoming.length === 0 ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-4 text-center">
            <p className="text-lg text-foreground/60">Nothing queued yet</p>
          </div>
        ) : (
          <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto">
            {upcoming.map((item, index) => (
              <div key={item.id} className="group flex items-center gap-3.5">
                <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary/20 font-accent text-xl text-primary">
                  {index + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-lg font-semibold text-foreground">
                    {item.song.title}
                  </div>
                  <div className="truncate text-base text-foreground/50">
                    {item.singer} · {item.song.artist}
                  </div>
                </div>
                {/* Held at zero opacity rather than unmounted so hovering a row
                    never shifts the list under the pointer */}
                <div className="flex shrink-0 items-center opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
                  {onPlay && (
                    <Button
                      variant="icon"
                      size="icon"
                      onClick={() => onPlay(item.id)}
                      aria-label={`Play ${item.song.title} now`}
                    >
                      <Play className="size-4.5 fill-success text-success" />
                    </Button>
                  )}
                  {onRemove && (
                    <Button
                      variant="icon"
                      size="icon"
                      onClick={() => onRemove(item.id)}
                      aria-label={`Remove ${item.song.title} from the queue`}
                    >
                      <X className="size-4.5 text-destructive" />
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default StageQueueRail;
