import React, { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useAuthStore } from "@/stores/authStore";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { createLogger } from "@/lib/logger";
import { toast } from "sonner";
import { Clock, Music, ShieldAlert } from "lucide-react";
import { SongActionPanel } from "./SongActionPanel";
import { Song } from "@/types/Song";

const logger = createLogger("component:DataQualityTab");

type Severity = "error" | "warning" | "info";

interface MetadataIssue {
  type: string;
  label: string;
  severity: Severity;
}

interface FlaggedSong {
  id: string;
  title: string;
  artist: string;
  date_added: string | null;
  source: string | null;
  status: string;
  issues: MetadataIssue[];
}

interface MetadataAuditResult {
  flagged_songs: FlaggedSong[];
  summary: Record<string, number>;
  total_songs_scanned: number;
  total_flagged: number;
}

const SEVERITY_BADGE_CLASS: Record<Severity, string> = {
  error: "border-red-500 text-red-500",
  warning: "border-amber-500 text-amber-500",
  info: "border-muted-foreground/50 text-muted-foreground",
};

export const DataQualityTab: React.FC = () => {
  const { token } = useAuthStore();
  const [result, setResult] = useState<MetadataAuditResult | null>(null);
  const [expandedSongId, setExpandedSongId] = useState<string | null>(null);

  const scanMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch("/api/songs/metadata-audit", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Scan failed");
      return res.json() as Promise<MetadataAuditResult>;
    },
    onSuccess: (data) => {
      setResult(data);
      setExpandedSongId(null);
      logger.info("Data quality scan complete", {
        scanned: data.total_songs_scanned,
        flagged: data.total_flagged,
      });
      if (data.total_flagged === 0) {
        toast.success("No metadata issues found!");
      } else {
        toast.warning(
          `Found ${data.total_flagged} song${data.total_flagged !== 1 ? "s" : ""} with issues`,
        );
      }
    },
    onError: () => toast.error("Failed to run data quality scan"),
  });

  const backfillDurationMutation = useMutation({
    mutationFn: async (mode: "missing" | "all") => {
      const res = await fetch(`/api/songs/backfill-duration?mode=${mode}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to queue duration backfill");
      return res.json() as Promise<{ taskId: string; queued: number }>;
    },
    onSuccess: (data) => {
      toast.success(`Queued duration backfill for ${data.queued} song${data.queued !== 1 ? "s" : ""}`);
    },
    onError: () => toast.error("Failed to queue duration backfill"),
  });

  const backfillGenresMutation = useMutation({
    mutationFn: async (mode: "missing" | "all") => {
      const res = await fetch(`/api/songs/backfill-genres?mode=${mode}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to queue genre backfill");
      return res.json() as Promise<{ taskId: string; queued: number }>;
    },
    onSuccess: (data) => {
      toast.success(`Queued genre backfill for ${data.queued} song${data.queued !== 1 ? "s" : ""}`);
    },
    onError: () => toast.error("Failed to queue genre backfill"),
  });

  const handleDone = () => {
    setExpandedSongId(null);
    scanMutation.mutate();
  };

  const errorCount =
    result?.flagged_songs.reduce(
      (n, s) => n + s.issues.filter((i) => i.severity === "error").length,
      0,
    ) ?? 0;
  const warningCount =
    result?.flagged_songs.reduce(
      (n, s) => n + s.issues.filter((i) => i.severity === "warning").length,
      0,
    ) ?? 0;
  const infoCount =
    result?.flagged_songs.reduce(
      (n, s) => n + s.issues.filter((i) => i.severity === "info").length,
      0,
    ) ?? 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Data Quality</h2>
          <p className="text-sm text-muted-foreground">
            Scan the library for songs with missing or suspicious metadata.
          </p>
        </div>
        <Button
          onClick={() => scanMutation.mutate()}
          disabled={scanMutation.isPending}
        >
          <ShieldAlert className="mr-2 h-4 w-4" />
          {scanMutation.isPending ? "Scanning..." : "Run Scan"}
        </Button>
      </div>

      {/* Summary bar */}
      {result && (
        <div className="flex flex-wrap gap-3 rounded-lg border bg-muted/30 p-4 text-sm text-muted-foreground">
          <span>{result.total_songs_scanned} songs scanned</span>
          <span>·</span>
          <span className={result.total_flagged > 0 ? "font-medium" : ""}>
            {result.total_flagged} flagged
          </span>
          {errorCount > 0 && (
            <>
              <span>·</span>
              <span className="font-medium text-red-500">
                {errorCount} error{errorCount !== 1 ? "s" : ""}
              </span>
            </>
          )}
          {warningCount > 0 && (
            <>
              <span>·</span>
              <span className="font-medium text-amber-500">
                {warningCount} warning{warningCount !== 1 ? "s" : ""}
              </span>
            </>
          )}
          {infoCount > 0 && (
            <>
              <span>·</span>
              <span>{infoCount} info</span>
            </>
          )}
        </div>
      )}

      {/* Results list */}
      {result && result.flagged_songs.length > 0 && (
        <div className="divide-y rounded-lg border">
          {result.flagged_songs.map((flaggedSong) => (
            <div key={flaggedSong.id}>
              <button
                type="button"
                className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-muted/30 transition-colors"
                onClick={() =>
                  setExpandedSongId((prev) =>
                    prev === flaggedSong.id ? null : flaggedSong.id,
                  )
                }
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium truncate">
                    {flaggedSong.title}
                  </p>
                  <p className="text-xs text-muted-foreground truncate">
                    {flaggedSong.artist}
                  </p>
                </div>
                <div className="flex flex-wrap gap-1 ml-4 shrink-0 justify-end">
                  {flaggedSong.issues.map((issue) => (
                    <Badge
                      key={issue.type}
                      variant="outline"
                      className={`text-xs ${SEVERITY_BADGE_CLASS[issue.severity]}`}
                    >
                      {issue.label}
                    </Badge>
                  ))}
                </div>
              </button>

              {expandedSongId === flaggedSong.id && (
                <div className="border-t bg-muted/20 p-4">
                  <SongActionPanel
                    song={flaggedSong as unknown as Song}
                    issues={flaggedSong.issues.map((i) => i.type)}
                    onDone={handleDone}
                  />
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Clean state */}
      {result && result.total_flagged === 0 && (
        <div className="py-12 text-center text-muted-foreground">
          <ShieldAlert className="mx-auto mb-3 h-10 w-10 opacity-40" />
          <p className="font-medium">All clear</p>
          <p className="text-sm">No metadata issues detected.</p>
        </div>
      )}

      {/* Empty state (before first run) */}
      {!result && !scanMutation.isPending && (
        <div className="py-12 text-center text-muted-foreground">
          <ShieldAlert className="mx-auto mb-3 h-10 w-10 opacity-40" />
          <p className="text-sm">
            Run a scan to check for metadata issues across all songs.
          </p>
        </div>
      )}

      <Separator />

      {/* Genre Enrichment */}
      <div className="space-y-3">
        <div>
          <h2 className="text-lg font-semibold">Genre Enrichment</h2>
          <p className="text-sm text-muted-foreground">
            Fetch genre tags from Last.fm for your library.
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="default"
            onClick={() => backfillGenresMutation.mutate("missing")}
            disabled={backfillGenresMutation.isPending}
          >
            <Music className="mr-2 h-4 w-4" />
            {backfillGenresMutation.variables === "missing" && backfillGenresMutation.isPending
              ? "Queueing..."
              : "Backfill Missing"}
          </Button>
          <Button
            variant="outline"
            onClick={() => backfillGenresMutation.mutate("all")}
            disabled={backfillGenresMutation.isPending}
          >
            <Music className="mr-2 h-4 w-4" />
            {backfillGenresMutation.variables === "all" && backfillGenresMutation.isPending
              ? "Queueing..."
              : "Refresh All"}
          </Button>
        </div>
      </div>

      <Separator />

      {/* Duration Backfill */}
      <div className="space-y-3">
        <div>
          <h2 className="text-lg font-semibold">Duration</h2>
          <p className="text-sm text-muted-foreground">
            Compute song duration from the original audio file.
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="default"
            onClick={() => backfillDurationMutation.mutate("missing")}
            disabled={backfillDurationMutation.isPending}
          >
            <Clock className="mr-2 h-4 w-4" />
            {backfillDurationMutation.variables === "missing" && backfillDurationMutation.isPending
              ? "Queueing..."
              : "Backfill Missing"}
          </Button>
          <Button
            variant="outline"
            onClick={() => backfillDurationMutation.mutate("all")}
            disabled={backfillDurationMutation.isPending}
          >
            <Clock className="mr-2 h-4 w-4" />
            {backfillDurationMutation.variables === "all" && backfillDurationMutation.isPending
              ? "Queueing..."
              : "Refresh All"}
          </Button>
        </div>
      </div>
    </div>
  );
};
