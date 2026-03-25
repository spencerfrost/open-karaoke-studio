import React, { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useAuthStore } from "@/stores/authStore";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { createLogger } from "@/lib/logger";
import { toast } from "sonner";
import { Copy, Trash2 } from "lucide-react";

const logger = createLogger("component:DuplicatesTab");

interface DuplicateSong {
  id: string;
  title: string;
  artist: string;
  date_added: string | null;
  source: string | null;
}

interface DuplicatesResult {
  clusters: DuplicateSong[][];
  total_clusters: number;
  total_duplicates: number;
}

function formatDate(iso: string | null): string {
  if (!iso) return "Unknown date";
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export const DuplicatesTab: React.FC = () => {
  const { token } = useAuthStore();
  const [result, setResult] = useState<DuplicatesResult | null>(null);
  const [deletingIds, setDeletingIds] = useState<Set<string>>(new Set());

  const scanMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch("/api/songs/duplicates", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Scan failed");
      return res.json() as Promise<DuplicatesResult>;
    },
    onSuccess: (data) => {
      setResult(data);
      logger.info("Duplicate scan complete", {
        clusters: data.total_clusters,
        duplicates: data.total_duplicates,
      });
      if (data.total_clusters === 0) {
        toast.success("No duplicates found!");
      } else {
        toast.warning(
          `Found ${data.total_duplicates} duplicate songs in ${data.total_clusters} cluster${data.total_clusters !== 1 ? "s" : ""}`,
        );
      }
    },
    onError: () => toast.error("Failed to scan for duplicates"),
  });

  const deleteSong = async (songId: string) => {
    setDeletingIds((prev) => new Set(prev).add(songId));
    try {
      const res = await fetch(`/api/songs/${songId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Delete failed");
      toast.success("Song deleted");
      setResult((prev) => {
        if (!prev) return null;
        const updatedClusters = prev.clusters
          .map((cluster) => cluster.filter((s) => s.id !== songId))
          .filter((cluster) => cluster.length > 1);
        return {
          clusters: updatedClusters,
          total_clusters: updatedClusters.length,
          total_duplicates: updatedClusters.reduce((sum, c) => sum + c.length, 0),
        };
      });
    } catch {
      toast.error("Failed to delete song");
    } finally {
      setDeletingIds((prev) => {
        const next = new Set(prev);
        next.delete(songId);
        return next;
      });
    }
  };

  const isClean = result && result.total_clusters === 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Duplicate Detection</h2>
          <p className="text-sm text-muted-foreground">
            Find songs that appear more than once based on matching title and
            artist.
          </p>
        </div>
        <Button
          onClick={() => scanMutation.mutate()}
          disabled={scanMutation.isPending}
        >
          <Copy className="mr-2 h-4 w-4" />
          {scanMutation.isPending ? "Scanning..." : "Find Duplicates"}
        </Button>
      </div>

      {/* Summary bar */}
      {result && (
        <div className="flex flex-wrap gap-3 rounded-lg border bg-muted/30 p-4 text-sm text-muted-foreground">
          <span>{result.total_clusters} duplicate cluster{result.total_clusters !== 1 ? "s" : ""}</span>
          <span>·</span>
          <span
            className={result.total_duplicates > 0 ? "font-medium text-amber-500" : ""}
          >
            {result.total_duplicates} duplicate songs
          </span>
        </div>
      )}

      {/* Clusters */}
      {result && result.clusters.map((cluster, i) => {
        const representative = cluster[0];
        return (
          <section key={`${representative.title}-${representative.artist}-${i}`} className="space-y-2">
            <h3 className="flex items-center gap-2 font-medium">
              <Badge variant="outline" className="border-amber-500 text-amber-500">
                {cluster.length}
              </Badge>
              {representative.title}
              <span className="text-xs font-normal text-muted-foreground">
                by {representative.artist}
              </span>
            </h3>
            <div className="divide-y rounded-lg border">
              {cluster.map((song) => (
                <div
                  key={song.id}
                  className="flex items-center justify-between px-4 py-3"
                >
                  <div>
                    <p className="text-sm font-medium">{song.title}</p>
                    <p className="text-xs text-muted-foreground">
                      {song.artist}
                      <span className="mx-1.5">·</span>
                      Added {formatDate(song.date_added)}
                      {song.source && (
                        <>
                          <span className="mx-1.5">·</span>
                          {song.source}
                        </>
                      )}
                    </p>
                  </div>
                  <Button
                    variant="destructive"
                    size="sm"
                    disabled={deletingIds.has(song.id)}
                    onClick={() => deleteSong(song.id)}
                  >
                    <Trash2 className="mr-1.5 h-3.5 w-3.5" />
                    {deletingIds.has(song.id) ? "Deleting..." : "Delete"}
                  </Button>
                </div>
              ))}
            </div>
          </section>
        );
      })}

      {/* Clean state */}
      {isClean && (
        <div className="py-12 text-center text-muted-foreground">
          <Copy className="mx-auto mb-3 h-10 w-10 opacity-40" />
          <p className="font-medium">No duplicates found</p>
          <p className="text-sm">Every song in the library is unique.</p>
        </div>
      )}

      {/* Empty state (before first scan) */}
      {!result && !scanMutation.isPending && (
        <div className="py-12 text-center text-muted-foreground">
          <Copy className="mx-auto mb-3 h-10 w-10 opacity-40" />
          <p className="text-sm">
            Run a scan to find songs that have been added more than once.
          </p>
        </div>
      )}
    </div>
  );
};
