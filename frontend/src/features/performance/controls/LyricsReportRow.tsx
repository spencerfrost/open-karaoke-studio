/**
 * LyricsReportRow - "Something wrong?  [Wrong words] [Out of sync]".
 *
 * Whoever is singing notices bad lyrics first. A report records it for an
 * admin and starts a fix: other lyrics for wrong words, a re-timing of the
 * same words for out of sync. Each button is used once per song; the
 * bookkeeping lives in useLyricsFixes.
 */

import React from "react";
import { Button } from "@/components/ui/button";
import type { LyricsReportKind } from "@/hooks/api/useLyricsReports";
import { LYRICS_REPORTS } from "../hooks/useLyricsFixes";

interface LyricsReportRowProps {
  reported: Set<LyricsReportKind>;
  disabled: boolean;
  onReport: (kind: LyricsReportKind) => void;
}

const LyricsReportRow: React.FC<LyricsReportRowProps> = ({
  reported,
  disabled,
  onReport,
}) => (
  <div className="flex flex-col gap-2">
    <span className="text-sm uppercase tracking-[0.08em] text-foreground-dim">
      Something wrong?
    </span>
    <div className="flex gap-2">
      {LYRICS_REPORTS.map(({ kind, label }) => {
        const isReported = reported.has(kind);
        return (
          <Button
            key={kind}
            variant="outline"
            disabled={disabled || isReported}
            onClick={() => onReport(kind)}
            className="h-11 flex-1 text-base font-semibold"
          >
            {isReported ? "Reported" : label}
          </Button>
        );
      })}
    </div>
  </div>
);

export default LyricsReportRow;
