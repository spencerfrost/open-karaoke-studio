/**
 * A song's fixed lines: what each said before, what it says now, and Undo.
 *
 * A fix the lyrics no longer show (its line is gone after new lyrics, or
 * someone changed it by hand since) is marked, so an admin can put it back
 * by hand or let it go.
 */

import React from "react";
import { Undo2 } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  useLyricsLineFixes,
  useUndoLineFix,
  type LineFixAlignStatus,
  type LyricsLineFix,
} from "@/hooks/api/useLyricsLineFixes";
import { describeWhen } from "@/features/admin/review/describeWhen";

const TIMING_LABEL: Record<LineFixAlignStatus, string | null> = {
  pending: "Timing the words…",
  aligned: null,
  failed: "Couldn't time the new words; the line keeps its old timing",
  no_timing: null,
};

const LineFixRow: React.FC<{ fix: LyricsLineFix }> = ({ fix }) => {
  const undoFix = useUndoLineFix();
  const timing = TIMING_LABEL[fix.alignStatus];

  const undo = () =>
    undoFix.mutate(fix, {
      onSuccess: ({ restored }) =>
        toast.success(
          restored ? "Put the line's old words back" : "Fix removed",
        ),
      onError: (error) => toast.error(error.message),
    });

  return (
    <li className="flex items-start justify-between gap-3 py-2">
      <div className="min-w-0 space-y-0.5 text-sm">
        <p className="text-muted-foreground line-through">{fix.oldText}</p>
        <p className="font-medium">{fix.newText}</p>
        <p className="text-xs text-muted-foreground">
          {fix.fixedBy ?? "Someone"}, {describeWhen(fix.updatedAt)}
          {timing && ` · ${timing}`}
        </p>
        {!fix.shown && (
          <Badge variant="outline">Not on screen: the lyrics changed</Badge>
        )}
      </div>
      <Button
        size="sm"
        variant="outline"
        disabled={undoFix.isPending}
        onClick={undo}
        title={
          fix.shown
            ? "Put the line's old words back"
            : "Forget this fix; the lyrics stay as they are"
        }
      >
        <Undo2 aria-hidden="true" />
        Undo
      </Button>
    </li>
  );
};

interface LineFixesListProps {
  songId: string;
  /** Shown when the song has no fixes; nothing when left out. */
  emptyText?: string;
}

export const LineFixesList: React.FC<LineFixesListProps> = ({
  songId,
  emptyText,
}) => {
  const { data: fixes, isLoading, error } = useLyricsLineFixes(songId);

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading fixes…</p>;
  }
  if (error) {
    return (
      <p className="text-sm text-destructive">
        Couldn't load the fixed lines: {error.message}
      </p>
    );
  }
  if (!fixes?.length) {
    return emptyText ? (
      <p className="py-8 text-center text-sm text-muted-foreground">
        {emptyText}
      </p>
    ) : null;
  }
  return (
    <ul className="divide-y divide-border">
      {fixes.map((fix) => (
        <LineFixRow key={fix.id} fix={fix} />
      ))}
    </ul>
  );
};
