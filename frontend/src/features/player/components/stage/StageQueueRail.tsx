/**
 * StageQueueRail - the right rail: who is singing, who is next, and the QR
 * code to join. Full replacement for the old KaraokeQueueList/Item pair.
 */

import React from "react";
import { Library, Mic, Play, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { QRCodeDisplay } from "@/features/queue";
import { useOpenSongSelect } from "@/hooks/useOpenSongSelect";
import { useSessionStore } from "@/stores/sessionStore";
import { cn } from "@/lib/utils";
import type { KaraokeQueueItemWithSong } from "@/types/KaraokeQueue";

const cardClass =
  "flex flex-col gap-2.5 rounded-md border border-glass-border/10 bg-glass/5 p-[18px]";
const railLabelClass =
  "text-[17px] font-semibold uppercase tracking-[0.08em] text-foreground/70";

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
  const { displayCode } = useSessionStore();
  const openSongSelect = useOpenSongSelect();

  return (
    // h-full so the rail is bounded by the stage row rather than by its own
    // content — that is what lets "Up Next" scroll instead of growing and
    // shoving the join code off the bottom of the screen.
    <div className="flex h-full min-h-0 flex-col gap-4">
      <div className={cn(cardClass, "shrink-0")}>
        <span className={railLabelClass}>Singing Now</span>
        <div className="flex items-center gap-3">
          <Mic size={26} className="shrink-0 text-primary" />
          <span className="min-w-0 truncate font-display text-[28px] font-bold text-foreground">
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
            aria-label="Browse library"
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
                <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-primary/20 font-accent text-2xl text-primary">
                  {index + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-[21px] font-semibold text-foreground">
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

      {displayCode && (
        <div className="flex flex-col shrink-0 items-center gap-4 rounded-md border border-glass-border/10 bg-glass/5 p-2">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-lg uppercase tracking-[0.08em] text-foreground/60">Join Code:</span>
              <span className="font-accent text-4xl leading-tight text-primary">{displayCode}</span>
            </div>
          </div>
          <QRCodeDisplay
            value={`${window.location.origin}/join/${displayCode}`}
            size={180}
            className="shrink-0 mb-2"
          />
        </div>
      )}
    </div>
  );
};

export default StageQueueRail;
