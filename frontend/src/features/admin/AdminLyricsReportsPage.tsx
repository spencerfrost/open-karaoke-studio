import React, { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { MessageSquareWarning } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  useLyricsReports,
  useResolveLyricsReport,
  useUndoLyricsReport,
  type LyricsReport,
  type LyricsReportKind,
  type LyricsReportOutcome,
} from "@/hooks/api/useLyricsReports";
import { parseLrc } from "@/utils/lrcParser";
import { formatTime } from "@/utils/formatters";
import {
  FilterChips,
  ReviewEmpty,
  ReviewLayout,
  type ReviewSelection,
} from "./review/ReviewLayout";
import { SongPanel } from "./review/SongPanel";
import { LyricsFixButtons } from "./review/SongActions";
import { useReviewSong } from "./review/useReviewSong";

const KIND_LABEL: Record<LyricsReportKind, string> = {
  words: "Wrong words",
  timing: "Out of sync",
};

const OUTCOME_LABEL: Record<LyricsReportOutcome, string> = {
  replaced: "Replaced with other lyrics",
  retimed: "Re-timed to the singing",
  transcribed: "Replaced with a transcript of the singing",
  unchanged: "Couldn't fix it",
};

type KindFilter = "all" | LyricsReportKind;

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

/** The lyrics as they are now: timed lines when there are some. */
const LyricsPreview: React.FC<{
  syncedLyrics?: string;
  plainLyrics?: string;
}> = ({ syncedLyrics, plainLyrics }) => {
  const timed = syncedLyrics
    ? parseLrc(syncedLyrics).filter((line) => !line.isBlank)
    : [];

  if (!timed.length && !plainLyrics) {
    return <p className="text-sm text-muted-foreground">No lyrics.</p>;
  }

  return (
    <div className="max-h-80 overflow-y-auto rounded-md border border-border/60 bg-muted/30 p-3 text-sm leading-relaxed">
      {timed.length ? (
        <ol className="space-y-0.5">
          {timed.map((line, index) => (
            <li key={index} className="flex gap-3">
              <span className="w-10 shrink-0 text-right font-mono text-xs leading-relaxed text-muted-foreground">
                {formatTime(line.timestamp / 1000)}
              </span>
              <span>{line.content}</span>
            </li>
          ))}
        </ol>
      ) : (
        <p className="whitespace-pre-line">{plainLyrics}</p>
      )}
    </div>
  );
};

const ReportDetail: React.FC<{
  report: LyricsReport;
  selection: ReviewSelection;
}> = ({ report, selection }) => {
  const queryClient = useQueryClient();
  const basics = {
    id: report.songId,
    title: report.title ?? report.songId,
    artist: report.artist ?? "",
  };
  const song = useReviewSong(basics);
  const resolveReport = useResolveLyricsReport();
  const undoReport = useUndoLyricsReport();
  const isBusy = resolveReport.isPending || undoReport.isPending;

  // Both hooks refresh the reports list themselves.
  const resolve = (message: string) =>
    resolveReport.mutate(report.id, {
      onSuccess: () => {
        toast.success(message);
        selection.done();
      },
      onError: (error) => toast.error(error.message),
    });

  const undo = () =>
    undoReport.mutate(report, {
      onSuccess: ({ restored }) => {
        toast.success(
          restored
            ? "Put the reported lyrics back"
            : "Report removed. Those lyrics can be used again",
        );
        selection.done();
      },
      onError: (error) => toast.error(error.message),
    });

  return (
    <SongPanel
      basics={basics}
      details={
        <div className="space-y-3">
          <div className="space-y-1 text-sm">
            <p>
              <Badge variant="outline" className="mr-2">
                {KIND_LABEL[report.kind]}
              </Badge>
              {report.reportCount > 1
                ? `${report.reportCount} reports, last by `
                : "By "}
              {report.reporterName ?? "someone"},{" "}
              {describeWhen(report.lastReportedAt)}
            </p>
            <p>
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
          </div>
          <LyricsPreview
            syncedLyrics={song.syncedLyrics}
            plainLyrics={song.plainLyrics}
          />
        </div>
      }
    >
      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          disabled={isBusy}
          onClick={() => resolve("Report closed")}
        >
          Looks right now
        </Button>
        <Button
          size="sm"
          variant="outline"
          disabled={isBusy}
          onClick={undo}
          title={
            report.canRestore
              ? "The lyrics were right: put them back and forget this report"
              : "The lyrics were right: let them be used again"
          }
        >
          Report was wrong
        </Button>
        {/* New lyrics picked here are the fix, so the report closes too. */}
        <LyricsFixButtons
          song={song}
          onSaved={() => {
            queryClient.invalidateQueries({ queryKey: ["songs"] });
            resolve("Lyrics saved and report closed");
          }}
        />
      </div>
    </SongPanel>
  );
};

/**
 * Lyrics reports from people singing: what they said, and what the app did
 * about it. Each stays listed until someone checks the song.
 */
const AdminLyricsReportsPage: React.FC = () => {
  const { data: reports, isLoading, error } = useLyricsReports();
  const [kind, setKind] = useState<KindFilter>("all");

  const shown =
    kind === "all" ? reports : reports?.filter((r) => r.kind === kind);
  const countOf = (k: LyricsReportKind) =>
    reports?.filter((r) => r.kind === k).length;

  return (
    <ReviewLayout
      label="Lyrics reports"
      items={shown}
      getId={(report) => String(report.id)}
      isLoading={isLoading}
      error={error}
      toolbar={
        <p className="text-sm text-muted-foreground">
          The app tries a fix as soon as something is reported. Listen to the
          song, then close the report, fix the lyrics here, or undo the report
          if the lyrics were right.
        </p>
      }
      filters={
        !!reports?.length && (
          <FilterChips
            label="Show reports"
            value={kind}
            onChange={(value) => setKind(value as KindFilter)}
            chips={[
              { value: "all", label: "All", count: reports.length },
              { value: "words", label: "Wrong words", count: countOf("words") },
              {
                value: "timing",
                label: "Out of sync",
                count: countOf("timing"),
              },
            ]}
          />
        )
      }
      empty={
        <ReviewEmpty icon={MessageSquareWarning} title="No lyrics reports">
          Singers can report wrong words or out-of-sync lyrics from the Lyrics
          controls.
        </ReviewEmpty>
      }
      renderRow={(report) => (
        <>
          <p className="truncate text-sm font-medium">
            {report.title ?? report.songId}
          </p>
          <p className="truncate text-xs text-muted-foreground">
            {report.artist}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            {KIND_LABEL[report.kind]}
            {report.reportCount > 1 && ` · ${report.reportCount} reports`}
            {!report.outcome && " · fixing…"}
          </p>
        </>
      )}
      renderDetail={(report, selection) => (
        <ReportDetail report={report} selection={selection} />
      )}
    />
  );
};

export default AdminLyricsReportsPage;
