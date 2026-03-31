import React, { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuthStore } from "@/stores/authStore";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { createLogger } from "@/lib/logger";
import { toast } from "sonner";
import { CheckCircle2, AlertTriangle, XCircle, Mic2, RefreshCw, Loader2 } from "lucide-react";

const logger = createLogger("component:LyricsAlignmentTab");

interface AlignmentStatus {
  total: number;
  withVocals: number;
  aligned: number;
  needsAlignment: number;
  noLyrics: number;
}

interface SongResult {
  songId: string;
  title: string;
  status: "activated" | "low_confidence" | "failed";
  meanScore?: number;
  wordCount?: number;
  sourceType?: "synced" | "plain";
  reason?: string;
}

interface BatchResult {
  processed: number;
  activated: number;
  failed: number;
  skipped: number;
  results: SongResult[];
}

const STATUS_ICON: Record<SongResult["status"], React.ReactNode> = {
  activated: <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />,
  low_confidence: <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0" />,
  failed: <XCircle className="h-4 w-4 text-red-500 shrink-0" />,
};

const STATUS_BADGE: Record<SongResult["status"], string> = {
  activated: "border-green-500 text-green-600",
  low_confidence: "border-amber-500 text-amber-600",
  failed: "border-red-500 text-red-500",
};

const STATUS_LABEL: Record<SongResult["status"], string> = {
  activated: "Activated",
  low_confidence: "Low confidence",
  failed: "Failed",
};

type TaskState = "idle" | "dispatched" | "running" | "done" | "error";

export const LyricsAlignmentTab: React.FC = () => {
  const { token } = useAuthStore();
  const [batchResult, setBatchResult] = useState<BatchResult | null>(null);
  const [mode, setMode] = useState<"missing" | "all">("missing");
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
          logger.info("Batch alignment complete", data.result);
          if (data.result.activated > 0) {
            toast.success(`Activated ${data.result.activated} song${data.result.activated !== 1 ? "s" : ""} with word-level lyrics`);
          } else if (data.result.processed === 0) {
            toast.info("No songs needed alignment");
          } else {
            toast.warning(`Processed ${data.result.processed} songs — ${data.result.failed} failed, ${data.result.activated} activated`);
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Lyrics Alignment</h2>
          <p className="text-sm text-muted-foreground">
            Generate word-level synced lyrics for songs using WhisperX forced
            alignment.
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
            className="text-green-600"
          />
          <StatCard
            label="Needs alignment"
            value={status.needsAlignment}
            className={status.needsAlignment > 0 ? "text-amber-600" : undefined}
          />
        </div>
      )}

      <Separator />

      {/* Run controls */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <p className="text-sm font-medium">Run batch alignment</p>
          <p className="text-xs text-muted-foreground">
            {mode === "missing"
              ? "Only processes songs without word-level lyrics. Skips already-aligned songs."
              : "Re-runs alignment on all songs with vocals, including already-aligned ones."}
          </p>
        </div>
        <div className="flex gap-2 shrink-0">
          <Button
            variant={mode === "missing" ? "default" : "outline"}
            size="sm"
            onClick={() => setMode("missing")}
          >
            Missing only
          </Button>
          <Button
            variant={mode === "all" ? "default" : "outline"}
            size="sm"
            onClick={() => setMode("all")}
          >
            Re-run all
          </Button>
        </div>
      </div>

      <Button
        onClick={handleRun}
        disabled={isRunning || (mode === "missing" && status?.needsAlignment === 0)}
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
            ? "Aligning… (check back in a moment)"
            : mode === "missing"
              ? `Align ${status?.needsAlignment ?? "…"} unaligned song${status?.needsAlignment !== 1 ? "s" : ""}`
              : `Re-align all ${status?.withVocals ?? "…"} songs`}
      </Button>

      {/* In-flight indicator */}
      {isRunning && taskId && (
        <div className="flex items-center gap-2 rounded-lg border bg-muted/30 px-4 py-3 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin shrink-0" />
          <span>Running in background… task <code className="font-mono text-xs">{taskId.slice(0, 8)}</code> — this page will update automatically.</span>
        </div>
      )}

      {/* Results */}
      {batchResult && (
        <div className="space-y-3">
          <Separator />
          <div className="flex flex-wrap gap-3 rounded-lg border bg-muted/30 p-4 text-sm text-muted-foreground">
            <span>{batchResult.processed} processed</span>
            <span>·</span>
            <span className="font-medium text-green-600">
              {batchResult.activated} activated
            </span>
            {batchResult.failed > 0 && (
              <>
                <span>·</span>
                <span className="font-medium text-red-500">
                  {batchResult.failed} failed
                </span>
              </>
            )}
            {batchResult.skipped > 0 && (
              <>
                <span>·</span>
                <span>{batchResult.skipped} skipped</span>
              </>
            )}
          </div>

          {batchResult.results.length > 0 && (
            <div className="divide-y rounded-lg border max-h-96 overflow-y-auto">
              {batchResult.results.map((r) => (
                <div
                  key={r.songId}
                  className="flex items-center gap-3 px-4 py-2.5"
                >
                  {STATUS_ICON[r.status]}
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium truncate">{r.title}</p>
                    {r.status === "failed" && r.reason && (
                      <p className="text-xs text-muted-foreground truncate">
                        {r.reason}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {r.meanScore !== undefined && (
                      <span className="text-xs text-muted-foreground">
                        {r.meanScore.toFixed(3)}
                      </span>
                    )}
                    {r.wordCount !== undefined && (
                      <span className="text-xs text-muted-foreground">
                        {r.wordCount}w
                      </span>
                    )}
                    {r.sourceType && (
                      <Badge variant="outline" className="text-xs opacity-60">
                        {r.sourceType}
                      </Badge>
                    )}
                    <Badge
                      variant="outline"
                      className={`text-xs ${STATUS_BADGE[r.status]}`}
                    >
                      {STATUS_LABEL[r.status]}
                    </Badge>
                  </div>
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
  <div className="rounded-lg border bg-card p-3 text-center">
    <p className={`text-2xl font-bold ${className ?? ""}`}>{value}</p>
    <p className="text-xs text-muted-foreground mt-0.5">{label}</p>
  </div>
);
