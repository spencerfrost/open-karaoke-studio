/**
 * ProcessingTrackerRow - one song's trip through the pipeline, as one row.
 *
 * Shared by the stage's processing list and the phone's add-song results. The
 * first line says what's happening in a guest's words ("Taking out the
 * vocals"); the pipeline's own message is the second, quieter line.
 *
 * A finished row asks the library whether the song came out playable - the
 * jobs feed only says the jobs are gone, not how they ended - and hands a
 * playable song to `renderReady` for the screen's own action.
 */

import React from "react";
import { Badge } from "@/components/ui/badge";
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemTitle,
} from "@/components/ui/item";
import { Progress } from "@/components/ui/progress";
import { useSongs } from "@/hooks/api/useSongs";
import { cn } from "@/lib/utils";
import type { Song } from "@/types/Song";
import type { TrackerRow } from "./jobTimeline";
import { stepLabel, WAITING_LABEL } from "./stepLabels";

interface ProcessingTrackerRowProps {
  row: TrackerRow;
  /** The action for a finished, playable song (the stage's "Sing this"). */
  renderReady?: (song: Song) => React.ReactNode;
  /** Shown on a finished song that didn't come out, e.g. a dismiss button. */
  renderFailed?: () => React.ReactNode;
  /** Hide the title, for a row that sits under its own search result. */
  hideTitle?: boolean;
  className?: string;
}

/** The first line for a song still in the pipeline. */
function pipelineLine(row: TrackerRow): string {
  if (row.phase === "waiting") {
    return row.ahead > 0
      ? `${WAITING_LABEL} · ${row.ahead} ahead`
      : WAITING_LABEL;
  }
  const label = stepLabel(row.step);
  return row.stepNumber
    ? `${label} · step ${row.stepNumber} of ${row.stepCount}`
    : label;
}

type Outcome = "ready" | "failed" | "pending";

export const ProcessingTrackerRow: React.FC<ProcessingTrackerRowProps> = ({
  row,
  renderReady,
  renderFailed,
  hideTitle = false,
  className,
}) => {
  const finished = row.phase === "finished";
  // Only a finished row asks; an empty id leaves the query disabled.
  const { useSong } = useSongs();
  const { data: song } = useSong(finished ? row.songId : "");
  let outcome: Outcome | null = null;
  if (finished) {
    if (song?.status === "processed") outcome = "ready";
    else if (song?.status === "error") outcome = "failed";
    else outcome = "pending";
  }

  return (
    <Item
      size="sm"
      variant={row.isMine ? "muted" : "default"}
      className={cn("gap-x-3 gap-y-1.5 px-3 py-2", className)}
    >
      <ItemContent className="min-w-0 gap-0.5">
        {!hideTitle && (
          <ItemTitle className="w-full min-w-0">
            <span className="truncate">{row.title ?? "A new song"}</span>
            {row.isMine && (
              <Badge variant="secondary" className="shrink-0">
                Yours
              </Badge>
            )}
          </ItemTitle>
        )}
        {outcome === "ready" && (
          <ItemDescription className="text-primary">
            Ready to sing
          </ItemDescription>
        )}
        {outcome === "failed" && (
          <ItemDescription className="text-destructive">
            Couldn't get this one ready
          </ItemDescription>
        )}
        {outcome === "pending" && (
          <ItemDescription>Almost ready</ItemDescription>
        )}
        {!finished && <ItemDescription>{pipelineLine(row)}</ItemDescription>}
        {row.phase === "working" && row.detail && (
          <p className="truncate text-xs text-foreground-faint">{row.detail}</p>
        )}
      </ItemContent>
      {outcome === "ready" && song && renderReady && (
        <ItemActions>{renderReady(song)}</ItemActions>
      )}
      {outcome === "failed" && renderFailed && (
        <ItemActions>{renderFailed()}</ItemActions>
      )}
      {row.phase === "working" && (
        <Progress
          value={row.progress}
          aria-label={`${stepLabel(row.step)}, ${row.progress}%`}
          className="h-1.5 basis-full"
        />
      )}
    </Item>
  );
};
