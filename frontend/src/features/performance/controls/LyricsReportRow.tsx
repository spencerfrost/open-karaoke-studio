/**
 * LyricsReportRow - "Something wrong?  [Wrong words] [Out of sync]".
 *
 * Whoever is singing notices bad lyrics first. A report records it for an
 * admin and starts a fix: other lyrics for wrong words, a re-timing of the
 * same words for out of sync. Each button is used once per song.
 */

import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  useReportLyrics,
  type LyricsReportKind,
} from "@/hooks/api/useLyricsReports";
import { cn } from "@/lib/utils";
import type { Density } from "./density";

const REPORTS: Array<{
  kind: LyricsReportKind;
  label: string;
  thanks: string;
}> = [
  {
    kind: "words",
    label: "Wrong words",
    thanks: "Thanks — looking for better lyrics",
  },
  {
    kind: "timing",
    label: "Out of sync",
    thanks: "Thanks — re-timing the lyrics to the singing",
  },
];

interface LyricsReportRowProps {
  density: Density;
  songId: string | null;
  /** The song has lyrics on screen to report. */
  hasLyrics: boolean;
}

const LyricsReportRow: React.FC<LyricsReportRowProps> = ({
  density,
  songId,
  hasLyrics,
}) => {
  const isTv = density === "tv";
  const reportLyrics = useReportLyrics();
  const [reported, setReported] = useState<Set<LyricsReportKind>>(new Set());

  // A new song gets fresh buttons.
  useEffect(() => {
    setReported(new Set());
  }, [songId]);

  if (!hasLyrics) return null;

  const report = (kind: LyricsReportKind, thanks: string) => {
    if (!songId) return;
    reportLyrics.mutate(
      { songId, kind },
      {
        onSuccess: () => {
          setReported((previous) => new Set(previous).add(kind));
          toast.success(thanks);
        },
        onError: (error) => {
          toast.error(`Couldn't send that: ${error.message}`);
        },
      },
    );
  };

  return (
    <div className="flex flex-col gap-2">
      <span
        className={cn(
          "uppercase tracking-[0.08em] text-foreground/55",
          isTv ? "text-sm" : "text-xs",
        )}
      >
        Something wrong?
      </span>
      <div className="flex gap-2">
        {REPORTS.map(({ kind, label, thanks }) => {
          const isReported = reported.has(kind);
          return (
            <Button
              key={kind}
              variant="outline"
              disabled={!songId || isReported || reportLyrics.isPending}
              onClick={() => report(kind, thanks)}
              className={cn(
                "flex-1 font-semibold",
                isTv ? "h-11 text-base" : "h-11 text-sm",
              )}
            >
              {isReported ? "Reported" : label}
            </Button>
          );
        })}
      </div>
    </div>
  );
};

export default LyricsReportRow;
