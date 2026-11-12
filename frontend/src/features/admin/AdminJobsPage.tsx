import React from "react";
import { toast } from "sonner";
import { Loader2, Pause, Play, Square } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  useBatchJobs,
  useCancelRun,
  usePauseRun,
  useRecentRuns,
  useResumeRun,
  useRunJob,
  type BatchJob,
  type BatchRun,
  type RepairReason,
  type RunMode,
  type RunStatus,
} from "./hooks/useBatchJobs";
import ArtistCreditsReportDialog from "./ArtistCreditsReportDialog";
import { JOB_INFO, countOf, type JobInfo } from "./jobInfo";
import WorkerStrip from "./WorkerStrip";

const MODE_LABEL: Record<RunMode, string> = {
  missing: "missing",
  repair: "needing repair",
  retime: "with lyrics, keeping their lyrics",
  retry: "not yet matched",
  all: "all",
  preview: "preview",
  apply: "apply",
};

const REPAIR_REASON_LABEL: Record<RepairReason, string> = {
  no_word_timing: "Synced lyrics, no word timing",
  plain_only: "Plain lyrics only",
  plain_timing: "Timed against plain lyrics",
  words_mismatch: "Word timing doesn't match the lyrics",
  reported: "Reported by a singer",
};

const STATUS_LABEL: Record<RunStatus, string> = {
  queued: "Waiting",
  running: "Running",
  interrupted: "Interrupted",
  pausing: "Pausing",
  paused: "Paused",
  done: "Finished",
  failed: "Failed",
  cancelled: "Stopped",
};

// Red text is hard to read on the page background, so a failure is a solid
// pill instead.
const STATUS_CLASS: Record<RunStatus, string> = {
  queued: "text-foreground-dim",
  running: "text-primary",
  interrupted: "text-foreground-dim",
  pausing: "text-foreground-dim",
  paused: "text-foreground-dim",
  done: "text-foreground",
  failed: "rounded bg-destructive px-1.5 py-0.5 text-destructive-foreground",
  cancelled: "text-foreground-dim",
};

function formatWhen(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

/** "Oct 2, 9:14 PM · 1,500 songs · 3 failed" */
function describeRun(run: BatchRun, unit: JobInfo["unit"]): string {
  const parts = [formatWhen(run.finishedAt ?? run.createdAt)];
  if (run.mode === "all") parts.push("re-ran all");
  if (run.mode === "repair") parts.push("ones needing repair");
  if (run.mode === "retime") parts.push("re-timed all, lyrics kept");
  if (run.mode === "retry") parts.push("retried ones not yet matched");
  if (run.mode === "preview") parts.push("preview");
  if (run.mode === "apply") parts.push("applied");
  if (run.total !== null) parts.push(countOf(run.total, unit));
  if (run.failed > 0) parts.push(`${run.failed.toLocaleString()} failed`);
  return parts.join(" · ");
}

const RunButton: React.FC<{
  job: BatchJob;
  mode: RunMode;
  info: JobInfo;
}> = ({ job, mode, info }) => {
  const runJob = useRunJob();
  const count = job.modeCounts[mode] ?? 0;
  const label =
    mode === "all"
      ? "Re-run all"
      : mode === "retime"
        ? "Re-time all, keep lyrics"
        : mode === "preview"
          ? "Preview"
          : mode === "apply"
            ? job.kind === "lrc_offset"
              ? `Apply ${countOf(count, ["shift", "shifts"])}`
              : "Apply"
            : `Run on ${count.toLocaleString()} ${MODE_LABEL[mode]}`;

  const start = () =>
    runJob.mutate(
      { kind: job.kind, mode },
      {
        onSuccess: () => toast.success(`${info.name}: queued`),
        onError: (error) => toast.error(error.message),
      },
    );

  const disabled = runJob.isPending || job.activeRun !== null || count === 0;

  if (mode === "missing" && count === 0) {
    return (
      <span className="self-center text-sm text-foreground-dim">
        Up to date
      </span>
    );
  }

  // Applying rewrites part of the library, so it asks first.
  if (mode === "apply") {
    return (
      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button size="sm" variant="outline" disabled={disabled}>
            {label}
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Apply {info.name.toLowerCase()}?
            </AlertDialogTitle>
            <AlertDialogDescription>
              {job.kind === "lrc_offset"
                ? `This shifts the lyrics of ${countOf(count, info.unit)} by the offset the sweep found and re-times their words, so the TV shows the change. Listen to them on Compare word timing first. Take a database backup (pg_dump) first: it can't be undone from here.`
                : `This re-credits ${countOf(count, info.unit)}, merges duplicate artists and deletes unused ones, as the last preview's report describes. Take a database backup (pg_dump) first: it can't be undone from here.`}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={start}>Apply</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    );
  }

  // A full re-run can take hours (vocal range is ~8 hours for 1,500 songs),
  // so it asks first.
  if (mode === "all") {
    return (
      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button size="sm" variant="outline" disabled={disabled}>
            {label}
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Re-run {info.name.toLowerCase()} on every {info.unit[0]}?
            </AlertDialogTitle>
            <AlertDialogDescription>
              That's {countOf(count, info.unit)}, including ones already done.
              It runs in the background and you can stop it from this page.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={start}>Re-run all</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    );
  }

  return (
    <Button
      size="sm"
      variant={mode === "missing" || mode === "preview" ? "default" : "outline"}
      disabled={disabled}
      onClick={start}
    >
      {label}
    </Button>
  );
};

const ActiveRun: React.FC<{ run: BatchRun; info: JobInfo }> = ({
  run,
  info,
}) => {
  const cancelRun = useCancelRun();
  const pauseRun = usePauseRun();
  const resumeRun = useResumeRun();
  const handled = run.done + run.failed;
  const paused = run.status === "paused" || run.status === "pausing";
  const percent =
    run.total && run.total > 0 ? (handled / run.total) * 100 : undefined;

  const stop = () =>
    cancelRun.mutate(run.id, {
      onSuccess: () => toast.success(`${info.name}: stopping`),
      onError: (error) => toast.error(error.message),
    });

  const togglePause = () =>
    (paused ? resumeRun : pauseRun).mutate(run.id, {
      onSuccess: () =>
        toast.success(`${info.name}: ${paused ? "resuming" : "pausing"}`),
      onError: (error) => toast.error(error.message),
    });

  return (
    <div className="flex items-center gap-3">
      {run.status === "interrupted" || paused ? (
        <Pause className="h-4 w-4 shrink-0 text-foreground-dim" />
      ) : (
        <Loader2 className="h-4 w-4 shrink-0 animate-spin text-primary" />
      )}
      <div className="min-w-0 flex-1 space-y-1">
        <Progress value={percent ?? 0} className="h-1.5" />
        <p className="text-xs text-foreground-dim">
          {run.status === "queued"
            ? "Waiting for the worker…"
            : run.status === "interrupted"
              ? `Stopped with the worker at ${handled.toLocaleString()} of ${countOf(run.total ?? 0, info.unit)} · carries on when the worker starts`
              : run.status === "pausing"
                ? `Pausing after this song · ${handled.toLocaleString()} of ${countOf(run.total ?? 0, info.unit)} done`
                : run.status === "paused"
                  ? `Paused at ${handled.toLocaleString()} of ${countOf(run.total ?? 0, info.unit)} · GPU free until you resume`
                  : run.total === null
                    ? "Starting…"
                    : run.waiting !== null
                      ? `${handled.toLocaleString()} of ${countOf(run.total, info.unit)} done · ${run.waiting.toLocaleString()} waiting their turn`
                      : `${handled.toLocaleString()} of ${countOf(run.total, info.unit)}`}
          {run.failed > 0 && ` · ${run.failed.toLocaleString()} failed`}
        </p>
      </div>
      <Button
        size="sm"
        variant="ghost"
        onClick={togglePause}
        disabled={pauseRun.isPending || resumeRun.isPending}
      >
        {paused ? (
          <Play className="mr-1.5 h-3 w-3" />
        ) : (
          <Pause className="mr-1.5 h-3 w-3" />
        )}
        {paused ? "Resume" : "Pause"}
      </Button>
      <Button
        size="sm"
        variant="ghost"
        onClick={stop}
        disabled={cancelRun.isPending}
      >
        <Square className="mr-1.5 h-3 w-3" />
        Stop
      </Button>
    </div>
  );
};

const JobRow: React.FC<{
  job: BatchJob;
  onOpenReport: (runId: number) => void;
}> = ({ job, onOpenReport }) => {
  const info = JOB_INFO[job.kind];
  const { have, of } = job.coverage;
  const coveragePercent = of > 0 ? (have / of) * 100 : 100;

  return (
    <div className="grid gap-4 p-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1.2fr)_minmax(0,1.6fr)] lg:items-center">
      <div className="min-w-0 space-y-1">
        <p className="font-semibold">{info.name}</p>
        <p className="text-sm text-foreground-dim">{info.description}</p>
        {job.repairReasons && (job.modeCounts.repair ?? 0) > 0 && (
          <details className="text-xs text-foreground-dim">
            <summary className="cursor-pointer">
              Why {countOf(job.modeCounts.repair ?? 0, info.unit)} need repair
            </summary>
            <ul className="mt-1 space-y-0.5 pl-3">
              {(Object.keys(REPAIR_REASON_LABEL) as RepairReason[])
                .filter((reason) => (job.repairReasons?.[reason] ?? 0) > 0)
                .map((reason) => (
                  <li key={reason} className="flex justify-between gap-4">
                    <span>{REPAIR_REASON_LABEL[reason]}</span>
                    <span className="tabular-nums">
                      {job.repairReasons?.[reason]}
                    </span>
                  </li>
                ))}
            </ul>
            <p className="mt-1">A song can have more than one reason.</p>
          </details>
        )}
      </div>

      <div className="space-y-1">
        <Progress value={coveragePercent} className="h-1.5" />
        <p className="text-xs tabular-nums text-foreground-dim">
          {have.toLocaleString()} of {countOf(of, info.unit)}
        </p>
      </div>

      <div className="space-y-2">
        {job.activeRun ? (
          <ActiveRun run={job.activeRun} info={info} />
        ) : (
          <div className="flex flex-wrap gap-2 lg:justify-end">
            {job.modes.map((mode) => (
              <RunButton key={mode} job={job} mode={mode} info={info} />
            ))}
          </div>
        )}
        {job.lastRun && (
          <p className="text-xs text-foreground-dim lg:text-right">
            Last run{" "}
            <span className={STATUS_CLASS[job.lastRun.status]}>
              {STATUS_LABEL[job.lastRun.status].toLowerCase()}
            </span>{" "}
            {describeRun(job.lastRun, info.unit)}
            {job.lastRun.hasReport && (
              <>
                {" · "}
                <Button
                  variant="link"
                  size="sm"
                  className="h-auto p-0 text-xs"
                  onClick={() => onOpenReport(job.lastRun!.id)}
                >
                  View report
                </Button>
              </>
            )}
          </p>
        )}
        {job.lastRun?.error && (
          <p className="text-xs text-foreground lg:text-right">
            {job.lastRun.error}
          </p>
        )}
      </div>
    </div>
  );
};

const RecentRuns: React.FC<{ onOpenReport: (runId: number) => void }> = ({
  onOpenReport,
}) => {
  const { data } = useRecentRuns();
  const runs = data?.runs ?? [];
  if (runs.length === 0) return null;

  return (
    <section className="space-y-2">
      <h2 className="text-lg font-semibold">Recent runs</h2>
      <div className="divide-y divide-border/30 rounded-lg border border-border/40 text-sm">
        {runs.map((run) => {
          const info = JOB_INFO[run.kind];
          return (
            <div
              key={run.id}
              className="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-2"
            >
              <span className="w-44 font-medium">{info?.name ?? run.kind}</span>
              <span className={cn("w-20", STATUS_CLASS[run.status])}>
                {STATUS_LABEL[run.status]}
              </span>
              <span className="text-foreground-dim">
                {describeRun(run, info?.unit ?? ["song", "songs"])}
              </span>
              {run.hasReport && (
                <Button
                  variant="link"
                  size="sm"
                  className="h-auto p-0"
                  onClick={() => onOpenReport(run.id)}
                >
                  View report
                </Button>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
};

/** Every library-wide batch job in one place, with its coverage and runs. */
const AdminJobsPage: React.FC = () => {
  const { data, isLoading, error } = useBatchJobs();
  const [reportRunId, setReportRunId] = React.useState<number | null>(null);

  return (
    <div className="max-w-6xl space-y-6">
      <div className="space-y-3">
        <p className="text-sm text-foreground-dim">
          Jobs that work through the whole library. They run in the background,
          one song at a time, so the night can carry on while they do.
        </p>
        <WorkerStrip />
      </div>

      {isLoading && <p className="text-sm text-foreground-dim">Loading…</p>}
      {error && !data && (
        <p className="w-fit rounded bg-destructive px-3 py-1 text-sm text-destructive-foreground">
          Couldn't load jobs: {error.message}
        </p>
      )}
      {data && (
        <div className="divide-y divide-border/30 rounded-lg border border-border/40">
          {data.jobs.map((job) => (
            <JobRow key={job.kind} job={job} onOpenReport={setReportRunId} />
          ))}
        </div>
      )}

      <RecentRuns onOpenReport={setReportRunId} />

      <ArtistCreditsReportDialog
        runId={reportRunId}
        onOpenChange={(open) => !open && setReportRunId(null)}
      />
    </div>
  );
};

export default AdminJobsPage;
