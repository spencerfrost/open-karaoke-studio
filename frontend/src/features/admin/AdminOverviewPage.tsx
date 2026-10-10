import React from "react";
import { Link } from "react-router-dom";
import { Loader2, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { useProcessingIndicators } from "@/stores/processingIndicatorsStore";
import {
  useAdminOverview,
  type AdminOverview,
  type ScanKind,
  type ScanRun,
} from "./hooks/useAdminQueries";
import { JOB_INFO, countOf } from "./jobInfo";
import WorkerStrip from "./WorkerStrip";

const CARD = "rounded-lg border border-border/40 p-5";

function plural(n: number, singular: string, pluralForm = `${singular}s`) {
  return `${n.toLocaleString()} ${n === 1 ? singular : pluralForm}`;
}

function formatDay(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

const CardHead: React.FC<{ title: string; note?: string }> = ({
  title,
  note,
}) => (
  <div className="mb-4 flex flex-wrap items-baseline justify-between gap-x-3">
    <h2 className="font-semibold">{title}</h2>
    {note && <span className="text-xs text-foreground-dim">{note}</span>}
  </div>
);

// --- What needs you ---

interface Tile {
  to: string;
  count: number;
  label: string;
  why: string;
  /** Failed songs can't be sung at all, so they're worse than the rest. */
  urgent?: boolean;
}

function tilesFor({ needsYou }: AdminOverview): Tile[] {
  const { suggested, ambiguous, noMatch, failed } = needsYou.acoustid;
  return [
    {
      to: "lyrics-reports",
      count: needsYou.lyricsReports,
      label: "Lyrics reports",
      why: "Singers flagged wrong or out-of-sync lyrics",
    },
    {
      to: "acoustid",
      count: suggested + ambiguous + noMatch + failed,
      label: "AcoustID matches",
      why: `${suggested} different name · ${ambiguous} unsure · ${noMatch} no match · ${failed} failed`,
    },
    {
      to: "failed",
      count: needsYou.failedSongs,
      label: "Failed songs",
      why: "Hidden from guests until they're fixed",
      urgent: true,
    },
    {
      to: "jobs",
      count: needsYou.alignmentRepair,
      label: "Lyrics need repair",
      why: "Word timing is missing or looks wrong",
    },
  ];
}

const NeedsYou: React.FC<{ overview: AdminOverview }> = ({ overview }) => (
  <section
    aria-label="Needs you"
    className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
  >
    {tilesFor(overview).map((tile) => {
      const clear = tile.count === 0;
      return (
        <Link
          key={tile.to}
          to={tile.to}
          className={cn(
            "flex flex-col gap-1 rounded-lg border border-border/40 border-l-4 p-4 transition-colors hover:border-primary",
            clear
              ? "border-l-success"
              : tile.urgent
                ? "border-l-destructive"
                : "border-l-warning",
          )}
        >
          <span className="font-display text-4xl tabular-nums">
            {tile.count.toLocaleString()}
          </span>
          <span className="font-semibold">{tile.label}</span>
          <span className="text-sm text-foreground-dim">
            {clear ? "Nothing to do" : tile.why}
          </span>
          {!clear && (
            <span className="mt-1 text-sm font-semibold text-primary">
              Review →
            </span>
          )}
        </Link>
      );
    })}
  </section>
);

// --- Running now ---

const ProgressRow: React.FC<{
  name: string;
  detail: string;
  percent: number | undefined;
}> = ({ name, detail, percent }) => (
  <div className="space-y-1.5 py-2.5">
    <div className="flex flex-wrap items-baseline justify-between gap-x-3">
      <span className="min-w-0 truncate font-medium">{name}</span>
      <span className="text-xs tabular-nums text-foreground-dim">{detail}</span>
    </div>
    <Progress value={percent ?? 0} className="h-1.5" />
  </div>
);

const RunningNow: React.FC<{ overview: AdminOverview }> = ({ overview }) => {
  const processing = useProcessingIndicators((state) => state.processingSongs);
  // Alignment queues a job per song; its batch run below stands for them.
  const separating = [...processing.values()].filter(
    (job) =>
      job.engineType !== "lyrics_alignment" &&
      (job.status === "queued" || job.status === "processing"),
  );
  const runs = overview.jobs.flatMap((job) =>
    job.activeRun ? [job.activeRun] : [],
  );

  return (
    <section className={CARD}>
      <CardHead title="Running now" />
      {separating.length === 0 && runs.length === 0 ? (
        <p className="text-sm text-foreground-dim">
          Nothing is running. Songs show up here while they're separated.
        </p>
      ) : (
        <div className="divide-y divide-border/30">
          {separating.map((job) => (
            <ProgressRow
              key={job.id}
              name={
                job.title
                  ? `Separating “${job.title}”${job.artist ? ` · ${job.artist}` : ""}`
                  : "Separating a song"
              }
              detail={job.status === "queued" ? "Waiting" : `${job.progress}%`}
              percent={job.progress}
            />
          ))}
          {runs.map((run) => {
            const info = JOB_INFO[run.kind];
            const handled = run.done + run.failed;
            return (
              <ProgressRow
                key={run.id}
                name={info.name}
                detail={
                  run.status === "queued"
                    ? "Waiting for the worker"
                    : run.total === null
                      ? "Starting"
                      : `${handled.toLocaleString()} of ${countOf(run.total, info.unit)}`
                }
                percent={run.total ? (handled / run.total) * 100 : undefined}
              />
            );
          })}
        </div>
      )}
      <div className="mt-4 border-t border-border/30 pt-4">
        <WorkerStrip />
      </div>
    </section>
  );
};

// --- Songs added ---

const SONG_STATUS: Record<string, { label: string; className: string }> = {
  processed: { label: "Ready", className: "text-foreground-dim" },
  error: {
    label: "Failed",
    className: "rounded bg-destructive px-1.5 text-destructive-foreground",
  },
};
const IN_PROGRESS = { label: "Processing", className: "text-primary" };

const SongsAdded: React.FC<{ overview: AdminOverview }> = ({ overview }) => {
  const { weeks, recent } = overview.songsAdded;
  const total = weeks.reduce((sum, week) => sum + week.count, 0);
  const max = Math.max(1, ...weeks.map((week) => week.count));
  const thisWeek = weeks[weeks.length - 1]?.count ?? 0;

  return (
    <section className={CARD}>
      <CardHead
        title="Songs added"
        note={`Last 12 weeks · ${total.toLocaleString()} total`}
      />
      <div
        role="img"
        aria-label={`Songs added per week over the last 12 weeks, ${thisWeek} this week`}
        className="flex h-14 items-end gap-1"
      >
        {weeks.map((week, i) => (
          <div
            key={week.start}
            title={`Week of ${formatDay(`${week.start}T00:00`)}: ${plural(week.count, "song")}`}
            className={cn(
              "flex-1 rounded-t-sm",
              i === weeks.length - 1 ? "bg-primary" : "bg-primary/30",
            )}
            // A sliver for empty weeks, so the 12 slots still read as a row.
            style={{ height: `${Math.max(4, (week.count / max) * 100)}%` }}
          />
        ))}
      </div>
      {recent.length > 0 && (
        <ul className="mt-4 divide-y divide-border/30">
          {recent.map((song) => {
            const status = SONG_STATUS[song.status] ?? IN_PROGRESS;
            return (
              <li
                key={song.id}
                className="flex items-center justify-between gap-3 py-2"
              >
                <div className="min-w-0">
                  <p className="truncate font-medium">{song.title}</p>
                  <p className="truncate text-xs text-foreground-dim">
                    {song.artist} · {formatDay(song.dateAdded)}
                  </p>
                </div>
                <span className={cn("shrink-0 text-xs", status.className)}>
                  {status.label}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
};

// --- Library coverage ---

const LibraryCoverage: React.FC<{ overview: AdminOverview }> = ({
  overview,
}) => (
  <section className={CARD}>
    <CardHead
      title="Library coverage"
      note="How much of the library each job has filled in"
    />
    <div className="grid grid-cols-[minmax(0,9rem)_minmax(0,1fr)_3rem_4rem] items-center gap-x-3 gap-y-2.5 text-sm">
      {overview.jobs.map(({ kind, coverage }) => {
        const percent =
          coverage.of > 0
            ? Math.floor((coverage.have / coverage.of) * 100)
            : 100;
        const complete = coverage.have >= coverage.of;
        return (
          <React.Fragment key={kind}>
            <span className="truncate">{JOB_INFO[kind].name}</span>
            <Progress value={percent} className="h-2" />
            <span className="text-right font-semibold tabular-nums">
              {percent}%
            </span>
            {complete ? (
              <span />
            ) : (
              <Link
                to="jobs"
                className="text-right font-semibold text-primary hover:underline"
              >
                Fill in
              </Link>
            )}
          </React.Fragment>
        );
      })}
    </div>
  </section>
);

// --- Hand-run scans ---

const SCANS: {
  kind: ScanKind;
  name: string;
  to: string;
  found: (n: number) => string;
}[] = [
  {
    kind: "disk_check",
    name: "Disk check",
    to: "disk",
    found: (n) => (n === 0 ? "no problems" : plural(n, "problem")),
  },
  {
    kind: "duplicates",
    name: "Duplicates",
    to: "duplicates",
    found: (n) =>
      n === 0 ? "no duplicates" : `${plural(n, "song")} with copies`,
  },
  {
    kind: "metadata_scan",
    name: "Metadata scan",
    to: "metadata",
    found: (n) => `${plural(n, "song")} flagged`,
  },
];

function describeScan(run: ScanRun | null, found: (n: number) => string) {
  if (!run) return "Never run";
  const when = formatDay(run.finishedAt ?? run.createdAt);
  return run.issues === null
    ? `Last run ${when}`
    : `Last run ${when} · ${found(run.issues)}`;
}

const HandRunScans: React.FC<{ overview: AdminOverview }> = ({ overview }) => (
  <section className={CARD}>
    <CardHead
      title="Checks you run by hand"
      note="Slow scans, so they only run when you ask"
    />
    <ul className="divide-y divide-border/30">
      {SCANS.map((scan) => (
        <li
          key={scan.kind}
          className="flex items-center justify-between gap-3 py-2.5 first:pt-0"
        >
          <div className="min-w-0">
            <p className="font-medium">{scan.name}</p>
            <p className="text-xs text-foreground-dim">
              {describeScan(overview.scans[scan.kind], scan.found)}
            </p>
          </div>
          <Button asChild size="sm" variant="outline">
            <Link to={scan.to}>Open</Link>
          </Button>
        </li>
      ))}
    </ul>
  </section>
);

/** /admin: what needs someone, what's running, and how the library is doing. */
const AdminOverviewPage: React.FC = () => {
  const { data, error, isFetching, refetch } = useAdminOverview();
  const today = new Date().toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
  });

  return (
    <div className="max-w-7xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-foreground-dim">
          {today}
          {data && ` · ${plural(data.librarySize, "song")} in the library`}
        </p>
        <Button
          size="sm"
          variant="outline"
          onClick={() => refetch()}
          disabled={isFetching}
        >
          <RefreshCw
            className={cn("mr-1.5 h-3.5 w-3.5", isFetching && "animate-spin")}
          />
          Refresh
        </Button>
      </div>

      {!data && !error && (
        <p className="flex items-center gap-2 text-sm text-foreground-dim">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading…
        </p>
      )}
      {error && !data && (
        <p className="w-fit rounded bg-destructive px-3 py-1 text-sm text-destructive-foreground">
          Couldn't load the overview: {error.message}
        </p>
      )}

      {data && (
        <>
          <NeedsYou overview={data} />
          <div className="grid gap-5 xl:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
            <RunningNow overview={data} />
            <SongsAdded overview={data} />
          </div>
          <div className="grid gap-5 xl:grid-cols-2">
            <LibraryCoverage overview={data} />
            <HandRunScans overview={data} />
          </div>
        </>
      )}
    </div>
  );
};

export default AdminOverviewPage;
