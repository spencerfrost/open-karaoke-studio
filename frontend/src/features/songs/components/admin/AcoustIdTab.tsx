import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/stores/authStore";
import { Badge } from "@/components/ui/badge";
import { createLogger } from "@/lib/logger";
import { Song } from "@/types/Song";
import { SongActionPanel } from "./SongActionPanel";
import { toast } from "sonner";

const logger = createLogger("component:AcoustIdTab");

type StatusFilter = "ambiguous" | "no_match" | "failed";

function useSongsByFingerprintStatus(status: StatusFilter) {
  const { token } = useAuthStore();
  return useQuery<Song[]>({
    queryKey: ["admin-acoustid-songs", status],
    queryFn: async () => {
      const res = await fetch(
        `/api/songs/by-fingerprint-status?status=${status}&limit=500`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      if (!res.ok) throw new Error("Failed to load songs");
      return res.json();
    },
    enabled: !!token,
  });
}

const STATUS_STYLES: Record<StatusFilter, string> = {
  ambiguous: "text-orange-400 border-orange-500/40",
  no_match: "text-amber-400 border-amber-500/40",
  failed: "text-red-400 border-red-500/40",
};

const ACTIVE_PILL_STYLES: Record<StatusFilter, string> = {
  ambiguous: "bg-orange-500/20 text-orange-400 border border-orange-500/40",
  no_match: "bg-amber-500/20 text-amber-400 border border-amber-500/40",
  failed: "bg-red-500/20 text-red-400 border border-red-500/40",
};

export const AcoustIdTab: React.FC = () => {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("ambiguous");
  const [expandedSongId, setExpandedSongId] = useState<string | null>(null);
  const { token } = useAuthStore();
  const queryClient = useQueryClient();

  const reprocessAllMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch("/api/songs/fingerprint?force=true", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to dispatch");
      return res.json();
    },
    onSuccess: () => {
      toast.success("Re-fingerprint job dispatched for all songs");
      queryClient.invalidateQueries({ queryKey: ["admin-acoustid-songs"] });
    },
    onError: () => toast.error("Failed to dispatch re-fingerprint job"),
  });

  const backfillArtworkMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch("/api/songs/backfill-artwork", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to dispatch");
      return res.json();
    },
    onSuccess: () => toast.success("Album art backfill job dispatched"),
    onError: () => toast.error("Failed to dispatch backfill job"),
  });

  const ambiguousQuery = useSongsByFingerprintStatus("ambiguous");
  const noMatchQuery = useSongsByFingerprintStatus("no_match");
  const failedQuery = useSongsByFingerprintStatus("failed");

  const counts: Record<StatusFilter, number> = {
    ambiguous: ambiguousQuery.data?.length ?? 0,
    no_match: noMatchQuery.data?.length ?? 0,
    failed: failedQuery.data?.length ?? 0,
  };

  const activeQuery =
    statusFilter === "ambiguous"
      ? ambiguousQuery
      : statusFilter === "no_match"
        ? noMatchQuery
        : failedQuery;

  const songs = activeQuery.data ?? [];

  const handleRowClick = (songId: string) => {
    setExpandedSongId((prev) => (prev === songId ? null : songId));
    logger.debug("Toggled row", { songId });
  };

  const handleDone = () => setExpandedSongId(null);

  const filterPills: { status: StatusFilter; label: string }[] = [
    { status: "ambiguous", label: "Ambiguous" },
    { status: "no_match", label: "No Match" },
    { status: "failed", label: "Failed" },
  ];

  return (
    <div className="space-y-4">
      {/* Batch actions */}
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm text-muted-foreground">
          AcoustID fingerprint management and review queue.
        </p>
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => backfillArtworkMutation.mutate()}
            disabled={backfillArtworkMutation.isPending}
            className="px-3 py-1 rounded text-xs font-medium bg-primary/10 text-primary border border-primary/30 hover:bg-primary/20 disabled:opacity-50 transition-colors"
          >
            {backfillArtworkMutation.isPending ? "Dispatching…" : "Backfill Album Art"}
          </button>
          <button
            onClick={() => reprocessAllMutation.mutate()}
            disabled={reprocessAllMutation.isPending}
            className="px-3 py-1 rounded text-xs font-medium bg-primary/10 text-primary border border-primary/30 hover:bg-primary/20 disabled:opacity-50 transition-colors"
          >
            {reprocessAllMutation.isPending ? "Dispatching…" : "Re-fingerprint All"}
          </button>
        </div>
      </div>

      {/* Filter pills */}
      <div className="flex items-center gap-2">
        {filterPills.map(({ status, label }) => (
          <button
            key={status}
            onClick={() => {
              setStatusFilter(status);
              setExpandedSongId(null);
            }}
            className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
              statusFilter === status
                ? ACTIVE_PILL_STYLES[status]
                : "bg-muted text-muted-foreground border border-border hover:bg-muted/80"
            }`}
          >
            {label} ({counts[status]})
          </button>
        ))}
      </div>

      {/* Song list */}
      {activeQuery.isLoading && (
        <p className="text-sm text-muted-foreground">Loading songs...</p>
      )}
      {activeQuery.error && (
        <p className="text-sm text-destructive">
          Failed to load: {(activeQuery.error as Error).message}
        </p>
      )}
      {!activeQuery.isLoading && songs.length === 0 && (
        <p className="text-sm text-muted-foreground">
          No songs with status &ldquo;{statusFilter}&rdquo;.
        </p>
      )}

      <div className="space-y-1">
        {songs.map((song) => (
          <div
            key={song.id}
            className="rounded-lg border border-border/50 overflow-hidden"
          >
            <div
              className="flex items-center gap-3 p-3 cursor-pointer hover:bg-muted/40 transition-colors"
              onClick={() => handleRowClick(song.id)}
            >
              <div className="flex-1 min-w-0">
                <p className="font-medium text-sm truncate">{song.title}</p>
                <p className="text-xs text-muted-foreground truncate">
                  {song.artist}
                </p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {song.acoustidScore != null && (
                  <span className="text-xs text-muted-foreground">
                    {(song.acoustidScore * 100).toFixed(0)}%
                  </span>
                )}
                <Badge
                  variant="outline"
                  className={`text-xs ${STATUS_STYLES[statusFilter]}`}
                >
                  {song.acoustidFingerprintStatus}
                </Badge>
                <span className="text-muted-foreground text-xs">
                  {expandedSongId === song.id ? "▲" : "▼"}
                </span>
              </div>
            </div>

            {expandedSongId === song.id && (
              <div className="border-t border-border/50 bg-muted/20 p-4">
                <SongActionPanel song={song} onDone={handleDone} />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
