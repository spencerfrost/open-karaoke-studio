import React, { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { MessageSquareWarning } from "lucide-react";
import {
  useLyricsReports,
  useResolveLyricsReport,
  useUndoLyricsReport,
  type LyricsReport,
  type LyricsReportOutcome,
} from "@/hooks/api/useLyricsReports";
import { SongActionPanel } from "./SongActionPanel";
import type { Song } from "@/types/Song";

const KIND_LABEL: Record<LyricsReport["kind"], string> = {
  words: "Wrong words",
  timing: "Out of sync",
};

const OUTCOME_LABEL: Record<LyricsReportOutcome, string> = {
  replaced: "Replaced with other lyrics",
  retimed: "Re-timed to the singing",
  transcribed: "Replaced with a transcript of the singing",
  unchanged: "Couldn't fix it",
};

function describeWhen(iso: string | null): string {
  if (!iso) return "";
  // Stored as UTC without a zone marker.
  const when = new Date(
    iso.endsWith("Z") || iso.includes("+") ? iso : `${iso}Z`,
  );
  return when.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

/**
 * Lyrics reports from people singing: what they said, and what the app did
 * about it. Each stays listed until someone checks the song.
 */
export const LyricsReportsTab: React.FC = () => {
  const { data: reports, isLoading } = useLyricsReports();
  const resolveReport = useResolveLyricsReport();
  const undoReport = useUndoLyricsReport();
  const [expandedReportId, setExpandedReportId] = useState<number | null>(null);

  const resolve = (reportId: number) => {
    resolveReport.mutate(reportId, {
      onSuccess: () => {
        setExpandedReportId(null);
        toast.success("Report closed");
      },
      onError: (error) => toast.error(error.message),
    });
  };

  const undo = (report: LyricsReport) => {
    undoReport.mutate(report, {
      onSuccess: ({ restored }) => {
        setExpandedReportId(null);
        toast.success(
          restored
            ? "Put the reported lyrics back"
            : "Report removed. Those lyrics can be used again",
        );
      },
      onError: (error) => toast.error(error.message),
    });
  };

  const isBusy = resolveReport.isPending || undoReport.isPending;

  if (isLoading) {
    return <p className="py-12 text-center text-muted-foreground">Loading…</p>;
  }

  if (!reports?.length) {
    return (
      <div className="py-12 text-center text-muted-foreground">
        <MessageSquareWarning className="mx-auto mb-3 h-8 w-8 opacity-50" />
        <p className="font-medium">No lyrics reports</p>
        <p className="text-sm">
          Singers can report wrong words or out-of-sync lyrics from the Lyrics
          controls.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">
        The app tries a fix as soon as something is reported. Check the song,
        then close the report, fix the lyrics here, or undo the report if the
        lyrics were right.
      </p>
      {reports.map((report) => {
        const isExpanded = expandedReportId === report.id;
        return (
          <div key={report.id} className="rounded-lg border">
            <div className="flex flex-wrap items-start gap-3 p-4">
              <button
                type="button"
                className="min-w-0 flex-1 text-left"
                onClick={() =>
                  setExpandedReportId(isExpanded ? null : report.id)
                }
              >
                <p className="truncate font-medium">
                  {report.title ?? report.songId}
                </p>
                <p className="truncate text-sm text-muted-foreground">
                  {report.artist}
                </p>
                <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
                  <Badge variant="outline">{KIND_LABEL[report.kind]}</Badge>
                  <span className="text-muted-foreground">
                    {report.reportCount > 1
                      ? `${report.reportCount} reports, last by `
                      : "By "}
                    {report.reporterName ?? "someone"},{" "}
                    {describeWhen(report.lastReportedAt)}
                  </span>
                </div>
                <p className="mt-1 text-sm">
                  {report.outcome
                    ? OUTCOME_LABEL[report.outcome]
                    : "Fixing it now…"}
                  {report.lyricsSource && (
                    <span className="text-muted-foreground">
                      {" "}
                      · timings from {report.lyricsSource}
                    </span>
                  )}
                  {report.lyricsHandPicked && (
                    <span className="text-muted-foreground">
                      {" "}
                      · picked by a person
                    </span>
                  )}
                </p>
              </button>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={isBusy}
                  onClick={() => undo(report)}
                  title={
                    report.canRestore
                      ? "The lyrics were right: put them back and forget this report"
                      : "The lyrics were right: let them be used again"
                  }
                >
                  Report was wrong
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={isBusy}
                  onClick={() => resolve(report.id)}
                >
                  Looks right now
                </Button>
              </div>
            </div>
            {isExpanded && (
              <div className="border-t bg-muted/20 p-4">
                <SongActionPanel
                  song={
                    {
                      id: report.songId,
                      title: report.title ?? "",
                      artist: report.artist ?? "",
                    } as Song
                  }
                  issues={["missing_lyrics"]}
                  onDone={() => setExpandedReportId(null)}
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
