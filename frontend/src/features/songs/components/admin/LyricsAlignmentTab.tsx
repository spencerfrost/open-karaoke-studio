import React, { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuthStore } from "@/stores/authStore";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { createLogger } from "@/lib/logger";
import { toast } from "sonner";
import { CheckCircle2, Clock, Mic2, RefreshCw, Loader2 } from "lucide-react";

const logger = createLogger("component:LyricsAlignmentTab");

type RepairReason =
  | "no_word_timing"
  | "plain_only"
  | "plain_timing"
  | "words_mismatch"
  | "reported";

const REPAIR_REASON_LABEL: Record<RepairReason, string> = {
  no_word_timing: "Synced lyrics, no word timing",
  plain_only: "Plain lyrics only",
  plain_timing: "Timed against plain lyrics",
  words_mismatch: "Word timing doesn't match the lyrics",
  reported: "Reported by a singer",
};

interface AlignmentStatus {
  total: number;
  withVocals: number;
  aligned: number;
  needsAlignment: number;
  noLyrics: number;
  repair: number;
  repairReasons: Record<RepairReason, number>;
}

interface SongResult {
  songId: string;
  title: string;
  status: "queued" | "already_running";
  reasons: RepairReason[];
}

interface BatchResult {
  mode: RunMode;
  selected: number;
  queued: number;
  alreadyRunning: number;
  skipped: number;
  reasons: Record<RepairReason, number>;
  results: SongResult[];
}

type RunMode = "missing" | "repair" | "all";

const MODE_LABEL: Record<RunMode, string> = {
  missing: "Missing only",
  repair: "Needs repair",
  all: "Re-run all",
};

const MODE_DESCRIPTION: Record<RunMode, string> = {
  missing:
    "Songs without word-level lyrics, including songs with no lyrics yet.",
  repair:
    "Songs whose lyrics or word timing look wrong, or that a singer reported.",
  all: "Every song with vocals, including already-aligned ones.",
};

type TaskState = "idle" | "dispatched" | "running" | "done" | "error";

export const LyricsAlignmentTab: React.FC = () => {
  const { token } = useAuthStore();
  const [batchResult, setBatchResult] = useState<BatchResult | null>(null);
  const [mode, setMode] = useState<RunMode>("missing");
  const [taskId, setTaskId] = useState<string | null>(null);
  const [taskState, setTaskState] = useState<TaskState>("idle");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  useEffect(() => () => stopPolling(), []);

  const statusQuery = useQuery<AlignmentStatus>({
    queryKey: ["admin-alignment-status"],
    queryFn: async () => {
      const res = await fetch("/api/lyrics/batch/align", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to load alignment status");
      return res.json();
    },
    enabled: !!token,
  });

  const pollTaskStatus = (id: string) => {
    setTaskState("running");
    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`/api/lyrics/batch/align/status/${id}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error("Status check failed");
        const data = await res.json();

        if (data.state === "SUCCESS") {
          stopPolling();
          setTaskState("done");
          setBatchResult(data.result);
          statusQuery.refetch();
          logger.info("Batch alignment queued", data.result);
          if (data.result.queued > 0) {
            toast.success(
              `Queued ${data.result.queued} song${data.result.queued !== 1 ? "s" : ""} for lyrics alignment`,
            );
          } else if (data.result.selected === 0) {
            toast.info("No songs needed alignment");
          } else {
            toast.info("Every selected song is already aligning");
          }
        } else if (data.state === "FAILURE") {
          stopPolling();
          setTaskState("error");
          toast.error(`Alignment task failed: ${data.error}`);
        }
        // PENDING / STARTED: keep polling
      } catch (e) {
        logger.warn("Poll error", e);
      }
    }, 3000);
  };

  const handleRun = async () => {
    try {
      setTaskState("dispatched");
      setBatchResult(null);
      const res = await fetch(`/api/lyrics/batch/align?mode=${mode}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to dispatch alignment task");
      const data = await res.json();
      setTaskId(data.taskId);
      logger.info("Batch alignment dispatched", data);
      pollTaskStatus(data.taskId);
    } catch (e: unknown) {
      setTaskState("error");
      toast.error(e instanceof Error ? e.message : "Failed to start alignment");
    }
  };

  const isRunning = taskState === "dispatched" || taskState === "running";
  const status = statusQuery.data;
  const modeCount: Record<RunMode, number | undefined> = {
    missing: status && status.withVocals - status.aligned,
    repair: status?.repair,
    all: status?.withVocals,
  };
  const runCount = modeCount[mode];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Lyrics Alignment</h2>
          <p className="text-sm text-muted-foreground">
            Re-run lyrics alignment for many songs at once. Each song is queued
            as its own job, the same way a newly added song is aligned.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => statusQuery.refetch()}
            disabled={statusQuery.isFetching}
          >
            <RefreshCw
              className={`h-3.5 w-3.5 ${statusQuery.isFetching ? "animate-spin" : ""}`}
            />
          </Button>
        </div>
      </div>

      {/* Stats */}
      {status && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          <StatCard label="Total songs" value={status.total} />
          <StatCard label="With vocals" value={status.withVocals} />
          <StatCard
            label="Word-aligned"
            value={status.aligned}
            className="text-success-strong"
          />
          <StatCard
            label="Needs alignment"
            value={status.needsAlignment}
            className={
              status.needsAlignment > 0 ? "text-warning-strong" : undefined
            }
          />
          <StatCard
            label="Needs repair"
            value={status.repair}
            className={status.repair > 0 ? "text-warning-strong" : undefined}
          />
        </div>
      )}

      {status && status.repair > 0 && (
        <div className="rounded-lg border bg-muted/30 px-4 py-3 text-sm">
          <p className="mb-2 font-medium">Why songs need repair</p>
          <ul className="space-y-1 text-muted-foreground">
            {(Object.keys(REPAIR_REASON_LABEL) as RepairReason[])
              .filter((reason) => status.repairReasons[reason] > 0)
              .map((reason) => (
                <li key={reason} className="flex justify-between gap-4">
                  <span>{REPAIR_REASON_LABEL[reason]}</span>
                  <span className="tabular-nums">
                    {status.repairReasons[reason]}
                  </span>
                </li>
              ))}
          </ul>
          <p className="mt-2 text-xs text-muted-foreground">
            A song can be listed under more than one reason.
          </p>
        </div>
      )}

      <Separator />

      {/* Run controls */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <p className="text-sm font-medium">Run batch alignment</p>
          <p className="text-xs text-muted-foreground">
            {MODE_DESCRIPTION[mode]}
          </p>
        </div>
        <div className="flex gap-2 shrink-0">
          {(Object.keys(MODE_LABEL) as RunMode[]).map((m) => (
            <Button
              key={m}
              variant={mode === m ? "default" : "outline"}
              size="sm"
              onClick={() => setMode(m)}
            >
              {MODE_LABEL[m]}
            </Button>
          ))}
        </div>
      </div>

      <Button
        onClick={handleRun}
        disabled={isRunning || runCount === 0}
        className="w-full sm:w-auto"
      >
        {isRunning ? (
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        ) : (
          <Mic2 className="mr-2 h-4 w-4" />
        )}
        {taskState === "dispatched"
          ? "Dispatching…"
          : taskState === "running"
            ? "Queueing songs…"
            : `Align ${runCount ?? "…"} song${runCount !== 1 ? "s" : ""}`}
      </Button>

      {/* In-flight indicator */}
      {isRunning && taskId && (
        <div className="flex items-center gap-2 rounded-lg border bg-muted/30 px-4 py-3 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin shrink-0" />
          <span>
            Running in background… task{" "}
            <code className="font-mono text-xs">{taskId.slice(0, 8)}</code> —
            this page will update automatically.
          </span>
        </div>
      )}

      {/* Results */}
      {batchResult && (
        <div className="space-y-3">
          <Separator />
          <div className="flex flex-wrap gap-3 rounded-lg border bg-muted/30 p-4 text-sm text-muted-foreground">
            <span className="font-medium text-success-strong">
              {batchResult.queued} queued
            </span>
            {batchResult.alreadyRunning > 0 && (
              <>
                <span>·</span>
                <span>{batchResult.alreadyRunning} already aligning</span>
              </>
            )}
            {batchResult.skipped > 0 && (
              <>
                <span>·</span>
                <span>{batchResult.skipped} skipped</span>
              </>
            )}
          </div>
          {batchResult.queued > 0 && (
            <p className="text-xs text-muted-foreground">
              Songs align one after another in the background, up to a minute or
              more each. Refresh the counts above to see progress.
            </p>
          )}

          {batchResult.results.length > 0 && (
            <div className="divide-y rounded-lg border max-h-96 overflow-y-auto">
              {batchResult.results.map((r) => (
                <div
                  key={r.songId}
                  className="flex items-center gap-3 px-4 py-2.5"
                >
                  {r.status === "queued" ? (
                    <CheckCircle2 className="h-4 w-4 text-success-strong shrink-0" />
                  ) : (
                    <Clock className="h-4 w-4 text-muted-foreground shrink-0" />
                  )}
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium truncate">{r.title}</p>
                    {r.reasons.length > 0 && (
                      <p className="text-xs text-muted-foreground truncate">
                        {r.reasons
                          .map((reason) => REPAIR_REASON_LABEL[reason])
                          .join(" · ")}
                      </p>
                    )}
                  </div>
                  <Badge variant="outline" className="text-xs shrink-0">
                    {r.status === "queued" ? "Queued" : "Already aligning"}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

interface StatCardProps {
  label: string;
  value: number;
  className?: string;
}

const StatCard: React.FC<StatCardProps> = ({ label, value, className }) => (
  <Card className="block rounded-lg p-3 text-center shadow-none">
    <p className={`text-2xl font-bold ${className ?? ""}`}>{value}</p>
    <p className="text-xs text-muted-foreground mt-0.5">{label}</p>
  </Card>
);
